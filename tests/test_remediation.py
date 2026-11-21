"""Tests complets de validation et de sécurité pour SmartCampus AI (Section 8)."""
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Conversation, Role, User, VisitorSession
from app.services import cleanup_expired_sessions, login_limiter
from .conftest import ADMIN, H


def _admin(c):
    return c.post("/auth/login", json=ADMIN).json()["access_token"]


def _candidate(c, email: str, session: str | None = None) -> dict:
    r = c.post("/auth/register", json={"email": email, "password": "Password123!"}, headers=H(session=session))
    assert r.status_code == 201, r.text
    return r.json()


# =====================================================================
# 1. Authentification & Sécurité des Tokens JWT
# =====================================================================

def test_jwt_malformed_and_invalid_subject(c):
    """Rejet strict des tokens malformés, falsifiés, ou ayant un UUID sub invalide."""
    assert c.get("/auth/me", headers={"Authorization": "Bearer not-even-a-jwt"}).status_code == 401
    assert c.get("/auth/me", headers={"Authorization": "Bearer a.b.c"}).status_code == 401

    # Token avec un sub non-UUID
    invalid_sub_tok = jwt.encode(
        {"sub": "not-a-uuid", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    assert c.get("/auth/me", headers=H(invalid_sub_tok)).status_code == 401

    # Token sans sub
    no_sub_tok = jwt.encode(
        {"role": "admin", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    assert c.get("/auth/me", headers=H(no_sub_tok)).status_code == 401

    # Token signé avec un secret différent
    forged_tok = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
        "wrong-secret-key-that-does-not-match-at-all",
        algorithm=settings.jwt_algorithm
    )
    assert c.get("/auth/me", headers=H(forged_tok)).status_code == 401


def test_jwt_expired_token(c):
    """Rejet des tokens JWT dont la date d'expiration est dépassée."""
    cand = _candidate(c, "expired_cand@test.tn")
    expired_tok = jwt.encode(
        {"sub": cand["user"]["id"], "exp": datetime.now(timezone.utc) - timedelta(seconds=10)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    assert c.get("/auth/me", headers=H(expired_tok)).status_code == 401


def test_disabled_account_cannot_authenticate(c):
    """Un utilisateur désactivé voit ses requêtes avec token existant et son login refusés."""
    adm = _admin(c)
    cand = _candidate(c, "tobedeactivated@test.tn")
    cand_tok = cand["access_token"]
    user_id = cand["user"]["id"]

    # Accès normal initial
    assert c.get("/auth/me", headers=H(cand_tok)).status_code == 200

    # Désactivation par l'admin
    r_patch = c.patch(f"/admin/users/{user_id}", json={"is_active": False}, headers=H(adm))
    assert r_patch.status_code == 200
    assert r_patch.json()["is_active"] is False

    # Le token existant est désormais rejeté
    assert c.get("/auth/me", headers=H(cand_tok)).status_code == 401
    # La tentative de reconnexion est rejetée
    assert c.post("/auth/login", json={"email": "tobedeactivated@test.tn", "password": "Password123!"}).status_code == 401


# =====================================================================
# 2. Protection de l'administrateur
# =====================================================================

def test_last_active_admin_protection(c):
    """Le système empêche la désactivation du dernier administrateur actif."""
    adm = _admin(c)
    # Récupérer l'ID de l'admin principal
    me = c.get("/auth/me", headers=H(adm)).json()
    admin_id = me["id"]

    # Tentative d'auto-désactivation -> 400
    r = c.patch(f"/admin/users/{admin_id}", json={"is_active": False}, headers=H(adm))
    assert r.status_code == 400
    assert "son propre compte" in r.json()["detail"]

    # Création d'un second administrateur
    r_new_adm = c.post("/admin/users", json={
        "email": "admin2@smartcampus.tn",
        "password": "Password123!",
        "full_name": "Admin 2",
        "role": "admin"
    }, headers=H(adm))
    assert r_new_adm.status_code == 201
    admin2_id = r_new_adm.json()["id"]

    # L'admin 1 peut maintenant désactiver l'admin 2
    r_deact = c.patch(f"/admin/users/{admin2_id}", json={"is_active": False}, headers=H(adm))
    assert r_deact.status_code == 200
    assert r_deact.json()["is_active"] is False

    # Mais maintenant qu'admin 2 est inactif, l'admin 1 est à nouveau le seul admin actif
    # Si on tente de le désactiver (par ex via un appel tiers), cela doit échouer
    r_last = c.patch(f"/admin/users/{admin_id}", json={"is_active": False}, headers=H(adm))
    assert r_last.status_code == 400


# =====================================================================
# 3. Rate Limiting (Brute-Force & Abus)
# =====================================================================

def test_registration_rate_limiting(c):
    """Protection anti-création massive de comptes candidats par IP."""
    # Créer plusieurs comptes jusqu'à la limite autorisée par fenêtre
    for i in range(settings.register_ip_max_attempts):
        r = c.post("/auth/register", json={"email": f"spam_{i}@test.tn", "password": "Password123!"})
        assert r.status_code == 201

    # La tentative suivante doit être bloquée avec 429 et Retry-After
    r_blocked = c.post("/auth/register", json={"email": "spam_blocked@test.tn", "password": "Password123!"})
    assert r_blocked.status_code == 429
    assert "Retry-After" in r_blocked.headers


def test_reverse_proxy_forwarded_for_handling(c):
    """Gestion correcte de l'adresse IP cliente derrière un reverse proxy de confiance."""
    login_limiter.clear_all()
    bad_login = {"email": "proxy_victim@test.tn", "password": "wrongpassword"}

    # Requête avec X-Forwarded-For provenant du proxy de confiance 127.0.0.1
    headers = {"X-Forwarded-For": "203.0.113.195, 127.0.0.1"}

    for _ in range(settings.login_max_attempts):
        r = c.post("/auth/login", json=bad_login, headers=headers)
        assert r.status_code == 401

    # Doit être bloqué pour cette IP cliente
    r_blocked = c.post("/auth/login", json=bad_login, headers=headers)
    assert r_blocked.status_code == 429
    assert "Retry-After" in r_blocked.headers


# =====================================================================
# 4. Validation des Données, Numériques et Année Universitaire
# =====================================================================

def test_academic_year_validation(c):
    """Validation stricte de la cohérence de l'année universitaire (fin = début + 1)."""
    adm = _admin(c)
    p = {"slug": "genie-logiciel", "institution": "IIT", "level": "Ingenierie", "name": "Génie Logiciel"}
    assert c.post("/programs", json=p, headers=H(adm)).status_code == 201

    # Année valide (2026-2027)
    r_ok = c.post("/programs/genie-logiciel/tariffs", headers=H(adm), json={
        "academic_year": "2026-2027",
        "amount": 5500.00
    })
    assert r_ok.status_code == 201

    # Années invalides : non consécutives, inversées ou mal formées -> 422
    for bad_year in ["2026-2026", "2026-2028", "2025-2024", "abcd-efgh", "2026/2027"]:
        r_bad = c.post("/programs/genie-logiciel/tariffs", headers=H(adm), json={
            "academic_year": bad_year,
            "amount": 5000.00
        })
        assert r_bad.status_code == 422, f"Attendu 422 pour {bad_year}, reçu {r_bad.status_code}"


def test_monetary_precision_and_numeric_overflow_prevention(c):
    """Alignement Pydantic / PostgreSQL Numeric(10,2) pour prévenir les débordements."""
    adm = _admin(c)
    # Montant excessif (dépasse precision 10 de Numeric(10, 2)) -> rejeté 422 proprement au lieu de 500
    r_overflow = c.post("/programs/genie-logiciel/tariffs", headers=H(adm), json={
        "academic_year": "2027-2028",
        "amount": 99999999999999.99
    })
    assert r_overflow.status_code == 422

    # Montant avec plus de 2 décimales -> rejeté 422
    r_decimal = c.post("/programs/genie-logiciel/tariffs", headers=H(adm), json={
        "academic_year": "2027-2028",
        "amount": 5000.1234
    })
    assert r_decimal.status_code == 422

    # Moyenne minimale (Numeric(4,2), max 20)
    r_avg_overflow = c.post("/programs/genie-logiciel/admission-conditions", headers=H(adm), json={
        "title": "Bac",
        "min_average": 21.00
    })
    assert r_avg_overflow.status_code == 422

    r_avg_negative = c.post("/programs/genie-logiciel/admission-conditions", headers=H(adm), json={
        "title": "Bac",
        "min_average": -1.00
    })
    assert r_avg_negative.status_code == 422


def test_empty_and_whitespace_only_strings_rejected(c):
    """Rejet des champs vides ou constitués exclusivement d'espaces blancs."""
    adm = _admin(c)
    # Programme avec titre en espaces
    r_prog = c.post("/programs", headers=H(adm), json={
        "slug": "prog-whitespace",
        "institution": "IIT",
        "level": "   ",
        "name": "   "
    })
    assert r_prog.status_code == 422

    # Condition avec titre vide
    r_cond = c.post("/programs/genie-logiciel/admission-conditions", headers=H(adm), json={
        "title": "    "
    })
    assert r_cond.status_code == 422


# =====================================================================
# 5. Pagination & Filtrage Base de Données
# =====================================================================

def test_pagination_admin_users_and_conversations(c):
    """Pagination fonctionnelle sur les collections potentiellement volumineuses."""
    adm = _admin(c)
    # Vérification pagination utilisateurs admin
    r_users = c.get("/admin/users", params={"limit": 2, "offset": 0}, headers=H(adm))
    assert r_users.status_code == 200
    assert len(r_users.json()) <= 2

    r_users_page2 = c.get("/admin/users", params={"limit": 2, "offset": 2}, headers=H(adm))
    assert r_users_page2.status_code == 200

    # Vérification pagination conversations candidat
    cand = _candidate(c, "paginated_user@test.tn")
    sess = c.post("/sessions").json()["session_token"]
    for i in range(5):
        c.post("/conversations", json={"title": f"Conv {i}"}, headers=H(cand["access_token"], sess))

    r_conv1 = c.get("/conversations", params={"limit": 2, "offset": 0}, headers=H(cand["access_token"]))
    assert r_conv1.status_code == 200
    assert len(r_conv1.json()) == 2

    r_conv2 = c.get("/conversations", params={"limit": 2, "offset": 2}, headers=H(cand["access_token"]))
    assert r_conv2.status_code == 200
    assert len(r_conv2.json()) == 2
    # Les identifiants des pages doivent être disjoints
    ids_p1 = {item["id"] for item in r_conv1.json()}
    ids_p2 = {item["id"] for item in r_conv2.json()}
    assert ids_p1.isdisjoint(ids_p2)


def test_database_level_tariffs_filtering(c):
    """Filtrage des tarifs par année académique au niveau SQL."""
    adm = _admin(c)
    # Ajouter deux tarifs distincts
    c.post("/programs/genie-logiciel/tariffs", headers=H(adm), json={"academic_year": "2028-2029", "amount": 6000.00})
    c.post("/programs/genie-logiciel/tariffs", headers=H(adm), json={"academic_year": "2029-2030", "amount": 6500.00})

    # Filtrage par 2028-2029
    r_filtered = c.get("/programs/genie-logiciel/tariffs", params={"academic_year": "2028-2029"})
    assert r_filtered.status_code == 200
    data = r_filtered.json()
    assert len(data) == 1
    assert data[0]["academic_year"] == "2028-2029"


# =====================================================================
# 6. Rétention des Données & Cycle de Vie des Sessions
# =====================================================================

def test_expired_session_cleanup(c):
    """Le mécanisme de purge supprime les sessions anonymes expirées non liées."""
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        old_expired = now - timedelta(days=15)
        # Session anonyme expirée depuis 15 jours
        s1 = VisitorSession(token_hash="hash_old_expired", created_at=old_expired, last_seen_at=old_expired, expires_at=old_expired)
        # Session active
        s2 = VisitorSession(token_hash="hash_active", created_at=now, last_seen_at=now, expires_at=now + timedelta(hours=24))
        db.add_all([s1, s2])
        db.commit()

        # Exécuter le nettoyage avec rétention de 7 jours
        deleted = cleanup_expired_sessions(db, retention_days=7)
        assert deleted >= 1

        # Vérifier que s1 est supprimée et s2 est conservée
        assert db.get(VisitorSession, s1.id) is None
        assert db.get(VisitorSession, s2.id) is not None


def test_session_max_absolute_lifetime_enforcement(c):
    """Une session ne peut pas être prolongée au-delà de sa durée de vie maximale absolue."""
    with SessionLocal() as db:
        old_date = datetime.now(timezone.utc) - timedelta(days=settings.session_max_ttl_days + 1)
        # Session créée il y a 31 jours mais dont expires_at a été glissé
        vs = VisitorSession(
            token_hash="hash_over_max_ttl",
            created_at=old_date,
            last_seen_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=10)
        )
        db.add(vs)
        db.commit()
        sid = vs.id

    # En accédant avec ce jeton, il doit être considéré expiré car > session_max_ttl_days
    # On simule un token dont le hash correspond
    with patch("app.deps.hash_token", return_value="hash_over_max_ttl"):
        r = c.get("/sessions/me", headers={"X-Session-Token": "test-token"})
        assert r.status_code == 401


# =====================================================================
# 7. Sondes de Santé (Health, Live, Ready) & Observabilité
# =====================================================================

def test_liveness_and_readiness_probes(c):
    """Vérification des sondes de vivacité et de préparation."""
    # Liveness
    r_live = c.get("/health/live")
    assert r_live.status_code == 200
    assert r_live.json() == {"status": "alive"}

    # Readiness (BDD connectée)
    r_ready = c.get("/health/ready")
    assert r_ready.status_code == 200
    assert r_ready.json() == {"status": "ready", "database": "connected"}


def test_readiness_probe_database_unreachable(c):
    """La sonde de préparation renvoie 503 Service Unavailable si la base est injoignable."""
    with patch("app.main.SessionLocal", side_effect=Exception("Database connection timeout")):
        r = c.get("/health/ready")
        assert r.status_code == 503
        assert r.json() == {"status": "not ready", "database": "disconnected"}


def test_request_id_middleware(c):
    """Chaque réponse HTTP contient un en-tête X-Request-ID pour la traçabilité."""
    r = c.get("/programs")
    assert "X-Request-ID" in r.headers
    custom_id = "test-custom-req-id-12345"
    r_custom = c.get("/programs", headers={"X-Request-ID": custom_id})
    assert r_custom.headers["X-Request-ID"] == custom_id
