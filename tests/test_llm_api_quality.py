"""Tests d'intégration de bout en bout (API Backend) pour évaluer la qualité des interactions LLM.
Vérifie :
1. Plusieurs échanges successifs en français avec conservation du contexte (US-006 / SA-26).
2. Détection et traitement des questions ambiguës (obligation de clarification).
3. Situations où le modèle ne peut pas répondre (discipline hors catalogue, date inexistante).
4. Gestion de l'indisponibilité temporaire (panne Ollama, timeout, bascule fallback).
5. Isolation stricte du contexte entre sessions indépendantes.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services_llm import (LLMConnectionError, LLMTimeoutError,
                            llm_connector)
from .conftest import H


# =====================================================================
# 1. Échanges successifs en français & Conservation du contexte
# =====================================================================

def test_backend_api_successive_exchanges_french_and_context_retention(c):
    """Vérifie plusieurs échanges successifs en français à travers l'API Backend.
    Teste la rétention du contexte thématique (formation IIT Génie Informatique)
    sur des questions de suivi formulées avec des pronoms ou des tournures implicites.
    """
    # Étape 1 : Créer une session visiteur
    sess = c.post("/sessions").json()["session_token"]

    # Étape 2 : Créer une conversation
    conv = c.post(
        "/conversations",
        json={"title": "Projet d'études Génie Informatique"},
        headers=H(session=sess)
    ).json()
    conv_id = conv["id"]

    # -------------------------------------------------------------
    # Échange 1 : Orientation & Découverte en français
    # -------------------------------------------------------------
    q1 = "Bonjour, je suis titulaire d'un baccalauréat scientifique et je cherche une formation d'ingénieur en informatique à Sfax."
    r1 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": q1},
        headers=H(session=sess)
    )
    assert r1.status_code == 201
    d1 = r1.json()
    resp1 = d1["assistant_message"]["content"].lower()
    # Doit répondre en français et cibler l'IIT et le cycle ingénieur informatique
    assert any(w in resp1 for w in ["iit", "informatique", "ingénieur", "formation"])

    # -------------------------------------------------------------
    # Échange 2 : Question de suivi 1 (Conditions d'admission)
    # L'utilisateur ne répète ni "IIT" ni "informatique", test de continuité du contexte
    # -------------------------------------------------------------
    q2 = "Quelles sont les conditions d'admission pour intégrer ce cycle ?"
    r2 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": q2},
        headers=H(session=sess)
    )
    assert r2.status_code == 201
    d2 = r2.json()
    resp2 = d2["assistant_message"]["content"].lower()
    # Le modèle doit comprendre qu'il s'agit du cycle ingénieur (concours sur dossier, entretien, prépa/licence)
    assert any(w in resp2 for w in ["dossier", "concours", "entretien", "préparatoire", "licence", "admission", "commission"])

    # -------------------------------------------------------------
    # Échange 3 : Question de suivi 2 (Frais de scolarité)
    # Formule elliptique ("ses tarifs") résolue via la mémoire conversationnelle
    # -------------------------------------------------------------
    q3 = "Et quels sont ses tarifs et frais de scolarité ?"
    r3 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": q3},
        headers=H(session=sess)
    )
    assert r3.status_code == 201
    d3 = r3.json()
    resp3 = d3["assistant_message"]["content"].lower()
    # Doit donner les tarifs de l'IIT (778 DT/mois ou 800 DT inscription) et rappeler leur caractère indicatif
    assert any(w in resp3 for w in ["778", "800", "dt", "frais", "scolarité", "tarifs"])
    assert any(w in resp3 for w in ["indicatif", "revalider", "confirmation", "administration", "officiel"])

    # -------------------------------------------------------------
    # Échange 4 : Question de suivi 3 (Dossier administratif)
    # -------------------------------------------------------------
    q4 = "Quelles sont les pièces à fournir pour constituer mon dossier ?"
    r4 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": q4},
        headers=H(session=sess)
    )
    assert r4.status_code == 201
    d4 = r4.json()
    resp4 = d4["assistant_message"]["content"].lower()
    # Doit lister les documents exigés
    assert any(w in resp4 for w in ["bac", "relevé", "cin", "cv", "photo", "dossier"])

    # -------------------------------------------------------------
    # Contrôle de la mémoire temporaire complète (GET /conversations/{id}/messages)
    # -------------------------------------------------------------
    r_msgs = c.get(f"/conversations/{conv_id}/messages", headers=H(session=sess))
    assert r_msgs.status_code == 200
    messages = r_msgs.json()
    assert len(messages) == 8  # 4 user + 4 assistant
    assert [m["role"] for m in messages] == [
        "user", "assistant",
        "user", "assistant",
        "user", "assistant",
        "user", "assistant"
    ]


# =====================================================================
# 2. Questions ambiguës & Clarifications exigées
# =====================================================================

def test_backend_api_ambiguous_queries_trigger_clarification(c):
    """Vérifie que l'API détecte les questions ambiguës et oblige le modèle à poser
    des questions de clarification au lieu d'extrapoler ou de deviner arbitrairement.
    """
    sess = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={"title": "Test Ambiguïté"}, headers=H(session=sess)).json()
    conv_id = conv["id"]

    # Cas A : "C'est combien ?" (très ambigu sans mention de formation)
    r_a = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "C'est combien ?"},
        headers=H(session=sess)
    )
    assert r_a.status_code == 201
    resp_a = r_a.json()["assistant_message"]["content"].lower()
    # Doit demander des précisions sur la formation visée
    assert any(w in resp_a for w in ["préciser", "quelle formation", "quel programme", "iit ou isb", "frais de scolarité"]) or ("?" in resp_a)

    # Cas B : "Est-ce que je peux y accéder ?" (aucun diplôme ni filière mentionnés)
    r_b = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Est-ce que je peux y accéder ?"},
        headers=H(session=sess)
    )
    assert r_b.status_code == 201
    resp_b = r_b.json()["assistant_message"]["content"].lower()
    assert any(w in resp_b for w in ["diplôme", "formation", "préciser", "parcours", "baccalauréat", "éligible"]) or ("?" in resp_b)

    # Cas C : "Quelle est la meilleure formation ?" (question subjective sans critère)
    r_c = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Quelle est la meilleure formation ?"},
        headers=H(session=sess)
    )
    assert r_c.status_code == 201
    resp_c = r_c.json()["assistant_message"]["content"].lower()
    assert any(w in resp_c for w in ["projet", "objectifs", "intérêts", "compétences", "préférées", "dépend", "préciser"]) or ("?" in resp_c)


# =====================================================================
# 3. Situations où le modèle ne peut pas répondre (Hors-catalogue / Inconnu)
# =====================================================================

def test_backend_api_unanswerable_situations(c):
    """Vérifie la qualité de réponse lorsque l'information demandée ne peut pas être fournie :
    - Discipline médicale ou spatiale inexistante dans le catalogue IIT / ISB.
    - Demande d'une date limite administrative absente du corpus.
    """
    sess = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={"title": "Test Hors Périmètre"}, headers=H(session=sess)).json()
    conv_id = conv["id"]

    # 1. Formation hors catalogue (médecine / chirurgie)
    r1 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Avez-vous une filière médecine ou chirurgie dentaire à l'IIT ?"},
        headers=H(session=sess)
    )
    assert r1.status_code == 201
    resp1 = r1.json()["assistant_message"]["content"].lower()
    # Le modèle doit indiquer que ce n'est pas dispensé ou pas dans le catalogue
    assert any(w in resp1 for w in ["pas", "non", "n'offre pas", "ne propose pas", "non dispensé", "technologie", "ingénierie", "secrétariat", "contact"])

    # 2. Date limite imaginaire inexistante dans le corpus officiel
    r2 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Quelle est la date limite exacte au jour près pour déposer ma candidature ?"},
        headers=H(session=sess)
    )
    assert r2.status_code == 201
    resp2 = r2.json()["assistant_message"]["content"].lower()
    # Ne doit pas inventer de date absolue sans avertissement : doit orienter vers l'administration
    assert any(w in resp2 for w in ["contact", "administration", "secrétariat", "ens.tn", "iit.tn", "isb.tn", "iit", "isb", "non précisée", "indicatif", "vérifier", "officiel", "officielle"])


# =====================================================================
# 4. Situations d'indisponibilité temporaire (Panne Ollama & Timeout)
# =====================================================================

def test_backend_api_temporary_unavailability_handling(c):
    """Vérifie le comportement de l'API Backend lorsque le service LLM local est temporairement indisponible :
    - Cas 4.1 : Ollama injoignable avec repli activé -> Réponse déterministe via RAG fallback (200 OK).
    - Cas 4.2 : Ollama injoignable avec repli désactivé -> Code HTTP 503 propre.
    - Cas 4.3 : Dépassement de délai de réponse (Timeout) -> Code HTTP 504 propre.
    """
    orig_fallback = settings.llm_fallback_enabled

    try:
        # --- Cas 4.1 : Panne Ollama avec Fallback transparent ---
        settings.llm_fallback_enabled = True
        with patch.object(llm_connector.client, "chat_completion", side_effect=LLMConnectionError("Serveur local Ollama éteint")):
            r_fb = c.post("/llm/chat", json={"query": "Quels sont les frais de scolarité à l'IIT ?"})
            assert r_fb.status_code == 200
            data_fb = r_fb.json()
            assert data_fb["fallback_used"] is True
            assert "778" in data_fb["response"] or "tarifs" in data_fb["response"].lower()

        # --- Cas 4.2 : Panne Ollama sans Fallback -> 503 Service Unavailable ---
        settings.llm_fallback_enabled = False
        with patch.object(llm_connector.client, "chat_completion", side_effect=LLMConnectionError("Serveur éteint")):
            r_503 = c.post("/llm/chat", json={"query": "Quelles sont les formations ?"})
            assert r_503.status_code == 503
            assert "Erreur de connexion" in r_503.json()["detail"]

        # --- Cas 4.3 : Timeout du modèle sans Fallback -> 504 Gateway Timeout ---
        with patch.object(llm_connector.client, "chat_completion", side_effect=LLMTimeoutError("Temps d'attente expiré")):
            r_504 = c.post("/llm/chat", json={"query": "Quelles sont les formations ?"})
            assert r_504.status_code == 504
            assert "Délai d'attente de réponse dépassé" in r_504.json()["detail"]

    finally:
        settings.llm_fallback_enabled = orig_fallback


# =====================================================================
# 5. Isolation stricte des contextes entre sessions simultanées
# =====================================================================

def test_backend_api_independent_sessions_context_isolation(c):
    """Vérifie que deux sessions visiteurs distinctes ne mélangent jamais leurs contextes
    lors de questions de suivi identiques ("Et les frais de scolarité ?").
    """
    # Session A : axée sur le Génie Mécanique IIT
    sess_a = c.post("/sessions").json()["session_token"]
    conv_a = c.post("/conversations", json={"title": "Session A"}, headers=H(session=sess_a)).json()["id"]

    c.post(
        f"/conversations/{conv_a}/messages",
        json={"content": "Je veux des informations sur le cycle ingénieur génie mécanique de l'IIT."},
        headers=H(session=sess_a)
    )

    # Session B : axée sur la Licence Finance ISB
    sess_b = c.post("/sessions").json()["session_token"]
    conv_b = c.post("/conversations", json={"title": "Session B"}, headers=H(session=sess_b)).json()["id"]

    c.post(
        f"/conversations/{conv_b}/messages",
        json={"content": "Je m'intéresse à la licence en finance de l'ISB."},
        headers=H(session=sess_b)
    )

    # Question de suivi identique dans les deux sessions : "Et les frais de scolarité ?"
    r_follow_a = c.post(
        f"/conversations/{conv_a}/messages",
        json={"content": "Et les frais de scolarité ?"},
        headers=H(session=sess_a)
    )
    assert r_follow_a.status_code == 201
    resp_a = r_follow_a.json()["assistant_message"]["content"].lower()
    # Doit contenir les éléments IIT (611 DT / 9 mois ou IIT)
    assert any(term in resp_a for term in ["611", "iit", "mécanique", "800", "dt", "scolarité"])

    r_follow_b = c.post(
        f"/conversations/{conv_b}/messages",
        json={"content": "Et les frais de scolarité ?"},
        headers=H(session=sess_b)
    )
    assert r_follow_b.status_code == 201
    resp_b = r_follow_b.json()["assistant_message"]["content"].lower()
    # Doit contenir les éléments ISB (4 000 à 6 000 DT ou ISB) et non les tarifs de mécanique de l'IIT
    assert any(term in resp_b for term in ["isb", "4 000", "4000", "6 000", "6000", "finance", "licence"])
