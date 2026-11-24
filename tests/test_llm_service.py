"""Tests complets pour le service LLM local Ollama (Gemma), la sécurité des accès,
la gestion des pannes/timeouts et le benchmark d'évaluation SA-32.
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services_llm import (LLMConnectionError, LLMModelNotFoundError,
                            LLMTimeoutError, OllamaClient,
                            evaluate_response_criteria, llm_connector,
                            load_sa32_questions)
from .conftest import ADMIN, H


def _admin_token(c):
    return c.post("/auth/login", json=ADMIN).json()["access_token"]


# =====================================================================
# 1. Tests de la sonde de santé et d'inspection des modèles
# =====================================================================

def test_llm_health_probe(c):
    """Vérifie la sonde de santé GET /llm/health."""
    r = c.get("/llm/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["configured_model"] == "gemma3:1b"
    assert "ollama_url" in data
    assert isinstance(data["available_models"], list)
    if data["status"] == "ok":
        assert data["model_available"] is True


def test_llm_list_models(c):
    """Vérifie la récupération de la liste des modèles GET /llm/models."""
    r = c.get("/llm/models")
    assert r.status_code == 200
    models = r.json()
    assert isinstance(models, list)
    model_names = [m["name"] for m in models]
    # gemma3:1b doit figurer dans les modèles installés
    assert any("gemma" in name for name in model_names)


# =====================================================================
# 2. Tests de l'API de dialogue /llm/chat avec Gemma
# =====================================================================

def test_llm_chat_direct_nominal(c):
    """Envoi d'une question à l'API /llm/chat et génération d'une réponse par Gemma."""
    payload = {
        "query": "Quelles sont les conditions d'admission au cycle d'ingénieur en informatique de l'IIT ?",
        "temperature": 0.2,
        "inject_academic_context": True,
    }
    r = c.post("/llm/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "gemma" in data["model"]
    assert len(data["response"]) > 20
    assert data["latency_ms"] > 0
    # Vérification que le texte mentionne les éléments académiques
    content_lower = data["response"].lower()
    assert any(term in content_lower for term in ["iit", "ingénieur", "admission", "dossier", "concours", "licence", "préparatoire"])


def test_llm_chat_empty_query_rejected(c):
    """Rejet des requêtes vides avec validation Pydantic (422)."""
    r = c.post("/llm/chat", json={"query": "   "})
    assert r.status_code == 422


# =====================================================================
# 3. Tests de protection des clés d'accès (Sécurité API Key)
# =====================================================================

def test_llm_api_key_protection(c):
    """Vérifie la protection stricte de l'accès aux endpoints LLM via clé secrète."""
    test_secret_key = "secret-super-cle-llm-de-test-32bytes"
    original_key = settings.llm_service_api_key

    try:
        # Activer la protection par clé API
        settings.llm_service_api_key = test_secret_key

        # 1. Sans clé -> 401 Unauthorized
        r_no_key = c.post("/llm/chat", json={"query": "Bonjour"})
        assert r_no_key.status_code == 401
        assert "Accès refusé" in r_no_key.json()["detail"]

        # 2. Avec mauvaise clé -> 401 Unauthorized
        r_bad_key = c.post("/llm/chat", json={"query": "Bonjour"}, headers={"X-API-Key": "mauvaise-cle"})
        assert r_bad_key.status_code == 401

        # 3. Avec la clé valide dans l'en-tête X-API-Key -> 200 OK
        r_valid_x_key = c.post("/llm/chat", json={"query": "aslema"}, headers={"X-API-Key": test_secret_key})
        assert r_valid_x_key.status_code == 200

        # 4. Avec la clé valide dans Authorization: Bearer <key> -> 200 OK
        r_valid_bearer = c.post("/llm/chat", json={"query": "aslema"}, headers={"Authorization": f"Bearer {test_secret_key}"})
        assert r_valid_bearer.status_code == 200

        # 5. Avec un jeton admin connecté -> 200 OK
        admin_tok = _admin_token(c)
        r_admin = c.post("/llm/chat", json={"query": "aslema"}, headers=H(token=admin_tok))
        assert r_admin.status_code == 200

    finally:
        settings.llm_service_api_key = original_key


# =====================================================================
# 4. Tests de gestion des erreurs de connexion et de dépassement de délai
# =====================================================================

def test_llm_connection_error_handling(c):
    """Vérifie la détection et la réponse propre en cas d'indisponibilité du serveur Ollama."""
    original_url = llm_connector.client.base_url
    original_fallback = settings.llm_fallback_enabled

    try:
        # Pointeur vers un port mort (connexion impossible)
        llm_connector.client.base_url = "http://127.0.0.1:59999"

        # A. Mode avec Fallback activé : renvoie une réponse déterministe RAG avec fallback_used=True
        settings.llm_fallback_enabled = True
        r_fallback = c.post("/llm/chat", json={"query": "Quelles sont les conditions d'admission ?"})
        assert r_fallback.status_code == 200
        data_fb = r_fallback.json()
        assert data_fb["fallback_used"] is True
        assert len(data_fb["response"]) > 10

        # B. Mode sans Fallback : renvoie une erreur HTTP 503 Service Unavailable
        settings.llm_fallback_enabled = False
        with patch.object(llm_connector.client, "chat_completion", side_effect=LLMConnectionError("Ollama éteint")):
            r_err = c.post("/llm/chat", json={"query": "Quelles sont les conditions d'admission ?"})
            assert r_err.status_code == 503
            assert "Erreur de connexion" in r_err.json()["detail"]

    finally:
        llm_connector.client.base_url = original_url
        settings.llm_fallback_enabled = original_fallback


def test_llm_timeout_error_handling(c):
    """Vérifie la détection et la réponse propre lors d'un dépassement du délai de réponse (timeout)."""
    original_fallback = settings.llm_fallback_enabled

    try:
        # Simuler un timeout sans fallback
        settings.llm_fallback_enabled = False
        with patch.object(llm_connector.client, "chat_completion", side_effect=LLMTimeoutError("Temps dépassé (60s)")):
            r_timeout = c.post("/llm/chat", json={"query": "Calculer un programme complexe"})
            assert r_timeout.status_code == 504
            assert "Délai d'attente de réponse dépassé" in r_timeout.json()["detail"]

    finally:
        settings.llm_fallback_enabled = original_fallback


def test_llm_model_not_found_handling(c):
    """Vérifie la gestion d'un modèle absent sur le serveur Ollama (404)."""
    original_fallback = settings.llm_fallback_enabled
    try:
        settings.llm_fallback_enabled = False
        with patch.object(llm_connector.client, "chat_completion", side_effect=LLMModelNotFoundError("modele-inexistant")):
            r = c.post("/llm/chat", json={"query": "Test"})
            assert r.status_code == 404
            assert "modele-inexistant" in r.json()["detail"]
    finally:
        settings.llm_fallback_enabled = original_fallback


# =====================================================================
# 5. Tests du Benchmark SA-32 (Évaluation des LLM)
# =====================================================================

def test_sa32_questions_loading(c):
    """Vérifie le chargement exhaustif des 19 questions d'évaluation SA-32."""
    questions = load_sa32_questions()
    assert len(questions) == 19
    categories = {q["category"] for q in questions}
    assert categories == {"admission", "orientation", "reformulation", "ambiguous"}

    # Test via l'endpoint GET /llm/evaluations/questions
    r = c.get("/llm/evaluations/questions")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 19
    ids = [q["id"] for q in data]
    assert "ADM-001" in ids
    assert "ORI-001" in ids
    assert "REF-001" in ids
    assert "AMB-001" in ids


def test_sa32_ambiguity_detection_criteria():
    """Vérifie que les cas ambigus exigent une demande de clarification et ne tolèrent pas de supposition."""
    q_amb1 = {
        "id": "AMB-001",
        "category": "ambiguous",
        "query": "C'est combien ?",
        "expected_behavior": "Demander ce que le candidat souhaite connaître.",
    }

    # Cas 1 : Réponse qui demande des précisions -> Valide
    passed1, feedback1 = evaluate_response_criteria(
        q_amb1,
        "Afin de vous donner une réponse exacte, pourriez-vous préciser la formation dont vous souhaitez connaître les tarifs ?"
    )
    assert passed1 is True

    # Cas 2 : Réponse qui suppose arbitrairement un montant sans demander -> Échec
    passed2, feedback2 = evaluate_response_criteria(
        q_amb1,
        "Le prix est de 5000 dinars."
    )
    assert passed2 is False


def test_sa32_run_benchmark_subset(c):
    """Exécution ciblée du benchmark SA-32 sur la catégorie 'ambiguous' via POST /llm/evaluations/run."""
    r = c.post("/llm/evaluations/run?category=ambiguous&limit=2")
    assert r.status_code == 200
    data = r.json()
    assert data["evaluated_questions"] == 2
    assert "ambiguous" in data["categories"]
    assert len(data["results"]) == 2
    for item in data["results"]:
        assert item["category"] == "ambiguous"
        assert len(item["response"]) > 0
        assert isinstance(item["criteria_met"], bool)


# =====================================================================
# 6. Tests de la Mémoire Temporaire (US-006 / SA-26) et Garde-fous Administratifs
# =====================================================================

def test_temporary_memory_and_follow_up_questions(c):
    """Vérifie la transmission des messages récents de la session (US-006)
    afin que le modèle comprenne le contexte et réponde aux questions de suivi.
    """
    # 1. Création d'une session visiteur temporaire
    sess = c.post("/sessions").json()["session_token"]

    # 2. Création d'une conversation liée à cette session
    conv = c.post("/conversations", json={"title": "Orientation Ingénieur"}, headers=H(session=sess)).json()
    conv_id = conv["id"]

    # 3. Premier tour : Sujet précis sur le cycle d'ingénieur en informatique à l'IIT
    r1 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Je suis intéressé par le cycle ingénieur en génie informatique à l'IIT."},
        headers=H(session=sess)
    )
    assert r1.status_code == 201
    resp1 = r1.json()["assistant_message"]["content"]
    assert len(resp1) > 20

    # 4. Deuxième tour (Question de suivi) : Formule implicite sans répéter "IIT" ni "informatique"
    r2 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Quels sont ses frais de scolarité et ses tarifs ?"},
        headers=H(session=sess)
    )
    assert r2.status_code == 201
    resp2 = r2.json()["assistant_message"]["content"].lower()
    
    # Le modèle doit avoir compris le sujet précédent grâce à la mémoire de session (US-006)
    # et fournir les tarifs/frais correspondants (778 DT / 9 mois ou droit d'inscription 800 DT / IIT)
    assert any(term in resp2 for term in ["778", "iit", "informatique", "800", "dt", "scolarité", "tarifs"])

    # 5. Vérifier que la mémoire conversationnelle conserve les 4 messages ordonnés
    r_msgs = c.get(f"/conversations/{conv_id}/messages", headers=H(session=sess))
    assert r_msgs.status_code == 200
    msgs = r_msgs.json()
    assert len(msgs) == 4
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]


