"""Routes du portail captif."""
from flask import Blueprint, render_template

bp = Blueprint("portal", __name__)


@bp.get("/")
def index():
    """Page d'accueil du portail (future page « J'accepte les conditions »)."""
    return render_template("index.html", restaurant="Restaurant de test")


@bp.get("/health")
def health():
    """Point de contrôle pour la supervision (Uptime Kuma)."""
    return {"status": "ok"}
