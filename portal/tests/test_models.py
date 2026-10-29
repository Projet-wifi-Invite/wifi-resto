"""Tests du modèle de données, sur SQLite en mémoire."""
from datetime import timedelta

from app import create_app
from app.models import LegalLog, Restaurant, db, now_utc


def make_app():
    return create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://"})


def test_les_tables_se_creent():
    app = make_app()
    with app.app_context():
        db.create_all()
        tables = set(db.metadata.tables)
    assert tables == {"restaurants", "connection_sessions", "legal_logs", "newsletter_consents", "pending_auths"}


def test_journal_legal_purge_a_un_an():
    app = make_app()
    with app.app_context():
        db.create_all()
        resto = Restaurant(name="Test", slug="test")
        db.session.add(resto)
        db.session.flush()
        debut = now_utc()
        log = LegalLog(
            restaurant_id=resto.id,
            client_ip="10.20.0.42",
            client_port=51234,
            client_mac="AA:BB:CC:DD:EE:FF",
            connected_at=debut,
            purge_after=debut + timedelta(days=365),
        )
        db.session.add(log)
        db.session.commit()
        assert LegalLog.query.count() == 1
        assert (log.purge_after - log.connected_at).days == 365
