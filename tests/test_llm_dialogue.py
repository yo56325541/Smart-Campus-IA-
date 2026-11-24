"""Tests pour la connexion du LLM, la mémoire conversationnelle et le dialogue (SA-26, SA-36, SA-38)."""
import pytest
from fastapi.testclient import TestClient

from .conftest import ADMIN, H


def _admin(c):
    return c.post("/auth/login", json=ADMIN).json()["access_token"]


def _candidate(c, email: str, session: str | None = None) -> dict:
    r = c.post("/auth/register", json={"email": email, "password": "Password123!"}, headers=H(session=session))
    assert r.status_code == 201, r.text
    return r.json()


def test_visitor_chat_with_llm_and_memory(c):
    """Dialogue avec le LLM en tant que visiteur anonyme et persistance des messages (SA-36, SA-38)."""
    # 1. Créer une session visiteur
    sess = c.post("/sessions").json()["session_token"]

    # 2. Créer une conversation
    conv = c.post("/conversations", json={}, headers=H(session=sess)).json()
    conv_id = conv["id"]

    # 3. Premier message : Salutation en dialecte tunisien / Arabizi (SA-34)
    r1 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "aslema marhba"},
        headers=H(session=sess)
    )
    assert r1.status_code == 201
    d1 = r1.json()
    assert d1["user_message"]["role"] == "user"
    assert d1["user_message"]["content"] == "aslema marhba"
    assert d1["assistant_message"]["role"] == "assistant"
    assert "SmartCampus AI" in d1["assistant_message"]["content"]

    # 4. Deuxième message : Demande de tarifs en dialecte (b9adeh / flous)
    r2 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "b9adeh les frais de licence informatique ?"},
        headers=H(session=sess)
    )
    assert r2.status_code == 201
    d2 = r2.json()
    assert d2["assistant_message"]["role"] == "assistant"
    assert "tarifs" in d2["assistant_message"]["content"].lower()

    # 5. Vérifier la mémoire conversationnelle complète via GET (SA-26)
    r_msgs = c.get(f"/conversations/{conv_id}/messages", headers=H(session=sess))
    assert r_msgs.status_code == 200
    msgs = r_msgs.json()
    assert len(msgs) == 4  # 2 messages user + 2 messages assistant
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]


def test_llm_dialogue_candidate_and_session_linking(c):
    """Vérifie que l'historique conversationnel est préservé lors du rattachement de session (SA-29, SA-38)."""
    # 1. Visiteur commence une discussion
    sess = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={"title": "Orientation"}, headers=H(session=sess)).json()
    conv_id = conv["id"]

    c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Quelles sont les conditions d'admission au cycle ingénieur ?"},
        headers=H(session=sess)
    )

    # 2. Le visiteur s'inscrit en candidat
    cand = _candidate(c, "dialogue_link@test.tn", session=sess)
    cand_tok = cand["access_token"]
    user_id = cand["user"]["id"]

    # 3. La conversation et ses messages appartiennent maintenant au candidat
    r_msgs = c.get(f"/conversations/{conv_id}/messages", headers=H(cand_tok))
    assert r_msgs.status_code == 200
    msgs = r_msgs.json()
    assert len(msgs) == 2  # user + assistant

    # 4. Le candidat peut poursuivre la conversation
    r3 = c.post(
        f"/conversations/{conv_id}/messages",
        json={"content": "Est-ce qu'il y a un concours ou un entretien oral ?"},
        headers=H(cand_tok)
    )
    assert r3.status_code == 201
    assert r3.json()["assistant_message"]["role"] == "assistant"

    # Vérification que le total est désormais de 4 messages
    r_updated = c.get(f"/conversations/{conv_id}/messages", headers=H(cand_tok))
    assert len(r_updated.json()) == 4


def test_conversation_messages_isolation(c):
    """Isolation stricte : un utilisateur tiers ne peut ni lire ni poster de message."""
    s1 = c.post("/sessions").json()["session_token"]
    s2 = c.post("/sessions").json()["session_token"]

    conv1 = c.post("/conversations", json={}, headers=H(session=s1)).json()

    # Tentative d'écriture depuis une autre session
    r_post = c.post(
        f"/conversations/{conv1['id']}/messages",
        json={"content": "Hack"},
        headers=H(session=s2)
    )
    assert r_post.status_code == 404

    # Tentative de lecture depuis une autre session
    r_get = c.get(f"/conversations/{conv1['id']}/messages", headers=H(session=s2))
    assert r_get.status_code == 404
