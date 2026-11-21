"""Tests d'intégration pour le module Candidatures (SA-13).

Couvre :
  - Dépôt de candidature (candidat)
  - Unicité (user, program, year) → 409
  - Consultation de ses candidatures
  - Accès refusé à la candidature d'un autre utilisateur
  - Retrait d'une candidature en statut draft
  - Retrait impossible en statut non-draft
  - Flux admin : liste, détail enrichi, changement de statut, suppression
  - Formation inactive → 404
  - Formats d'année académique invalides → 422
  - Accès aux routes admin refusé aux candidats
"""
import pytest
from fastapi.testclient import TestClient

from tests.conftest import ADMIN, H

# ─────────────────────────── constantes ─────────────────────────────

CANDIDAT_A = {"email": "app_cand_a@test.tn", "password": "Password123!", "full_name": "Candidat A"}
CANDIDAT_B = {"email": "app_cand_b@test.tn", "password": "Password123!", "full_name": "Candidat B"}

PROGRAM_PAYLOAD = {
    "slug": "licence-info-sa13",
    "institution": "IIT",
    "level": "licence",
    "name": "Licence Informatique SA13",
    "description": "Formation de test SA-13",
    "duration_years": 3,
    "language": "fr",
    "careers": "Développeur",
    "is_active": True,
}

YEAR = "2026-2027"

# État partagé entre tests du même module (module-scope)
STATE: dict = {}


def _login(c: TestClient, email: str, password: str) -> str:
    r = c.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.json()}"
    return r.json()["access_token"]


# ─────────────────────── Fixture module-scope ────────────────────────

@pytest.fixture(scope="module", autouse=True)
def setup_state(c: TestClient):
    """Initialise les tokens, la formation et vide STATE entre modules."""
    # Enregistrement des candidats (register retourne 201)
    for payload in (CANDIDAT_A, CANDIDAT_B):
        r = c.post("/auth/register", json=payload)
        assert r.status_code in (201, 409), r.json()

    STATE["admin_token"] = _login(c, ADMIN["email"], ADMIN["password"])
    STATE["token_a"] = _login(c, CANDIDAT_A["email"], CANDIDAT_A["password"])
    STATE["token_b"] = _login(c, CANDIDAT_B["email"], CANDIDAT_B["password"])

    # Création de la formation de test
    r = c.post("/programs", json=PROGRAM_PAYLOAD, headers=H(STATE["admin_token"]))
    assert r.status_code in (201, 409), r.json()

    r = c.get(f"/programs/{PROGRAM_PAYLOAD['slug']}")
    assert r.status_code == 200, r.json()
    STATE["program_id"] = r.json()["id"]
    STATE["app_id"] = None


# ═══════════════════════════ Dépôt ══════════════════════════════════

def test_create_application_as_candidat(c: TestClient):
    r = c.post(
        "/applications",
        json={"program_id": STATE["program_id"], "academic_year": YEAR, "notes": "Très motivé !"},
        headers=H(STATE["token_a"])
    )
    assert r.status_code == 201, r.json()
    data = r.json()
    assert data["status"] == "draft"
    assert data["program_id"] == STATE["program_id"]
    assert data["academic_year"] == YEAR
    STATE["app_id"] = data["id"]


def test_create_duplicate_application_returns_409(c: TestClient):
    """Même utilisateur + même formation + même année → 409."""
    r = c.post(
        "/applications",
        json={"program_id": STATE["program_id"], "academic_year": YEAR},
        headers=H(STATE["token_a"])
    )
    assert r.status_code == 409


def test_create_application_requires_auth(c: TestClient):
    r = c.post("/applications", json={"program_id": STATE["program_id"], "academic_year": YEAR})
    assert r.status_code == 401


def test_create_application_inactive_program_returns_404(c: TestClient):
    slug = "prog-inactive-sa13-v2"
    # Créer puis désactiver la formation
    r = c.post("/programs", json={**PROGRAM_PAYLOAD, "slug": slug}, headers=H(STATE["admin_token"]))
    assert r.status_code in (201, 409)
    prog_id = c.get(f"/programs/{slug}").json()["id"]
    c.delete(f"/programs/{slug}", headers=H(STATE["admin_token"]))  # désactivation logique

    r = c.post(
        "/applications",
        json={"program_id": prog_id, "academic_year": "2025-2026"},
        headers=H(STATE["token_a"])
    )
    assert r.status_code == 404


def test_invalid_academic_year_format_returns_422(c: TestClient):
    r = c.post(
        "/applications",
        json={"program_id": STATE["program_id"], "academic_year": "2026/2027"},
        headers=H(STATE["token_a"])
    )
    assert r.status_code == 422


def test_non_consecutive_academic_year_returns_422(c: TestClient):
    r = c.post(
        "/applications",
        json={"program_id": STATE["program_id"], "academic_year": "2026-2030"},
        headers=H(STATE["token_a"])
    )
    assert r.status_code == 422


# ═══════════════════════════ Consultation ═══════════════════════════

