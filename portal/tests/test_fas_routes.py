"""Tests des routes /fas : de la redirection openNDS jusqu'à la file authmon."""
import hashlib

import pytest

from app import create_app
from app.models import ConnectionSession, LegalLog, PendingAuth, Restaurant, db
from tests.test_fas import HID, make_fas

KEY = "cle-de-test"
GW = hashlib.sha256(b"Coeur%20de%20Beurre").hexdigest()


@pytest.fixture
def client():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True, "FAS_KEY": KEY})
    with app.app_context():
        db.create_all()
        db.session.add(Restaurant(name="Cœur de Beurre", slug="coeur-de-beurre", gateway_hash=GW))
        db.session.commit()
        yield app.test_client()


def test_entree_fas_affiche_la_page_du_restaurant(client):
    html = client.get("/fas", query_string={"fas": make_fas()}).get_data(as_text=True)
    assert "Cœur de Beurre" in html
    assert 'name="fas"' in html


def test_entree_fas_sans_parametre_donne_400(client):
    assert client.get("/fas").status_code == 400


def test_entree_fas_restaurant_inconnu_donne_404(client):
    assert client.get("/fas", query_string={"fas": make_fas(resto="inconnu")}).status_code == 404


@pytest.mark.parametrize("champ", ["clientip", "clientmac", "gatewayname"])
def test_fas_sans_champ_requis_donne_400(client, champ):
    """Sans IP/MAC pas de journal légal valable ; sans gatewayname pas de file authmon."""
    fas = make_fas(**{champ: ""})
    assert client.get("/fas", query_string={"fas": fas}).status_code == 400
    assert client.post("/fas/accept", data={"fas": fas, "terms": "on"}).status_code == 400
    assert LegalLog.query.count() == 0


def test_acceptation_ecrit_journal_session_et_file(client):
    reponse = client.post("/fas/accept", data={"fas": make_fas(), "terms": "on"})
    assert reponse.status_code == 302

    log = LegalLog.query.one()
    assert log.client_ip == "10.20.0.42"
    assert log.client_mac == "aa:bb:cc:dd:ee:ff"
    assert (log.purge_after - log.connected_at).days == 365

    assert ConnectionSession.query.one().client_hid == HID

    pending = PendingAuth.query.one()
    assert pending.rhid == hashlib.sha256((HID + KEY).encode()).hexdigest()
    assert pending.gateway_hash == GW
    assert pending.line.startswith(pending.rhid + " 240 2000 8000 0 0 ")


def test_acceptation_sans_cocher_est_refusee(client):
    assert client.post("/fas/accept", data={"fas": make_fas()}).status_code == 400
    assert PendingAuth.query.count() == 0
    assert LegalLog.query.count() == 0


def test_restaurant_sans_passerelle_refuse_l_acceptation_en_503(client):
    """Sans gateway_hash, la ligne irait dans une file que personne ne lirait : on refuse explicitement."""
    db.session.add(Restaurant(name="Sans passerelle", slug="sans-passerelle"))
    db.session.commit()
    response = client.post("/fas/accept", data={"fas": make_fas(resto="sans-passerelle"), "terms": "on"})
    assert response.status_code == 503
    assert PendingAuth.query.count() == 0
    assert LegalLog.query.count() == 0


def test_double_acceptation_ne_duplique_pas_la_file(client):
    client.post("/fas/accept", data={"fas": make_fas(), "terms": "on"})
    client.post("/fas/accept", data={"fas": make_fas(), "terms": "on"})
    assert PendingAuth.query.count() == 1
