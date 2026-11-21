import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import create_app
from app.services.llm_service import LLMService, SYSTEM_PROMPT

URL = "/api/v1/chat/messages"


def make_client(handler):
    """Client de test avec un faux LLM (aucun appel reseau reel)."""
    llm = LLMService(get_settings(), transport=httpx.MockTransport(handler))
    return TestClient(create_app(llm=llm))


def ok_handler(captured):
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={
            "choices": [{"message": {"content": " Reponse de test "}}]})
    return handler


def test_health():
    c = make_client(ok_handler([]))
    assert c.get("/api/v1/health").json() == {"status": "ok"}


def test_first_message_creates_conversation():
    cap = []
    r = make_client(ok_handler(cap)).post(URL, json={"message": "Bonjour"})
    assert r.status_code == 200
    data = r.json()
    assert data["conversation_id"] and data["reply"] == "Reponse de test"
    assert cap[0]["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}


def test_history_is_sent_on_second_message():
    cap = []
    c = make_client(ok_handler(cap))
    cid = c.post(URL, json={"message": "Quels masters ?"}).json()["conversation_id"]
    c.post(URL, json={"message": "Et les tarifs ?", "conversation_id": cid})
    roles = [m["role"] for m in cap[1]["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert cap[1]["messages"][1]["content"] == "Quels masters ?"


@pytest.mark.parametrize("msg", [
    "chnowa el conditions mta3 el inscription ?",   # Arabizi
    "شنوة شروط القبول في الماجستير؟",                  # arabe / dialecte
    "Bch nconsulti el tarifs, 3andkom bourse ?",     # melange
])
def test_dialect_and_arabizi_passthrough(msg):
    cap = []
    r = make_client(ok_handler(cap)).post(URL, json={"message": msg})
    assert r.status_code == 200
    assert cap[0]["messages"][-1]["content"] == msg


def test_history_limit_is_respected():
    cap = []
    c = make_client(ok_handler(cap))
    cid = None
    for i in range(8):
        cid = c.post(URL, json={"message": f"q{i}", "conversation_id": cid}
                     ).json()["conversation_id"]
    # 1 system + 10 (limite) + 1 message courant
    assert len(cap[-1]["messages"]) == 12


def test_empty_message_rejected():
    r = make_client(ok_handler([])).post(URL, json={"message": ""})
    assert r.status_code == 422


def test_llm_http_error_gives_502():
    c = make_client(lambda req: httpx.Response(500))
    assert c.post(URL, json={"message": "Salut"}).status_code == 502


def test_llm_invalid_payload_gives_502():
    c = make_client(lambda req: httpx.Response(200, json={"oops": 1}))
    assert c.post(URL, json={"message": "Salut"}).status_code == 502


def test_failed_call_does_not_pollute_memory():
    c = make_client(lambda req: httpx.Response(500))
    r = c.post(URL, json={"message": "Salut", "conversation_id": "abc"})
    assert r.status_code == 502
    assert c.get("/api/v1/chat/conversations/abc/messages").json() == []
