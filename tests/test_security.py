"""Tests de sécurité et de robustesse (correctifs de la revue de code)."""
import threading

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from .conftest import ADMIN, H, IS_SQLITE


def _admin(c):
    return c.post("/auth/login", json=ADMIN).json()["access_token"]


def _candidate(c, email, session=None):
    r = c.post("/auth/register", json={"email": email, "password": "motdepasse1"}, headers=H(session=session))
    assert r.status_code == 201
    return r.json()


# ---------- Configuration de production ----------
def test_production_refuses_default_secrets():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", jwt_secret="x" * 40)  # mdp admin par défaut
    ok = Settings(_env_file=None, environment="production", jwt_secret="x" * 40,
                  admin_password="Un-Mot-De-Passe-Solide-1")
    assert ok.environment == "production"
    Settings(_env_file=None)  # dev : les défauts restent acceptés


# ---------- SA-29 : rattachement immuable ----------
def test_session_cannot_be_reassigned(c):
    sess = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={"title": "a"}, headers=H(session=sess)).json()
    a = _candidate(c, "a@test.tn", sess)
    assert a["linked_conversations"] == 1

    # un second compte tente de récupérer la même session
    b = _candidate(c, "b@test.tn")  # inscription sans session
    r = c.post("/sessions/link", headers=H(b["access_token"], sess))
    assert r.status_code == 409
    # via login : pas de rattachement, mais le login réussit
    r = c.post("/auth/login", json={"email": "b@test.tn", "password": "motdepasse1"}, headers=H(session=sess))
    assert r.status_code == 200 and r.json()["linked_conversations"] == 0
    # via register avec la session déjà prise : compte créé, 0 conversation rattachée
    r = c.post("/auth/register", json={"email": "c@test.tn", "password": "motdepasse1"}, headers=H(session=sess))
    assert r.status_code == 201 and r.json()["linked_conversations"] == 0

    # la conversation reste à A
    assert c.get(f"/conversations/{conv['id']}", headers=H(a["access_token"])).json()["user_id"] == a["user"]["id"]
    # B ne la voit pas ; JWT de B + session de A est refusé
    assert c.get(f"/conversations/{conv['id']}", headers=H(b["access_token"])).status_code == 404
    assert c.get("/conversations", headers=H(b["access_token"], sess)).status_code == 403
    assert c.post("/conversations", json={}, headers=H(b["access_token"], sess)).status_code == 403
    # re-lier au même compte reste idempotent
    assert c.post("/sessions/link", headers=H(a["access_token"], sess)).status_code == 200


def test_conversation_isolation_between_visitors(c):
    s1 = c.post("/sessions").json()["session_token"]
    s2 = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={}, headers=H(session=s1)).json()
    assert c.get(f"/conversations/{conv['id']}", headers=H(session=s2)).status_code == 404
    assert c.get("/conversations", headers=H(session=s2)).json() == []
    assert c.get(f"/conversations/{conv['id']}").status_code == 401 or \
        c.get(f"/conversations/{conv['id']}").status_code == 404


def test_admin_not_linked(c):
    adm = _admin(c)
    sess = c.post("/sessions").json()["session_token"]
    assert c.post("/sessions/link", headers=H(adm, sess)).status_code in (403,)  # réservé aux candidats


# ---------- PATCH : null interdit sur colonnes NOT NULL ----------
def test_patch_null_rejected_cleanly(c):
    adm = _admin(c)
    p = {"slug": "prepa-integree", "institution": "IIT", "level": "Prepa", "name": "Prépa intégrée"}
    assert c.post("/programs", json=p, headers=H(adm)).status_code == 201
    assert c.patch("/programs/prepa-integree", json={"name": None}, headers=H(adm)).status_code == 422
    assert c.patch("/programs/prepa-integree", json={"is_active": None}, headers=H(adm)).status_code == 422
    # champ nullable : accepté
    assert c.patch("/programs/prepa-integree", json={"duration_years": None}, headers=H(adm)).status_code == 200
    # champ omis : inchangé
    assert c.patch("/programs/prepa-integree", json={"description": "ok"}, headers=H(adm)).json()["name"] == "Prépa intégrée"

    cid = c.post("/programs/prepa-integree/admission-conditions", headers=H(adm),
                 json={"title": "Bac maths", "min_average": 12}).json()["id"]
    assert c.patch(f"/admission-conditions/{cid}", json={"title": None}, headers=H(adm)).status_code == 422
    assert c.patch(f"/admission-conditions/{cid}", json={"min_average": None}, headers=H(adm)).status_code == 200
    assert c.patch(f"/admission-conditions/{cid}", json={"min_average": 25}, headers=H(adm)).status_code == 422

    tid = c.post("/programs/prepa-integree/tariffs", headers=H(adm),
                 json={"academic_year": "2026-2027", "amount": 3000}).json()["id"]
    assert c.patch(f"/tariffs/{tid}", json={"amount": None}, headers=H(adm)).status_code == 422
    assert c.patch(f"/tariffs/{tid}", json={"amount": -1}, headers=H(adm)).status_code == 422
    assert c.patch(f"/tariffs/{tid}", json={"payment_terms": None}, headers=H(adm)).status_code == 200
    assert c.post("/programs/prepa-integree/tariffs", headers=H(adm),
                  json={"academic_year": "2026-2027", "amount": 1}).status_code == 409


