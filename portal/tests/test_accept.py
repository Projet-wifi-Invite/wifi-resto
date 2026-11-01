"""Tests de la page d'acceptation des conditions."""
import pytest

from app import create_app
from app.models import ConnectionSession, LegalLog, NewsletterConsent, Restaurant, db


@pytest.fixture
def client():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True})
    with app.app_context():
        db.create_all()
        db.session.add(Restaurant(name="Trattoria Test", slug="test"))
        db.session.commit()
        yield app.test_client()


def test_page_affiche_le_restaurant_et_la_mention_cnil(client):
    html = client.get("/portal/test").get_data(as_text=True)
    assert "Trattoria Test" in html
    assert "1 an" in html
    assert "jamais" in html


def test_restaurant_inconnu_donne_404(client):
    assert client.get("/portal/nexistepas").status_code == 404


def test_accepter_cree_une_session(client):
    reponse = client.post("/portal/test/accept", data={"terms": "on", "client_hid": "abc"})
    assert reponse.status_code == 302
    assert ConnectionSession.query.count() == 1
    assert NewsletterConsent.query.count() == 0


def test_previsualisation_n_ecrit_pas_de_journal_legal(client):
    client.post("/portal/test/accept", data={"terms": "on"})
    assert LegalLog.query.count() == 0
    assert ConnectionSession.query.one().client_hid == "preview"


def test_refuser_les_conditions_est_bloque(client):
    reponse = client.post("/portal/test/accept", data={"client_hid": "abc"})
    assert reponse.status_code == 400
    assert ConnectionSession.query.count() == 0


def test_email_enregistre_seulement_si_case_cochee(client):
    client.post("/portal/test/accept", data={"terms": "on", "email": "a@b.fr"})
    assert NewsletterConsent.query.count() == 0
    client.post("/portal/test/accept", data={"terms": "on", "newsletter": "on", "email": "a@b.fr"})
    assert NewsletterConsent.query.count() == 1


def test_page_merci_affiche_les_liens_du_restaurant(client):
    from app.models import Restaurant, db
    with client.application.app_context():
        resto = db.session.execute(db.select(Restaurant).filter_by(slug="test")).scalar_one()
        resto.google_reviews_url = "https://maps.google.com/?cid=1"
        resto.instagram_url = "https://www.instagram.com/test/"
        db.session.commit()
    html = client.get("/portal/test/merci").get_data(as_text=True)
    assert "Laisser un avis sur Google" in html
    assert "Suivre sur Instagram" in html
