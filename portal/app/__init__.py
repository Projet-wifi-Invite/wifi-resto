"""Fabrique de l'application Flask du portail wifi-resto."""
import os

from dotenv import load_dotenv
from flask import Flask

from app.fas import gateway_hash
from app.models import db


def create_app(test_config=None):
    """Crée et configure l'application. Appelée par Flask et par les tests."""
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-only")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite://")
    app.config["FAS_KEY"] = os.environ.get("FAS_KEY", "dev-fas-key")

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from app.routes import bp
    app.register_blueprint(bp)

    @app.cli.command("init-db")
    def init_db():
        """Crée les tables. Usage : flask --app app init-db"""
        db.create_all()
        print("Tables créées.")

    @app.cli.command("seed")
    def seed():
        """Crée le restaurant du pilote. Usage : flask --app app seed"""
        from app.models import Restaurant

        slug = "coeur-de-beurre"
        if db.session.execute(db.select(Restaurant).filter_by(slug=slug)).scalar_one_or_none():
            print("Le restaurant existe déjà.")
            return
        db.session.add(
            Restaurant(
                name="Cœur de Beurre",
                slug=slug,
                primary_color="#3b6f9c",
                google_reviews_url="https://maps.google.com/?cid=17216702826779400729",
                instagram_url="https://www.instagram.com/coeurdebeurre_rennes/",
                gateway_hash=gateway_hash("Coeur%20de%20Beurre"),
            )
        )
        db.session.commit()
        print(f"Restaurant créé : /portal/{slug}")

    return app
