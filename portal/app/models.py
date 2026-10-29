"""Modèle de données du portail.

Règle CNIL : les journaux légaux ne contiennent que des données techniques
(IP, MAC, dates). Jamais de contenu, de site visité ni de requête DNS.
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now_utc():
    return datetime.now(timezone.utc)


class Restaurant(db.Model):
    """Un établissement équipé. Ses couleurs et liens pour le portail."""
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    primary_color = db.Column(db.String(7), default="#c0392b")
    google_reviews_url = db.Column(db.String(300))
    gateway_id = db.Column(db.String(64), unique=True)  # identifiant openNDS de la passerelle
    created_at = db.Column(db.DateTime(timezone=True), default=now_utc)

    sessions = db.relationship("ConnectionSession", back_populates="restaurant")


class ConnectionSession(db.Model):
    """Une authentification réussie sur le portail. Sert aux statistiques."""
    __tablename__ = "connection_sessions"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    client_hid = db.Column(db.String(128), nullable=False)  # identifiant haché fourni par openNDS
    started_at = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)
    accepted_terms = db.Column(db.Boolean, default=True, nullable=False)

    restaurant = db.relationship("Restaurant", back_populates="sessions")


class LegalLog(db.Model):
    """Journal légal : conservé 1 an puis purgé. Données techniques uniquement."""
    __tablename__ = "legal_logs"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    client_ip = db.Column(db.String(45), nullable=False)      # IPv4 ou IPv6
    client_port = db.Column(db.Integer)
    client_mac = db.Column(db.String(17), nullable=False)
    connected_at = db.Column(db.DateTime(timezone=True), nullable=False)
    disconnected_at = db.Column(db.DateTime(timezone=True))
    purge_after = db.Column(db.DateTime(timezone=True), nullable=False)  # connected_at + 1 an


class NewsletterConsent(db.Model):
    """E-mail laissé volontairement par un client. Stocké à part des journaux."""
    __tablename__ = "newsletter_consents"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    consented_at = db.Column(db.DateTime(timezone=True), default=now_utc, nullable=False)
