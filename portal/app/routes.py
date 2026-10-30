"""Routes du portail captif."""
from datetime import timedelta

from flask import Blueprint, Response, abort, current_app, redirect, render_template, request, url_for

from app.fas import (
    FasError,
    build_auth_line,
    compute_rhid,
    decode_payload,
    encode_auth_list,
    gateway_hash,
    is_sha256_hex,
    parse_acklist,
    parse_fas,
)
from app.models import (
    ConnectionSession,
    LegalLog,
    NewsletterConsent,
    PendingAuth,
    Restaurant,
    db,
    now_utc,
)

bp = Blueprint("portal", __name__)

LEGAL_RETENTION = timedelta(days=365)

# Champs de `fas` sans lesquels on ne peut ni tenir le journal légal (IP, MAC),
# ni ranger l'autorisation dans la bonne file authmon (gatewayname), ni trouver
# le restaurant (resto). openNDS les envoie toujours ; leur absence est une
# passerelle mal configurée, à refuser plutôt qu'à journaliser à vide.
_REQUIRED_FAS_KEYS = ("clientip", "clientmac", "gatewayname", "resto")


def _restaurant_or_404(slug: str) -> Restaurant:
    restaurant = db.session.execute(db.select(Restaurant).filter_by(slug=slug)).scalar_one_or_none()
    if restaurant is None:
        abort(404)
    return restaurant


def _fas_params(raw: str) -> dict[str, str]:
    """Décode le paramètre `fas` ou répond 400 (illisible, hid invalide, champ requis absent)."""
    try:
        params = parse_fas(raw)
    except FasError:
        abort(400, "Paramètre fas invalide.")
    missing = [key for key in _REQUIRED_FAS_KEYS if not params.get(key)]
    if missing:
        abort(400, f"Paramètre fas incomplet : {', '.join(missing)}.")
    return params


def _save_consent(restaurant: Restaurant, form) -> None:
    """Enregistre l'e-mail uniquement si la case newsletter est cochée."""
    email = form.get("email", "").strip()
    if form.get("newsletter") == "on" and email:
        db.session.add(NewsletterConsent(restaurant_id=restaurant.id, email=email))


@bp.get("/")
def index():
    """Page technique : sert à vérifier que l'appli répond."""
    return render_template("index.html", restaurant="wifi-resto")


@bp.get("/health")
def health():
    """Supervision : l'appli répond."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Entrée openNDS (FAS niveau 4) : docs/integration-opennds.md § 3 et § 4
# ---------------------------------------------------------------------------

@bp.get("/fas")
def fas_entry():
    """Point d'entrée GET : authmon (variante wget) si `auth_get` est présent, sinon page d'acceptation."""
    if "auth_get" in request.args:
        return handle_authmon()
    raw = request.args.get("fas", "")
    params = _fas_params(raw)
    restaurant = _restaurant_or_404(params["resto"])
    # `fas` repart tel quel dans un champ caché : le POST d'acceptation y relit `hid`.
    return render_template("accept.html", restaurant=restaurant, fas=raw)


@bp.post("/fas/accept")
def fas_accept():
    """Acceptation des conditions : journal légal, session, et mise en file pour authmon."""
    params = _fas_params(request.form.get("fas", ""))
    restaurant = _restaurant_or_404(params["resto"])
    if request.form.get("terms") != "on":
        abort(400, "Les conditions d'utilisation doivent être acceptées.")
    if restaurant.gateway_hash is None:
        # Sans passerelle enregistrée, la ligne irait dans une file que personne ne viendrait lire :
        # le client verrait « merci » sans jamais avoir Internet. On refuse plutôt que d'échouer en silence.
        current_app.logger.error("Restaurant %s sans passerelle enregistrée : /fas/accept refusé", restaurant.slug)
        abort(503, "Ce restaurant n'a pas de passerelle enregistrée.")
    if restaurant.gateway_hash != gateway_hash(params["gatewayname"]):
        abort(403, "Passerelle inconnue pour ce restaurant.")

    rhid = compute_rhid(params["hid"], current_app.config["FAS_KEY"])
    now = now_utc()

    db.session.add(ConnectionSession(restaurant_id=restaurant.id, client_hid=params["hid"], accepted_terms=True))
    # Journal légal : données techniques seulement. Jamais `originurl` (site visité).
    db.session.add(
        LegalLog(
            restaurant_id=restaurant.id,
            client_ip=params["clientip"],
            client_mac=params["clientmac"],
            connected_at=now,
            purge_after=now + LEGAL_RETENTION,
        )
    )
    # Un rafraîchissement de la page renvoie le même hid : une seule ligne par rhid dans la file.
    if not db.session.execute(db.select(PendingAuth).filter_by(rhid=rhid)).scalar_one_or_none():
        db.session.add(
            PendingAuth(
                # Le routeur hache le gatewayname URL-encodé : on hache la valeur telle que reçue.
                gateway_hash=gateway_hash(params["gatewayname"]),
                rhid=rhid,
                line=build_auth_line(rhid, custom=f"resto={restaurant.slug}"),
            )
        )
    _save_consent(restaurant, request.form)
    db.session.commit()
    return redirect(url_for("portal.thanks", slug=restaurant.slug))


# ---------------------------------------------------------------------------
# Prévisualisation sans passerelle (démo, maquette)
# ---------------------------------------------------------------------------

@bp.get("/portal/<slug>")
def accept_page(slug):
    """Page « J'accepte les conditions », hors openNDS (prévisualisation)."""
    restaurant = _restaurant_or_404(slug)
    return render_template("accept.html", restaurant=restaurant, fas=None)


