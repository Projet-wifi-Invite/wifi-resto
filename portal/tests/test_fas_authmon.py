"""Tests du dialogue avec authmon : la passerelle qui vient chercher ses autorisations."""
import base64
import hashlib
import logging
from urllib.parse import unquote

import pytest

from datetime import timedelta

from app import create_app
from app.fas import build_auth_line
from app.models import PendingAuth, Restaurant, db, now_utc
from app.routes import PENDING_AUTH_TTL
from tests.test_fas import HID, make_fas

KEY = "cle-de-test"
GW = hashlib.sha256(b"Coeur%20de%20Beurre").hexdigest()
OTHER_GW = hashlib.sha256(b"Autre%20Resto").hexdigest()
RHID = hashlib.sha256((HID + KEY).encode()).hexdigest()


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


@pytest.fixture
def client():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True, "FAS_KEY": KEY})
    with app.app_context():
        db.create_all()
        db.session.add(Restaurant(name="Cœur de Beurre", slug="coeur-de-beurre", gateway_hash=GW))
        db.session.add(Restaurant(name="Autre Resto", slug="autre-resto", gateway_hash=OTHER_GW))
        db.session.commit()
        yield app.test_client()


def authmon(client, action, payload="none", gw=GW, method="post", raw_payload=None):
    """Joue une requête du démon authmon. `raw_payload` court-circuite l'encodage base64."""
    encoded = raw_payload if raw_payload is not None else b64(payload)
    data = {"auth_get": action, "gatewayhash": gw, "payload": encoded}
    if method == "get":
        return client.get("/fas", query_string=data)
    return client.post("/fas", data=data)


def accept(client, hid=HID):
    return client.post("/fas/accept", data={"fas": make_fas(hid=hid), "terms": "on"})


def test_view_sur_file_vide_renvoie_etoile(client):
    assert authmon(client, "view").get_data(as_text=True) == "*"


def test_view_renvoie_la_ligne_encodee_sans_la_supprimer(client):
    accept(client)
    body = authmon(client, "view").get_data(as_text=True)
    assert body.startswith("* ")
    assert unquote(body[2:]).split(" ")[0] == RHID
    assert PendingAuth.query.count() == 1


def test_ack_supprime_le_rhid_acquitte(client):
    accept(client)
    assert authmon(client, "view", payload=f"* {RHID}").get_data(as_text=True) == "ack"
    assert PendingAuth.query.count() == 0


def test_ack_vide_garde_la_file(client):
    accept(client)
    assert authmon(client, "view", payload="*").get_data(as_text=True) == "ack"
    assert PendingAuth.query.count() == 1


def test_list_renvoie_puis_vide(client):
    accept(client)
    assert authmon(client, "list").get_data(as_text=True).startswith("* ")
    assert PendingAuth.query.count() == 0


def test_clear_vide_la_file(client):
    accept(client)
    assert authmon(client, "clear").status_code == 200
    assert PendingAuth.query.count() == 0

def test_view_purge_les_autorisations_perimees(client):
    """Une autorisation jamais acquittée au-delà du TTL est purgée, une fraîche survit."""
    stale_rhid = "c" * 64
    fresh_rhid = "d" * 64

    # Préparer : une ligne trop vieille et une ligne fraîche, même passerelle
    db.session.add(PendingAuth(
        gateway_hash=GW,
        rhid=stale_rhid,
        line=build_auth_line(stale_rhid),
        created_at=now_utc() - PENDING_AUTH_TTL - timedelta(seconds=1),
    ))
    db.session.add(PendingAuth(
        gateway_hash=GW,
        rhid=fresh_rhid,
        line=build_auth_line(fresh_rhid),
    ))
    db.session.commit()

    # Agir : authmon demande "qui dois-je ouvrir ?"
    response = authmon(client, "view")
    body = response.get_data(as_text=True)

    # Vérifier
    assert stale_rhid not in body
    assert fresh_rhid in body
    remaining = db.session.execute(db.select(PendingAuth.rhid)).scalars().all()
    assert remaining == [fresh_rhid]

def test_variante_get_utilisee_par_wget(client):
    accept(client)
    assert authmon(client, "view", method="get").get_data(as_text=True).startswith("* ")


def test_deauthed_est_acquitte(client):
    assert authmon(client, "deauthed", payload="donnees client").get_data(as_text=True) == "ack"


def test_passerelle_inconnue_refusee_et_ne_voit_rien(client):
    accept(client)
    response = authmon(client, "view", gw="0" * 64)
    assert response.status_code == 403
    assert RHID not in response.get_data(as_text=True)


def test_gatewayhash_vide_ou_mal_forme_refuse_en_403(client):
    assert authmon(client, "view", gw="").status_code == 403
    assert authmon(client, "view", gw="pas-un-sha256").status_code == 403


def test_auth_get_inconnu_renvoie_400(client):
    assert authmon(client, "inconnu").status_code == 400


def test_ack_d_une_autre_passerelle_ne_supprime_rien(client):
    """Une passerelle n'acquitte que ses propres lignes : isolation entre restaurants."""
    accept(client)
    assert authmon(client, "view", payload=f"* {RHID}", gw=OTHER_GW).get_data(as_text=True) == "ack"
    assert PendingAuth.query.count() == 1


def test_ack_de_deux_rhid_supprime_les_deux(client):
    """Cas où le PHP de référence échoue : plusieurs clients ouverts dans le même cycle."""
    other_hid = "b" * 64
    other_rhid = hashlib.sha256((other_hid + KEY).encode()).hexdigest()
    accept(client)
    accept(client, hid=other_hid)
    assert PendingAuth.query.count() == 2
    authmon(client, "view", payload=f"* {RHID} {other_rhid}")
    assert PendingAuth.query.count() == 0


def test_payload_non_base64_sur_view_renvoie_la_file_sans_supprimer(client):
    accept(client)
    response = authmon(client, "view", raw_payload="!!! pas du base64 !!!")
    assert response.status_code == 200
    assert response.get_data(as_text=True).startswith("* ")
    assert PendingAuth.query.count() == 1


def test_view_ne_renvoie_que_quatre_lignes_par_cycle(client):
    """authmon ne traite que 4 clients par cycle : inutile d'en envoyer plus."""
    for i in range(5):
        accept(client, hid=str(i) * 64)
    body = authmon(client, "view").get_data(as_text=True)
    assert len(body[2:].split(" ")) == 4
    assert PendingAuth.query.count() == 5


def test_deauthed_ne_journalise_pas_le_payload(client, caplog):
    """Exigence CNIL : le payload contient la MAC et le jeton du client, il ne doit jamais être logué."""
    caplog.set_level(logging.INFO, logger="app")
    authmon(client, "deauthed", payload="clientmac=aa:bb:cc:dd:ee:ff, token=jeton-secret")
    assert "deauthed" in caplog.text
    assert "aa:bb:cc" not in caplog.text
    assert "jeton-secret" not in caplog.text


def test_acceptation_depuis_une_autre_passerelle_refusee(client):
    response = client.post("/fas/accept", data={"fas": make_fas(gatewayname="Autre%20Resto"), "terms": "on"})
    assert response.status_code == 403
    assert PendingAuth.query.count() == 0
