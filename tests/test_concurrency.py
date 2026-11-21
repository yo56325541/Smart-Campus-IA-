"""Tests de concurrence réelle sous PostgreSQL (Section 3.A & 8).
Simule des accès concurrents stricts multi-threads avec verrouillage de ligne PostgreSQL.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.database import engine
from app.main import app
from .conftest import ADMIN, H, IS_SQLITE


def _candidate(c, email: str, session: str | None = None) -> dict:
    r = c.post("/auth/register", json={"email": email, "password": "Password123!"}, headers=H(session=session))
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.skipif(IS_SQLITE, reason="Concurrence de verrouillage de ligne testée sur PostgreSQL")
def test_concurrent_claim_same_unowned_session(c):
    """Cas 1 & 2 : Deux candidats tentent simultanément de rattacher la même session anonyme."""
    # 1. Créer une session anonyme et une conversation
    sess = c.post("/sessions").json()["session_token"]
    conv = c.post("/conversations", json={"title": "Orientation Info"}, headers=H(session=sess)).json()

    cand1 = _candidate(c, "c1_race@test.tn")
    cand2 = _candidate(c, "c2_race@test.tn")

    results = []

    def try_link(cand_data):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/sessions/link", headers=H(cand_data["access_token"], sess))
            results.append((cand_data["user"]["id"], resp.status_code, resp.json()))

    t1 = threading.Thread(target=try_link, args=(cand1,))
    t2 = threading.Thread(target=try_link, args=(cand2,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactement un candidat doit réussir (200), l'autre doit recevoir 409 (Session déjà rattachée)
    status_codes = [r[1] for r in results]
    assert sorted(status_codes) == [200, 409], f"Résultats inattendus: {results}"

    # Identifier le gagnant
    winner_id = [r[0] for r in results if r[1] == 200][0]
    loser_id = [r[0] for r in results if r[1] == 409][0]

    # Vérification d'intégrité : la conversation et la session appartiennent au gagnant
    winner_tok = cand1["access_token"] if cand1["user"]["id"] == winner_id else cand2["access_token"]
    loser_tok = cand2["access_token"] if cand1["user"]["id"] == winner_id else cand1["access_token"]

    r_winner = c.get(f"/conversations/{conv['id']}", headers=H(winner_tok))
    assert r_winner.status_code == 200
    assert r_winner.json()["user_id"] == winner_id

    # Le perdant ne doit pas pouvoir y accéder (404)
    r_loser = c.get(f"/conversations/{conv['id']}", headers=H(loser_tok))
    assert r_loser.status_code == 404


@pytest.mark.skipif(IS_SQLITE, reason="Concurrence testée sur PostgreSQL")
def test_concurrent_idempotent_linking_same_candidate(c):
    """Cas 3 : Le même candidat tente de lier la même session deux fois en parallèle."""
    sess = c.post("/sessions").json()["session_token"]
    c.post("/conversations", json={"title": "Question"}, headers=H(session=sess))
    cand = _candidate(c, "c_same@test.tn")

    results = []

    def link_twice():
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/sessions/link", headers=H(cand["access_token"], sess))
            results.append(resp.status_code)

    threads = [threading.Thread(target=link_twice) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Toutes les requêtes du même candidat doivent réussir (idempotence)
    assert set(results) == {200}, f"Statuts reçus : {results}"


@pytest.mark.skipif(IS_SQLITE, reason="Concurrence testée sur PostgreSQL")
def test_session_owned_by_candidate_a_requested_by_candidate_b(c):
    """Cas 4 : Une session déjà liée à Candidat A est demandée par Candidat B."""
    sess = c.post("/sessions").json()["session_token"]
    cand_a = _candidate(c, "user_a@test.tn", sess)
    cand_b = _candidate(c, "user_b@test.tn")

    # B tente de lier la session de A
    r_link = c.post("/sessions/link", headers=H(cand_b["access_token"], sess))
    assert r_link.status_code == 409
    assert "déjà rattachée" in r_link.json()["detail"]

    # B tente d'accéder aux conversations avec son JWT et la session de A
    r_conv = c.get("/conversations", headers=H(cand_b["access_token"], sess))
    assert r_conv.status_code == 403


@pytest.mark.skipif(IS_SQLITE, reason="Concurrence testée sur PostgreSQL")
def test_conversation_created_while_linking_session(c):
    """Cas 5 : Une conversation est créée pendant qu'une requête tente de lier sa session."""
    sess = c.post("/sessions").json()["session_token"]
    cand = _candidate(c, "interleave@test.tn")

    created_convs = []

    def make_conv():
        with TestClient(app, raise_server_exceptions=False) as client:
            r = client.post("/conversations", json={"title": "Raced Conv"}, headers=H(session=sess))
            if r.status_code in (201, 403):
                created_convs.append(r.status_code)

    def do_link():
        with TestClient(app, raise_server_exceptions=False) as client:
            client.post("/sessions/link", headers=H(cand["access_token"], sess))

    t1 = threading.Thread(target=make_conv)
    t2 = threading.Thread(target=do_link)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Si la conversation a été créée avant ou pendant le link, elle doit appartenir au candidat ou rester cohérente
    convs = c.get("/conversations", headers=H(cand["access_token"])).json()
    for cv in convs:
        assert cv["user_id"] == cand["user"]["id"]
