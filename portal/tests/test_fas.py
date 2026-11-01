"""Tests du protocole FAS, sans Flask ni base."""
import base64
import hashlib

import pytest

from app.fas import (
    FasError,
    build_auth_line,
    compute_rhid,
    encode_auth_list,
    gateway_hash,
    parse_fas,
)

HID = "a" * 64
KEY = "0123456789abcdef" * 4


def make_fas(**overrides) -> str:
    """Construit un paramètre fas comme le ferait openNDS niveau 4."""
    params = {
        "hid": HID,
        "clientip": "10.20.0.42",
        "clientmac": "aa:bb:cc:dd:ee:ff",
        "client_type": "cpd_can",
        "cpi_query": "",
        "gatewayname": "Coeur%20de%20Beurre",
        "gatewayurl": "http%3A%2F%2F10.20.0.1%3A2050%2F",
        "version": "10.3.1",
        "gatewayaddress": "10.20.0.1:2050",
        "gatewaymac": "94:83:c4:00:00:01",
        "originurl": "http%3A%2F%2Fexample.com%2F",
        "clientif": "wlan0",
        "themespec": "",
        "resto": "coeur-de-beurre",
    }
    params.update(overrides)
    raw = ", ".join(f"{k}={v}" for k, v in params.items())
    return base64.b64encode(raw.encode()).decode()


def test_parse_fas_retourne_les_champs_utiles():
    p = parse_fas(make_fas())
    assert p["hid"] == HID
    assert p["clientip"] == "10.20.0.42"
    assert p["clientmac"] == "aa:bb:cc:dd:ee:ff"
    assert p["gatewayname"] == "Coeur%20de%20Beurre"
    assert p["resto"] == "coeur-de-beurre"


def test_parse_fas_rejette_un_hid_invalide():
    with pytest.raises(FasError):
        parse_fas(make_fas(hid="pas-un-sha256"))


def test_parse_fas_rejette_un_base64_cassé():
    with pytest.raises(FasError):
        parse_fas("ceci n'est pas du base64 !!")


def test_parse_fas_rejette_le_vide():
    with pytest.raises(FasError):
        parse_fas("")


def test_rhid_est_sha256_de_hid_plus_cle():
    attendu = hashlib.sha256((HID + KEY).encode()).hexdigest()
    assert compute_rhid(HID, KEY) == attendu
    assert len(compute_rhid(HID, KEY)) == 64


def test_rhid_change_si_la_cle_change():
    assert compute_rhid(HID, KEY) != compute_rhid(HID, KEY + "x")


def test_gateway_hash_hache_la_valeur_encodee_telle_quelle():
    nom = "Coeur%20de%20Beurre"
    assert gateway_hash(nom) == hashlib.sha256(nom.encode()).hexdigest()


def test_build_auth_line_format_et_defauts():
    ligne = build_auth_line("r" * 64, custom="resto=coeur-de-beurre")
    champs = ligne.split(" ")
    assert len(champs) == 7
    assert champs[0] == "r" * 64
    assert champs[1:6] == ["240", "2000", "8000", "0", "0"]
    assert base64.b64decode(champs[6]).decode() == "resto=coeur-de-beurre"


def test_build_auth_line_sans_custom_a_six_champs():
    assert len(build_auth_line("r" * 64).split(" ")) == 6


def test_encode_auth_list_vide():
    assert encode_auth_list([]) == "*"


def test_encode_auth_list_encode_les_espaces_en_pourcent_20():
    ligne = build_auth_line("r" * 64)
    reponse = encode_auth_list([ligne])
    assert reponse.startswith("* ")
    assert " " not in reponse[2:]
    assert "%20" in reponse
    # authmon décode les %20 et retrouve la ligne d'origine
    from urllib.parse import unquote
    assert unquote(reponse[2:]) == ligne