"""Fabrique de l'application Flask du portail wifi-resto."""
import os

from dotenv import load_dotenv
from flask import Flask


def create_app():
    """Crée et configure l'application. Appelée par Flask et par les tests."""
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-only")

    from app.routes import bp
    app.register_blueprint(bp)

    return app
