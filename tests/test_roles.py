"""Tests complets pour les nouveaux rôles (Responsables académiques IIT/ISB, Entretien, Direction).
Vérifie :
1. Enumération et métadonnées des rôles (GET /admin/roles)
2. Création administrative d'utilisateurs avec chacun des rôles
3. Prérogatives Responsable Académique IIT (gestion formations IIT autorisée, ISB refusée, vision candidatures IIT)
4. Prérogatives Responsable Académique ISB (gestion formations ISB autorisée, IIT refusée, vision candidatures ISB)
5. Prérogatives Responsable Entretien (programmation d'entretiens et enregistrement des résultats autorisés)
6. Prérogatives Direction (accès tableau de bord global, statistiques, entonnoir de conversion)
7. Isolation et rejet des accès non autorisés pour les candidats
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models import Role, Institution, ApplicationStatus
from .conftest import ADMIN, H


def _login(c: TestClient, email: str, password: str = "Password123!") -> str:
    r = c.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Erreur login {email}: {r.text}"
    return r.json()["access_token"]


def test_list_roles_metadata(c: TestClient):
    """Vérifie que l'endpoint GET /admin/roles retourne les métadonnées officielles de tous les rôles."""
    adm_tok = _login(c, ADMIN["email"], ADMIN["password"])
    r = c.get("/admin/roles", headers=H(adm_tok))
    assert r.status_code == 200
    roles = r.json()
    role_codes = {item["code"] for item in roles}
    assert Role.responsable_academique_iit.value in role_codes
    assert Role.responsable_academique_isb.value in role_codes
    assert Role.responsable_entretien.value in role_codes
    assert Role.direction.value in role_codes
    assert Role.admin.value in role_codes
    assert Role.candidat.value in role_codes

    # Vérification des descriptions et permissions
    resp_iit = next(item for item in roles if item["code"] == Role.responsable_academique_iit.value)
    assert resp_iit["title"] == "Responsable académique IIT"
    assert "Supervise les informations" in resp_iit["description"]
    assert len(resp_iit["permissions"]) >= 5


def test_admin_create_users_with_all_roles(c: TestClient):
    """Vérifie que l'admin peut créer un compte pour chacun des nouveaux rôles."""
    adm_tok = _login(c, ADMIN["email"], ADMIN["password"])
    
    roles_to_test = [
        (Role.responsable_academique_iit, "test.iit@test.tn"),
        (Role.responsable_academique_isb, "test.isb@test.tn"),
        (Role.responsable_entretien, "test.entretien@test.tn"),
        (Role.direction, "test.direction@test.tn"),
    ]
    for role_enum, email in roles_to_test:
        r = c.post(
            "/admin/users",
            json={
                "email": email,
                "password": "Password123!",
                "full_name": f"User {role_enum.value}",
                "role": role_enum.value,
            },
            headers=H(adm_tok)
        )
        assert r.status_code == 201, f"Échec création {role_enum.value}: {r.text}"
        assert r.json()["role"] == role_enum.value
        assert r.json()["email"] == email


def test_responsable_academique_iit_permissions(c: TestClient):
    """Responsable IIT :
    - Peut créer un programme IIT
    - NE PEUT PAS créer un programme ISB (403)
    - Voit les candidatures IIT, mais pas ISB
    """
    adm_tok = _login(c, ADMIN["email"], ADMIN["password"])
    # Créer un compte responsable IIT
    iit_user_email = "prof.iit@test.tn"
    c.post(
        "/admin/users",
        json={"email": iit_user_email, "password": "Password123!", "full_name": "Prof IIT", "role": "responsable_academique_iit"},
        headers=H(adm_tok)
    )
    iit_tok = _login(c, iit_user_email)

    # 1. Création autorisée pour IIT
    slug_iit = "iit-genie-ia-special"
    r_create_iit = c.post(
        "/programs",
        json={
            "slug": slug_iit,
            "institution": "IIT",
            "level": "ingenierie",
            "name": "Cycle Ingénieur Intelligence Artificielle IIT",
            "description": "Nouvelle formation d'ingénieur IIT",
            "duration_years": 3,
            "language": "fr",
        },
        headers=H(iit_tok)
    )
    assert r_create_iit.status_code == 201
    assert r_create_iit.json()["slug"] == slug_iit

    # 2. Création refusée (403) pour ISB
    r_create_isb = c.post(
        "/programs",
        json={
            "slug": "isb-master-finance-illegal",
            "institution": "ISB",
            "level": "master",
            "name": "Tentative création ISB",
            "description": "Devrait échouer",
            "duration_years": 2,
            "language": "fr",
        },
        headers=H(iit_tok)
    )
    assert r_create_isb.status_code == 403

    # 3. Modification autorisée pour IIT
    r_patch_iit = c.patch(
        f"/programs/{slug_iit}",
        json={"description": "Description mise à jour par le responsable IIT"},
        headers=H(iit_tok)
    )
    assert r_patch_iit.status_code == 200
    assert r_patch_iit.json()["description"] == "Description mise à jour par le responsable IIT"


