"""Tests complets pour les extensions du socle technique Membre 2 (SA-12, SA-13, SA-14, SA-22).
Vérifie la robustesse, les contraintes, les autorisations d'accès (RBAC) et la gestion des erreurs.
"""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from .conftest import ADMIN, H


def _admin(c):
    return c.post("/auth/login", json=ADMIN).json()["access_token"]


def _candidate(c, email: str, session: str | None = None) -> dict:
    r = c.post("/auth/register", json={"email": email, "password": "Password123!"}, headers=H(session=session))
    assert r.status_code == 201, r.text
    return r.json()


def test_specialties_and_courses_flow(c):
    """SA-12 & SA-22 : Spécialités et matières enseignées (création admin, consultation, filtres)."""
    adm = _admin(c)

    # 1. Créer une formation
    p_data = {
        "slug": "cycle-informatique-test",
        "institution": "IIT",
        "level": "ingenierie",
        "name": "Cycle Informatique Test",
        "duration_years": 3
    }
    r_prog = c.post("/programs", json=p_data, headers=H(adm))
    assert r_prog.status_code == 201
    prog_slug = r_prog.json()["slug"]

    # 2. Ajout d'une spécialité par admin
    spec_data = {
        "name": "Intelligence Artificielle & Big Data",
        "code": "IA-BD",
        "description": "Filière spécialisée en apprentissage profond."
    }
    r_spec = c.post(f"/programs/{prog_slug}/specialties", json=spec_data, headers=H(adm))
    assert r_spec.status_code == 201
    spec_id = r_spec.json()["id"]
    assert r_spec.json()["code"] == "IA-BD"

    # Un non-admin ne peut pas ajouter de spécialité
    cand = _candidate(c, "cand_spec@test.tn")
    r_spec_cand = c.post(f"/programs/{prog_slug}/specialties", json=spec_data, headers=H(cand["access_token"]))
    assert r_spec_cand.status_code == 403

    # 3. Ajout de matières (courses)
    course1 = {
        "code": "IA-401",
        "name": "Deep Learning & NLP",
        "semester": "S1",
        "credits_ects": 5.0,
        "coefficient": 2.0,
        "hours_lectures": 28,
        "hours_tutorials": 28,
        "description": "Réseaux récurrents, Transformers et LLMs.",
        "specialty_id": spec_id
    }
    r_c1 = c.post(f"/programs/{prog_slug}/courses", json=course1, headers=H(adm))
    assert r_c1.status_code == 201
    assert r_c1.json()["code"] == "IA-401"

    course2 = {
        "code": "MATH-402",
        "name": "Optimisation Convexe",
        "semester": "S2",
        "credits_ects": 3.0,
        "coefficient": 1.5,
        "hours_lectures": 21,
        "hours_tutorials": 21
    }
    r_c2 = c.post(f"/programs/{prog_slug}/courses", json=course2, headers=H(adm))
    assert r_c2.status_code == 201

    # 4. Consultation publique avec filtres
    r_all_courses = c.get(f"/programs/{prog_slug}/courses")
    assert r_all_courses.status_code == 200
    assert len(r_all_courses.json()) == 2

    # Filtrer par semestre
    r_s1 = c.get(f"/programs/{prog_slug}/courses?semester=S1")
    assert len(r_s1.json()) == 1
    assert r_s1.json()[0]["code"] == "IA-401"

    # Consultation du détail du programme incluant spécialités et cours
    r_detail = c.get(f"/programs/{prog_slug}")
    assert r_detail.status_code == 200
    detail_data = r_detail.json()
    assert len(detail_data.get("specialties", [])) >= 1
    assert len(detail_data.get("courses", [])) >= 2


def test_academic_profile_and_equivalences(c):
    """SA-13 & SA-22 : Profil académique et gestion des équivalences."""
    adm = _admin(c)
    cand = _candidate(c, "cand_academic@test.tn")
    cand_tok = cand["access_token"]

    # 1. Profil non existant au départ -> 404
    assert c.get("/users/me/academic-profile", headers=H(cand_tok)).status_code == 404

    # 2. Création du profil académique
    prof_data = {
        "bac_section": "Mathématiques",
        "bac_year": 2022,
        "bac_average": 14.75,
        "highest_diploma": "Licence en Informatique",
        "graduation_institution": "FSS Sfax",
        "graduation_year": 2025,
        "notes": "Mention Assez Bien"
    }
    r_prof = c.post("/users/me/academic-profile", json=prof_data, headers=H(cand_tok))
    assert r_prof.status_code == 200
    assert float(r_prof.json()["bac_average"]) == 14.75

    # 3. Consultation du profil créé
    r_get_prof = c.get("/users/me/academic-profile", headers=H(cand_tok))
    assert r_get_prof.status_code == 200
    assert r_get_prof.json()["highest_diploma"] == "Licence en Informatique"

    # 4. Création d'une formation cible pour l'équivalence
    prog = c.post(
        "/programs",
        json={"slug": "iit-genie-civil-eq", "institution": "IIT", "level": "ingenierie", "name": "Génie Civil"},
        headers=H(adm)
    ).json()

    # 5. Dépôt d'une demande d'équivalence
    eq_data = {
        "target_program_id": prog["id"],
        "source_diploma": "Licence Génie Mécanique",
        "source_institution": "Institut Supérieur des Études Technologiques",
        "source_country": "Tunisie",
        "requested_level": "1ère année Ingénieur"
    }
    r_eq = c.post("/equivalences", json=eq_data, headers=H(cand_tok))
    assert r_eq.status_code == 201
    eq_id = r_eq.json()["id"]
    assert r_eq.json()["status"] == "pending"

    # 6. Examen et décision par l'admin
    r_review = c.patch(
        f"/equivalences/{eq_id}/review",
        json={"status": "approved", "decision_notes": "Admis après étude du dossier"},
        headers=H(adm)
    )
    assert r_review.status_code == 200
    assert r_review.json()["status"] == "approved"

    # Un candidat ne peut pas examiner sa propre équivalence -> 403
    r_hack = c.patch(
        f"/equivalences/{eq_id}/review",
        json={"status": "approved"},
        headers=H(cand_tok)
    )
    assert r_hack.status_code == 403


