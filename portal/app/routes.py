"""Routes du portail captif."""
from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.models import ConnectionSession, NewsletterConsent, Restaurant, db

bp = Blueprint("portal", __name__)


@bp.get("/")
def index():
    """Page technique : liste rien, sert à vérifier que l'appli répond."""
    return render_template("index.html", restaurant="wifi-resto")


@bp.get("/health")
def health():
    """Point de contrôle pour la supervision (Uptime Kuma)."""
    return {"status": "ok"}


@bp.get("/portal/<slug>")
def accept_page(slug):
    """Page « J'accepte les conditions » d'un restaurant."""
    restaurant = db.session.execute(
        db.select(Restaurant).filter_by(slug=slug)
    ).scalar_one_or_none()
    if restaurant is None:
        abort(404)
    # TODO : client_hid viendra de la requête openNDS (FAS), pas d'un champ fixe
    return render_template("accept.html", restaurant=restaurant, client_hid="dev-hid")


@bp.post("/portal/<slug>/accept")
def accept(slug):
    """Enregistre l'acceptation des conditions, et l'e-mail s'il est donné."""
    restaurant = db.session.execute(
        db.select(Restaurant).filter_by(slug=slug)
    ).scalar_one_or_none()
    if restaurant is None:
        abort(404)
    if request.form.get("terms") != "on":
        abort(400, "Les conditions d'utilisation doivent être acceptées.")

    session = ConnectionSession(
        restaurant_id=restaurant.id,
        client_hid=request.form.get("client_hid", "inconnu"),
        accepted_terms=True,
    )
    db.session.add(session)

    email = request.form.get("email", "").strip()
    if request.form.get("newsletter") == "on" and email:
        db.session.add(NewsletterConsent(restaurant_id=restaurant.id, email=email))

    db.session.commit()
    return redirect(url_for("portal.thanks", slug=slug))


@bp.get("/portal/<slug>/merci")
def thanks(slug):
    restaurant = db.session.execute(
        db.select(Restaurant).filter_by(slug=slug)
    ).scalar_one_or_none()
    if restaurant is None:
        abort(404)
    return render_template("thanks.html", restaurant=restaurant)
