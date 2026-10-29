"""Fabrique de l'application Flask du portail wifi-resto."""
import os

from dotenv import load_dotenv
from flask import Flask

from app.models import db


def create_app(test_config=None):
    """Crée et configure l'application. Appelée par Flask et par les tests."""
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-only")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite://")

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

    @app.cli.command("seed-demo")
    def seed_demo():
        """Crée un restaurant de démonstration. Usage : flask --app app seed-demo"""
        from app.models import Restaurant
        if db.session.execute(db.select(Restaurant).filter_by(slug="demo")).scalar_one_or_none():
            print("Le restaurant demo existe déjà.")
            return
        db.session.add(Restaurant(name="Trattoria Demo", slug="demo",
                                  google_reviews_url="https://g.page/r/demo/review"))
        db.session.commit()
        print("Restaurant demo créé : /portal/demo")

    return app