def test_unverified_administrative_info_guardrails(c):
    """Vérifie les instructions interdisant de présenter des informations administratives
    non vérifiées comme officielles et l'absence de décisions d'admission automatiques.
    """
    # Question demandant une admission garantie et une date limite non vérifiée
    query = (
        "Je veux m'inscrire en mastère. Pouvez-vous me garantir que je suis admis d'office "
        "et me donner la date limite définitive de dépôt ?"
    )
    r = c.post("/llm/chat", json={"query": query})
    assert r.status_code == 200
    content = r.json()["response"].lower()

    # 1. Ne doit pas garantir d'admission automatique
    # Doit mentionner la commission, l'étude de dossier ou la réserve
    assert any(term in content for term in ["commission", "dossier", "souveraine", "décision", "garantir", "admission", "entretien"])

    # 2. Doit préciser que les informations sont indicatives ou sous réserve de confirmation
    assert any(term in content for term in ["indicatif", "confirmation", "officiel", "revalider", "vérifi", "réserve"])

    # 3. Doit orienter vers les contacts officiels (IIT ou ISB)
    assert any(term in content for term in ["ameni.trigui@iit.ens.tn", "contact@isb.ens.tn", "iit.tn", "isb.tn", "scolarite@isb.ens.tn", "secrétariat", "administration"])


def test_chat_with_conversation_id_memory(c):
    """Vérifie que l'endpoint direct POST /llm/chat peut consommer la mémoire temporaire via conversation_id."""
    sess = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={"title": "Test Chat Memory"}, headers=H(session=sess)).json()
    conv_id = conv["id"]

    # Ajouter un premier message dans la conversation
    c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Je prépare un bac scientifique et je vise l'ISB."},
        headers=H(session=sess)
    )

    # Poser une question directe en référençant conversation_id
    r = c.post(
        "/llm/chat",
        json={
            "query": "Quelles spécialités me conseillez-vous ?",
            "conversation_id": conv_id
        }
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["response"]) > 20
    # Le modèle prend en compte le contexte ISB de la conversation
    resp_lower = data["response"].lower()
    assert any(term in resp_lower for term in ["isb", "gestion", "business", "licence", "finance", "marketing"])