@bp.post("/portal/<slug>/accept")
def accept(slug):
    """Acceptation hors openNDS : session seulement, pas de journal légal (pas de vraie connexion)."""
    restaurant = _restaurant_or_404(slug)
    if request.form.get("terms") != "on":
        abort(400, "Les conditions d'utilisation doivent être acceptées.")
    db.session.add(ConnectionSession(restaurant_id=restaurant.id, client_hid="preview", accepted_terms=True))
    _save_consent(restaurant, request.form)
    db.session.commit()
    return redirect(url_for("portal.thanks", slug=slug))


@bp.get("/portal/<slug>/merci")
def thanks(slug):
    restaurant = _restaurant_or_404(slug)
    return render_template("thanks.html", restaurant=restaurant)


# ---------------------------------------------------------------------------
# Dialogue avec authmon (FAS niveau 4) : docs/integration-opennds.md § 5
# ---------------------------------------------------------------------------

# Une ligne qu'authmon n'a pas acquittée en 60 s ne le sera plus (client parti du Wi-Fi,
# `ndsctl auth` en échec). On la retire : authmon ne traite que 4 lignes par cycle, les plus
# anciennes d'abord, et des lignes mortes bloqueraient toutes les suivantes (§ 5.2 du contrat).
PENDING_AUTH_TTL = timedelta(seconds=60)

# authmon.sh ne traite que 4 clients par cycle (limite d'arguments de Busybox) et tronque la
# réponse à 1024 caractères : renvoyer plus de 4 lignes ne sert à rien.
AUTHMON_BATCH = 4


def _text(body: str, status: int = 200) -> Response:
    return Response(body, status=status, mimetype="text/plain")


def _purge_stale(gw_hash: str) -> int:
    """Retire de la file d'une passerelle les autorisations trop anciennes. Renvoie le nombre retiré."""
    expired_before = now_utc() - PENDING_AUTH_TTL
    result = db.session.execute(
        db.delete(PendingAuth).where(
            PendingAuth.gateway_hash == gw_hash,
            PendingAuth.created_at < expired_before,
        )
    )
    if result.rowcount:
        db.session.commit()
        current_app.logger.warning(
            "authmon : %d autorisation(s) expirée(s) retirée(s), passerelle %s", result.rowcount, gw_hash[:12]
        )
    return result.rowcount


def handle_authmon():
    """Répond au démon authmon de la passerelle : clear, view, list, deauthed, custom."""
    action = request.values.get("auth_get", "")
    gw_hash = request.values.get("gatewayhash", "")
    payload = decode_payload(request.values.get("payload", ""))

    if not is_sha256_hex(gw_hash):
        # Valeur non maîtrisée : on ne la logue pas (une valeur libre pourrait forger une ligne de log).
        current_app.logger.warning("authmon : gatewayhash absent ou mal formé, requête refusée")
        return _text("", 403)
    if db.session.scalar(db.select(Restaurant.id).filter_by(gateway_hash=gw_hash)) is None:
        current_app.logger.warning("authmon : passerelle inconnue refusée (%s…)", gw_hash[:12])
        return _text("", 403)

    if action in ("deauthed", "custom"):
        # Le payload contient des données du client (MAC, jeton) : on journalise l'action, jamais le contenu.
        # TODO (étape séparée) : exploiter `deauthed` pour renseigner LegalLog.disconnected_at.
        # openNDS l'envoie au niveau 4 dès que BinAuth est actif (libopennds.sh, send_post_data : niveau >= 3).
        current_app.logger.info("authmon %s depuis la passerelle %s", action, gw_hash[:12])
        return _text("ack")

    if action == "clear":
        db.session.execute(db.delete(PendingAuth).where(PendingAuth.gateway_hash == gw_hash))
        db.session.commit()
        return _text("")

    if action == "view" and payload != "none":
        acked = parse_acklist(payload)
        if acked:
            # Le filtre sur gateway_hash est essentiel : une passerelle n'acquitte que ses propres lignes.
            db.session.execute(
                db.delete(PendingAuth).where(PendingAuth.gateway_hash == gw_hash, PendingAuth.rhid.in_(acked))
            )
            db.session.commit()
        return _text("ack")

    if action in ("view", "list"):
        _purge_stale(gw_hash)
        pending = db.session.execute(
            db.select(PendingAuth)
            .filter_by(gateway_hash=gw_hash)
            .order_by(PendingAuth.created_at)
            .limit(AUTHMON_BATCH)
        ).scalars().all()
        body = encode_auth_list([item.line for item in pending])
        if action == "list" and pending:
            db.session.execute(db.delete(PendingAuth).where(PendingAuth.id.in_([item.id for item in pending])))
            db.session.commit()
        return _text(body)

    return _text("", 400)


@bp.post("/fas")
def fas_authmon():
    """Point d'entrée d'authmon (variante POST, quand php-cli est installé sur le routeur)."""
    return handle_authmon()