# ---------- Limitation des tentatives ----------
def test_login_rate_limit(c):
    bad = {"email": "limit@test.tn", "password": "faux"}
    for _ in range(5):
        assert c.post("/auth/login", json=bad).status_code == 401
    r = c.post("/auth/login", json=bad)
    assert r.status_code == 429 and "Retry-After" in r.headers
    # un autre email n'est pas bloqué, et le bon mot de passe de l'admin passe toujours
    assert c.post("/auth/login", json=ADMIN).status_code == 200


def test_login_success_resets_counter(c):
    _candidate(c, "reset@test.tn")
    bad = {"email": "reset@test.tn", "password": "faux"}
    for _ in range(4):
        c.post("/auth/login", json=bad)
    assert c.post("/auth/login", json={"email": "reset@test.tn", "password": "motdepasse1"}).status_code == 200
    for _ in range(4):
        assert c.post("/auth/login", json=bad).status_code == 401


# ---------- Autorisations ----------
def test_unauthorized_access(c):
    adm = _admin(c)
    cand = _candidate(c, "cand@test.tn")["access_token"]
    assert c.get("/admin/users").status_code == 401
    assert c.get("/admin/users", headers=H(cand)).status_code == 403
    assert c.post("/admin/users", json={"email": "z@test.tn", "password": "motdepasse1", "role": "admin"},
                  headers=H(cand)).status_code == 403
    assert c.get("/auth/me", headers={"Authorization": "Bearer pas.un.jwt"}).status_code == 401
    # compte désactivé : le jeton existant ne fonctionne plus
    uid = c.get("/auth/me", headers=H(cand)).json()["id"]
    assert c.patch(f"/admin/users/{uid}", json={"is_active": False}, headers=H(adm)).status_code == 200
    assert c.get("/auth/me", headers=H(cand)).status_code == 401
    assert c.post("/auth/login", json={"email": "cand@test.tn", "password": "motdepasse1"}).status_code == 401
    # un admin ne peut pas se désactiver lui-même
    aid = c.get("/auth/me", headers=H(adm)).json()["id"]
    assert c.patch(f"/admin/users/{aid}", json={"is_active": False}, headers=H(adm)).status_code == 400


def test_jwt_forged_role_is_ignored(c):
    """Le rôle vient de la base, pas du jeton : un JWT signé avec le bon secret mais role=admin ne suffit pas."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.config import settings
    cand = _candidate(c, "forge@test.tn")
    tok = jwt.encode({"sub": cand["user"]["id"], "role": "admin",
                      "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                     settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert c.get("/admin/users", headers=H(tok)).status_code == 403
    expired = jwt.encode({"sub": cand["user"]["id"], "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert c.get("/auth/me", headers=H(expired)).status_code == 401


# ---------- Concurrence : 409 et jamais 500 ----------
@pytest.mark.skipif(IS_SQLITE, reason="concurrence significative uniquement sur PostgreSQL")
def test_concurrent_duplicate_slug_and_email(c):
    adm = _admin(c)
    results = []

    def make_program():
        with TestClient(app, raise_server_exceptions=False) as cl:
            results.append(("prog", cl.post("/programs", headers=H(adm), json={
                "slug": "course-race", "institution": "ISB", "level": "licence", "name": "Race"}).status_code))

    def make_user():
        with TestClient(app, raise_server_exceptions=False) as cl:
            results.append(("user", cl.post("/auth/register", json={
                "email": "race@test.tn", "password": "motdepasse1"}).status_code))

    threads = [threading.Thread(target=f) for f in (make_program, make_user) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    for kind in ("prog", "user"):
        codes = [code for k, code in results if k == kind]
        assert codes.count(201) == 1, codes
        assert set(codes) <= {201, 409}, codes


# ---------- Formats de connexion ----------
def test_login_formats(c):
    # JSON : email + password
    r = c.post("/auth/login", json=ADMIN)
    assert r.status_code == 200 and r.json()["user"]["role"] == "admin"
    # validation : champ manquant / email invalide → 422
    assert c.post("/auth/login", json={"password": "x"}).status_code == 422
    assert c.post("/auth/login", json={"email": "pas-un-email", "password": "x"}).status_code == 422
    # l'ancien format formulaire n'est plus accepté sur /auth/login
    assert c.post("/auth/login", data={"username": ADMIN["email"], "password": ADMIN["password"]}).status_code == 422
    # formulaire OAuth2 (bouton Authorize de Swagger) : /auth/token, caché de la doc
    r = c.post("/auth/token", data={"username": ADMIN["email"], "password": ADMIN["password"]})
    assert r.status_code == 200 and r.json()["access_token"]
    assert c.post("/auth/token", data={"username": ADMIN["email"], "password": "faux"}).status_code == 401
    assert "/auth/token" not in c.get("/openapi.json").json()["paths"]
    assert c.get("/openapi.json").json()["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]["tokenUrl"] == "auth/token"
