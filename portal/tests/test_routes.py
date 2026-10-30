"""Tests des routes de base."""
from app import create_app


def test_health_repond_ok():
    client = create_app().test_client()
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.get_json() == {"status": "ok"}


def test_index_affiche_le_restaurant():
    client = create_app().test_client()
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "Restaurant de test" in reponse.get_data(as_text=True)