def test_list_my_applications(c: TestClient):
    r = c.get("/applications/me", headers=H(STATE["token_a"]))
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert STATE["app_id"] in ids


def test_list_my_applications_filter_by_status(c: TestClient):
    r = c.get("/applications/me?status=draft", headers=H(STATE["token_a"]))
    assert r.status_code == 200
    for a in r.json():
        assert a["status"] == "draft"


def test_get_own_application(c: TestClient):
    r = c.get(f"/applications/{STATE['app_id']}", headers=H(STATE["token_a"]))
    assert r.status_code == 200
    assert r.json()["id"] == STATE["app_id"]


def test_get_other_user_application_returns_403(c: TestClient):
    """Candidat B ne peut pas consulter la candidature de Candidat A."""
    r = c.get(f"/applications/{STATE['app_id']}", headers=H(STATE["token_b"]))
    assert r.status_code == 403


# ═════════════════════════ Retrait candidat ══════════════════════════

def test_withdraw_other_user_application_returns_403(c: TestClient):
    r = c.delete(f"/applications/{STATE['app_id']}", headers=H(STATE["token_b"]))
    assert r.status_code == 403


# ═════════════════════════ Routes admin ══════════════════════════════

def test_admin_list_applications(c: TestClient):
    r = c.get("/admin/applications", headers=H(STATE["admin_token"]))
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()]
    assert STATE["app_id"] in ids


def test_admin_list_applications_filter_by_status(c: TestClient):
    r = c.get("/admin/applications?status=draft", headers=H(STATE["admin_token"]))
    assert r.status_code == 200
    for a in r.json():
        assert a["status"] == "draft"


def test_admin_get_application_detail(c: TestClient):
    r = c.get(f"/admin/applications/{STATE['app_id']}", headers=H(STATE["admin_token"]))
    assert r.status_code == 200
    data = r.json()
    assert data["program_name"] == PROGRAM_PAYLOAD["name"]
    assert data["applicant_email"] == CANDIDAT_A["email"]


def test_admin_update_status_to_submitted(c: TestClient):
    r = c.patch(
        f"/admin/applications/{STATE['app_id']}/status",
        json={"status": "submitted", "notes": "Dossier complet"},
        headers=H(STATE["admin_token"])
    )
    assert r.status_code == 200, r.json()
    assert r.json()["status"] == "submitted"


def test_candidat_cannot_withdraw_non_draft(c: TestClient):
    """Candidat A ne peut plus retirer sa candidature (statut : submitted)."""
    r = c.delete(f"/applications/{STATE['app_id']}", headers=H(STATE["token_a"]))
    assert r.status_code == 409


def test_admin_update_status_to_accepted(c: TestClient):
    r = c.patch(
        f"/admin/applications/{STATE['app_id']}/status",
        json={"status": "accepted"},
        headers=H(STATE["admin_token"])
    )
    assert r.status_code == 200, r.json()
    assert r.json()["status"] == "accepted"


def test_admin_delete_application(c: TestClient):
    r = c.delete(f"/admin/applications/{STATE['app_id']}", headers=H(STATE["admin_token"]))
    assert r.status_code == 204


def test_deleted_application_returns_404(c: TestClient):
    r = c.get(f"/applications/{STATE['app_id']}", headers=H(STATE["admin_token"]))
    assert r.status_code == 404


# ══════════════════════ Retrait draft (happy path) ═══════════════════

def test_candidat_can_withdraw_draft_application(c: TestClient):
    """Candidat B crée puis retire une candidature en draft."""
    r = c.post(
        "/applications",
        json={"program_id": STATE["program_id"], "academic_year": "2027-2028"},
        headers=H(STATE["token_b"])
    )
    assert r.status_code == 201, r.json()
    new_id = r.json()["id"]

    r = c.delete(f"/applications/{new_id}", headers=H(STATE["token_b"]))
    assert r.status_code == 204


# ══════════════════════ Contrôle d'accès admin ═══════════════════════

def test_candidat_cannot_access_admin_list(c: TestClient):
    r = c.get("/admin/applications", headers=H(STATE["token_a"]))
    assert r.status_code == 403


def test_candidat_cannot_patch_status(c: TestClient):
    # Recréer une candidature pour tester le refus de PATCH status
    r = c.post(
        "/applications",
        json={"program_id": STATE["program_id"], "academic_year": YEAR},
        headers=H(STATE["token_a"])
    )
    assert r.status_code in (201, 409), r.json()
    if r.status_code == 201:
        app_id = r.json()["id"]
    else:
        apps = c.get("/applications/me", headers=H(STATE["token_a"])).json()
        app_id = apps[0]["id"]

    r = c.patch(
        f"/admin/applications/{app_id}/status",
        json={"status": "rejected"},
        headers=H(STATE["token_a"])
    )
    assert r.status_code == 403


def test_unauthenticated_cannot_list_my_applications(c: TestClient):
    r = c.get("/applications/me")
    assert r.status_code == 401
