"""Fixtures communes pour la suite de tests SmartCampus AI.
PostgreSQL (base smartcampus_test) est l'environnement d'intégration prioritaire.
"""
import os

# Configuration de l'environnement de test prioritaire sur PostgreSQL
_default_db = "postgresql+psycopg://smartcampus:smartcampus@127.0.0.1:5433/smartcampus_test"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _default_db)
os.environ["ENVIRONMENT"] = "test"
os.environ["ADMIN_EMAIL"] = "admin@smartcampus.tn"
os.environ["ADMIN_PASSWORD"] = "ChangeMe123!"
os.environ["JWT_SECRET"] = "dev-secret-change-me-please-use-32-bytes-min"
os.environ["LOGIN_MAX_ATTEMPTS"] = "5"
os.environ["LOGIN_WINDOW_SECONDS"] = "300"
os.environ["LOGIN_IP_MAX_ATTEMPTS"] = "25"
os.environ["REGISTER_IP_MAX_ATTEMPTS"] = "10"
os.environ["REGISTER_WINDOW_SECONDS"] = "900"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.services import login_limiter

IS_SQLITE = engine.dialect.name == "sqlite"


@pytest.fixture(scope="module")
def c():
    """Fournit une base de données propre avec tables et compte admin initialisé pour chaque module."""
    Base.metadata.drop_all(engine)
    with TestClient(app) as client:
        yield client
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Réinitialise les compteurs de rate limiting avant et après chaque test."""
    login_limiter.clear_all()
    yield
    login_limiter.clear_all()


def H(token: str | None = None, session: str | None = None) -> dict[str, str]:
    """Helper pour construire les en-têtes d'authentification."""
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if session:
        headers["X-Session-Token"] = session
    return headers


ADMIN = {"email": "admin@smartcampus.tn", "password": "ChangeMe123!"}
