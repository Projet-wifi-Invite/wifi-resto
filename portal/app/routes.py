"""Routes du portail captif."""
from datetime import timedelta

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for

from app.fas import FasError, build_auth_line, compute_rhid, gateway_hash, parse_fas
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
    """Point d'entrée de la passerelle : décode `fas` et affiche la page d'acceptation."""
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