def test_interview_scheduling_and_evaluation_results(c):
    """SA-13 & SA-22 : Prise de rendez-vous d'entretien et grille de résultats."""
    adm = _admin(c)
    cand = _candidate(c, "cand_interview@test.tn")
    cand_tok = cand["access_token"]

    prog = c.post(
        "/programs",
        json={"slug": "iit-informatique-interview", "institution": "IIT", "level": "ingenierie", "name": "Informatique"},
        headers=H(adm)
    ).json()

    app_obj = c.post(
        "/applications",
        json={"program_id": prog["id"], "academic_year": "2026-2027"},
        headers=H(cand_tok)
    ).json()
    app_id = app_obj["id"]

    # 1. Admin programme l'entretien
    interview_data = {
        "scheduled_at": "2026-12-01T10:00:00Z",
        "duration_minutes": 30,
        "interview_type": "en_ligne",
        "location_or_link": "https://meet.google.com/test-room",
        "notes": "Entretien de motivation et d'admissibilité"
    }
    r_int = c.post(f"/applications/{app_id}/interview", json=interview_data, headers=H(adm))
    assert r_int.status_code == 201
    assert r_int.json()["status"] == "programme"

    # Tentative de doubler l'entretien -> 409 Conflit
    assert c.post(f"/applications/{app_id}/interview", json=interview_data, headers=H(adm)).status_code == 409

    # 2. Le candidat consulte son entretien
    r_cand_view = c.get(f"/applications/{app_id}/interview", headers=H(cand_tok))
    assert r_cand_view.status_code == 200
    assert "meet.google.com" in r_cand_view.json()["location_or_link"]

    # 3. Admin saisit les résultats de l'entretien
    result_data = {
        "technical_score": 16.0,
        "motivation_score": 18.0,
        "language_score": 14.0,
        "decision": "favorable",
        "jury_feedback": "Excellente prestation orale et motivation confirmée."
    }
    r_res = c.post(f"/applications/{app_id}/interview/result", json=result_data, headers=H(adm))
    assert r_res.status_code == 201
    res_json = r_res.json()
    assert float(res_json["overall_score"]) == 16.0
    assert res_json["decision"] == "favorable"

    # Vérification que le statut de l'entretien est passé à 'effectue'
    r_updated_int = c.get(f"/applications/{app_id}/interview", headers=H(cand_tok))
    assert r_updated_int.json()["status"] == "effectue"


def test_document_versioning_and_vector_sync(c):
    """SA-14 & SA-22 : Historique des versions de documents et synchronisation vectorielle."""
    adm = _admin(c)
    cand = _candidate(c, "cand_docver@test.tn")
    cand_tok = cand["access_token"]

    prog = c.post(
        "/programs",
        json={"slug": "iit-docver-prog", "institution": "IIT", "level": "licence", "name": "Licence"},
        headers=H(adm)
    ).json()

    app_obj = c.post(
        "/applications",
        json={"program_id": prog["id"], "academic_year": "2026-2027"},
        headers=H(cand_tok)
    ).json()

    # 1. Dépôt d'un document
    doc_data = {
        "filename": "releve_notes_s1.pdf",
        "file_path": "/uploads/releve_s1_v1.pdf",
        "document_type": "releve_notes",
        "mime_type": "application/pdf",
        "file_size": 150000
    }
    r_doc = c.post(f"/applications/{app_obj['id']}/documents", json=doc_data, headers=H(cand_tok))
    assert r_doc.status_code == 201
    doc_id = r_doc.json()["id"]
    assert r_doc.json()["current_version"] == 1

    # 2. Ajout d'une nouvelle version révisée
    ver_data = {
        "file_path": "/uploads/releve_s1_v2_signe.pdf",
        "file_size": 165000,
        "change_summary": "Relevé signé avec mention officielle"
    }
    r_ver = c.post(f"/documents/{doc_id}/versions", json=ver_data, headers=H(cand_tok))
    assert r_ver.status_code == 201
    assert r_ver.json()["version_number"] == 2

    # 3. Consultation de l'historique des versions
    r_vers = c.get(f"/documents/{doc_id}/versions", headers=H(cand_tok))
    assert r_vers.status_code == 200
    assert len(r_vers.json()) >= 1

    # 4. Déclenchement de la synchronisation vectorielle (SA-14)
    sync_body = {
        "action": "upsert",
        "embedding_model": "text-embedding-3-small",
        "collection_name": "smartcampus_documents"
    }
    r_sync = c.post(f"/documents/{doc_id}/vector-sync", json=sync_body, headers=H(adm))
    assert r_sync.status_code == 202
    assert r_sync.json()["status"] == "completed"
    assert r_sync.json()["chunk_count"] >= 1

    # Liste des tâches vectorielles
    r_tasks = c.get("/admin/vector-sync-tasks", headers=H(adm))
    assert r_tasks.status_code == 200
    assert len(r_tasks.json()) >= 1