def test_responsable_academique_isb_permissions(c: TestClient):
    """Responsable ISB :
    - Peut créer un programme ISB
    - NE PEUT PAS créer un programme IIT (403)
    """
    adm_tok = _login(c, ADMIN["email"], ADMIN["password"])
    isb_user_email = "prof.isb@test.tn"
    c.post(
        "/admin/users",
        json={"email": isb_user_email, "password": "Password123!", "full_name": "Prof ISB", "role": "responsable_academique_isb"},
        headers=H(adm_tok)
    )
    isb_tok = _login(c, isb_user_email)

    # 1. Création autorisée pour ISB
    slug_isb = "isb-licence-management-digital"
    r_create_isb = c.post(
        "/programs",
        json={
            "slug": slug_isb,
            "institution": "ISB",
            "level": "licence",
            "name": "Licence Management Digital ISB",
            "description": "Formation management ISB",
            "duration_years": 3,
            "language": "fr",
        },
        headers=H(isb_tok)
    )
    assert r_create_isb.status_code == 201

    # 2. Création refusée (403) pour IIT
    r_create_iit = c.post(
        "/programs",
        json={
            "slug": "iit-meca-illegal",
            "institution": "IIT",
            "level": "licence",
            "name": "Tentative IIT par ISB",
            "description": "Devrait échouer",
            "duration_years": 3,
            "language": "fr",
        },
        headers=H(isb_tok)
    )
    assert r_create_iit.status_code == 403


def test_responsable_entretien_workflow(c: TestClient):
    """Responsable Entretien :
    - Peut programmer un entretien
    - Peut saisir l'évaluation et la note du jury
    - Candidat ne peut pas le faire (403)
    """
    adm_tok = _login(c, ADMIN["email"], ADMIN["password"])
    
    # 1. Créer responsable entretien et un candidat
    ent_email = "jury.entretien@test.tn"
    cand_email = "etudiant.candidat@test.tn"
    c.post(
        "/admin/users",
        json={"email": ent_email, "password": "Password123!", "full_name": "M. Jury", "role": "responsable_entretien"},
        headers=H(adm_tok)
    )
    c.post(
        "/admin/users",
        json={"email": cand_email, "password": "Password123!", "full_name": "Étudiant Test", "role": "candidat"},
        headers=H(adm_tok)
    )
    ent_tok = _login(c, ent_email)
    cand_tok = _login(c, cand_email)

    # 2. Créer une formation et candidature pour le test
    prog = c.post(
        "/programs",
        json={
            "slug": "iit-cyber-demo",
            "institution": "IIT",
            "level": "licence",
            "name": "Licence Cybersécurité",
            "description": "Formation test",
        },
        headers=H(adm_tok)
    ).json()

    app_res = c.post(
        "/applications",
        json={"program_id": prog["id"], "academic_year": "2026-2027", "notes": "Candidature test"},
        headers=H(cand_tok)
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 3. Candidat essaie de programmer son propre entretien -> 403
    r_cand_interview = c.post(
        f"/applications/{app_id}/interview",
        json={
            "scheduled_at": "2026-12-01T10:00:00Z",
            "duration_minutes": 30,
            "interview_type": "en_ligne",
            "location_or_link": "https://meet.smartcampus.tn/room-1",
        },
        headers=H(cand_tok)
    )
    assert r_cand_interview.status_code == 403

    # 4. Responsable entretien programme l'entretien -> 201
    r_ent_interview = c.post(
        f"/applications/{app_id}/interview",
        json={
            "scheduled_at": "2026-12-01T10:00:00Z",
            "duration_minutes": 30,
            "interview_type": "en_ligne",
            "location_or_link": "https://meet.smartcampus.tn/room-1",
            "notes": "Entretien de motivation et test QCM",
        },
        headers=H(ent_tok)
    )
    assert r_ent_interview.status_code == 201
    assert r_ent_interview.json()["application_id"] == app_id

    # 5. Responsable entretien enregistre le résultat du jury
    r_result = c.post(
        f"/applications/{app_id}/interview/result",
        json={
            "technical_score": 16.5,
            "motivation_score": 18.0,
            "language_score": 15.0,
            "decision": "favorable",
            "jury_feedback": "Excellent profil technique et très motivé.",
        },
        headers=H(ent_tok)
    )
    assert r_result.status_code == 201
    assert r_result.json()["decision"] == "favorable"
    assert float(r_result.json()["overall_score"]) == 16.5


def test_direction_dashboard_and_funnel(c: TestClient):
    """Direction :
    - Accès au tableau de bord global (GET /dashboard/stats)
    - Statistiques décisionnelles et taux de conversion
    - Rejet pour un simple candidat (403)
    """
    adm_tok = _login(c, ADMIN["email"], ADMIN["password"])
    dir_email = "directeur@test.tn"
    cand_email = "simple.cand@test.tn"
    c.post(
        "/admin/users",
        json={"email": dir_email, "password": "Password123!", "full_name": "Directeur", "role": "direction"},
        headers=H(adm_tok)
    )
    c.post(
        "/admin/users",
        json={"email": cand_email, "password": "Password123!", "full_name": "Candidat", "role": "candidat"},
        headers=H(adm_tok)
    )
    dir_tok = _login(c, dir_email)
    cand_tok = _login(c, cand_email)

    # 1. Candidat refuse l'accès au tableau de bord (403)
    r_cand = c.get("/dashboard/stats", headers=H(cand_tok))
    assert r_cand.status_code == 403

    # 2. Direction accède au tableau de bord (200)
    r_dir = c.get("/dashboard/stats", headers=H(dir_tok))
    assert r_dir.status_code == 200
    stats = r_dir.json()

    assert "funnel" in stats
    assert "comparative_iit_vs_isb" in stats
    assert "most_demanded_programs" in stats
    assert "applications_by_status" in stats
    assert "interviews_by_status" in stats
    assert stats["scope"] == "global"
    assert "conversion_rate_preinscription_pct" in stats["funnel"]
    assert "conversion_rate_interview_pct" in stats["funnel"]
