"""Tests pour les candidatures, la gestion des documents et la synchronisation (SA-13, SA-14, SA-18)."""
import pytest
from fastapi.testclient import TestClient

from .conftest import ADMIN, H


def _admin(c):
    return c.post("/auth/login", json=ADMIN).json()["access_token"]


def _candidate(c, email: str, session: str | None = None) -> dict:
    r = c.post("/auth/register", json={"email": email, "password": "Password123!"}, headers=H(session=session))
    assert r.status_code == 201, r.text
    return r.json()


def test_applications_flow_and_rbac(c):
    """Test du cycle complet d'une candidature : création, contrôle des droits, changement de statut."""
    adm = _admin(c)

    # 1. Créer une formation
    p_data = {
        "slug": "cycle-genie-logiciel-iit",
        "institution": "IIT",
        "level": "ingenierie",
        "name": "Génie Logiciel",
        "duration_years": 3
    }
    r_prog = c.post("/programs", json=p_data, headers=H(adm))
    assert r_prog.status_code == 201
    prog_id = r_prog.json()["id"]

    # 2. Créer un candidat
    cand1 = _candidate(c, "candidat_app1@test.tn")
    cand1_tok = cand1["access_token"]

    # 3. Un utilisateur non candidat (visiteur anonyme) ne peut pas candidater
    assert c.post("/applications", json={"program_id": prog_id, "academic_year": "2026-2027"}).status_code == 401

    # 4. Le candidat soumet une candidature
    r_app = c.post(
        "/applications",
        json={"program_id": prog_id, "academic_year": "2026-2027", "notes": "Candidat admis avec mention bien"},
        headers=H(cand1_tok)
    )
    assert r_app.status_code == 201
    app_data = r_app.json()
    app_id = app_data["id"]
    assert app_data["status"] == "draft"
    assert app_data["academic_year"] == "2026-2027"

    # 5. Tentative de doubler la candidature pour la même année académique -> 409 Conflit
    r_dup = c.post(
        "/applications",
        json={"program_id": prog_id, "academic_year": "2026-2027"},
        headers=H(cand1_tok)
    )
    assert r_dup.status_code == 409

    # 6. Consultation : le candidat voit sa candidature
    r_list = c.get("/applications", headers=H(cand1_tok))
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1

    # 7. Un autre candidat ne voit pas cette candidature
    cand2 = _candidate(c, "candidat_app2@test.tn")
    r_list2 = c.get("/applications", headers=H(cand2["access_token"]))
    assert len(r_list2.json()) == 0
    assert c.get(f"/applications/{app_id}", headers=H(cand2["access_token"])).status_code == 404

    # 8. L'administrateur peut voir toutes les candidatures et modifier le statut
    r_admin_list = c.get("/applications", headers=H(adm))
    assert len(r_admin_list.json()) >= 1

    r_status = c.patch(
        f"/applications/{app_id}/status",
        json={"status": "under_review"},
        headers=H(adm)
    )
    assert r_status.status_code == 200
    assert r_status.json()["status"] == "under_review"

    # Un candidat ne peut pas modifier son propre statut
    r_cand_patch = c.patch(
        f"/applications/{app_id}/status",
        json={"status": "accepted"},
        headers=H(cand1_tok)
    )
    assert r_cand_patch.status_code == 403


def test_documents_attachment_and_verification(c):
    """Test du dépôt de pièces jointes et validation administrative (SA-14)."""
    adm = _admin(c)
    cand = _candidate(c, "candidat_docs@test.tn")
    cand_tok = cand["access_token"]

    # Créer programme et candidature
    p = c.post("/programs", json={"slug": "prepa-iit", "institution": "IIT", "level": "prepa", "name": "Prépa"}, headers=H(adm)).json()
    app_obj = c.post("/applications", json={"program_id": p["id"], "academic_year": "2026-2027"}, headers=H(cand_tok)).json()
    app_id = app_obj["id"]

    # Candidat dépose son diplôme de baccalauréat
    doc_in = {
        "document_type": "diplome",
        "filename": "bac_scientifique.pdf",
        "file_path": "/uploads/bac_123.pdf",
        "mime_type": "application/pdf",
        "file_size": 1048576
    }
    r_doc = c.post(f"/applications/{app_id}/documents", json=doc_in, headers=H(cand_tok))
    assert r_doc.status_code == 201
    doc_data = r_doc.json()
    doc_id = doc_data["id"]
    assert doc_data["is_verified"] is False
    assert doc_data["document_type"] == "diplome"

    # Lister les documents
    r_docs = c.get(f"/applications/{app_id}/documents", headers=H(cand_tok))
    assert len(r_docs.json()) == 1

    # Validation du document par l'admin
    r_verify = c.patch(f"/documents/{doc_id}/verify", headers=H(adm))
    assert r_verify.status_code == 200
    assert r_verify.json()["is_verified"] is True


def test_sync_catalog_and_logs(c):
    """Test du déclenchement de la synchronisation et de la traçabilité dans sync_logs (SA-14, SA-18)."""
    adm = _admin(c)
    cand = _candidate(c, "user_sync@test.tn")

    # Non-admin ne peut pas déclencher de synchronisation
    assert c.post("/admin/sync-catalog", headers=H(cand["access_token"])).status_code == 403
    assert c.get("/admin/sync-logs", headers=H(cand["access_token"])).status_code == 403

    # Admin déclenche la synchronisation
    r_sync = c.post("/admin/sync-catalog", headers=H(adm))
    assert r_sync.status_code == 200
    assert "Synchronisation du catalogue terminée" in r_sync.json()["message"]

    # Vérification des journaux de synchronisation
    r_logs = c.get("/admin/sync-logs", headers=H(adm))
    assert r_logs.status_code == 200
    logs = r_logs.json()
    assert len(logs) >= 1
    assert logs[0]["entity_type"] == "catalog_demo_seed"
    assert logs[0]["status"] == "success"
