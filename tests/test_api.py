from fastapi.testclient import TestClient

from backend import main, search_agent

client = TestClient(main.app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_status_reports_generic_booleans_only():
    resp = client.get("/status")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"tier1_configured", "tier2_configured", "tier3_configured"}
    assert body == {"tier1_configured": False, "tier2_configured": False, "tier3_configured": False}


def test_query_falls_back_when_nothing_configured():
    resp = client.post("/query", json={"question": "What is the capital of France?"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"answer", "sources", "mode", "answer_id"}
    assert body["mode"] == "general"
    assert body["sources"] == []
    assert "answer_id" in body and body["answer_id"]


def test_query_never_leaks_exception_text(monkeypatch):
    def boom(question, session_id=None):
        raise RuntimeError("super secret internal detail")

    monkeypatch.setattr(search_agent, "answer_question", boom)

    # Starlette's ServerErrorMiddleware always re-raises after sending the
    # handler's response, specifically so TestClient can surface it for
    # debugging. raise_server_exceptions=False here checks what a real
    # client actually receives over the wire instead.
    lenient_client = TestClient(main.app, raise_server_exceptions=False)
    resp = lenient_client.post("/query", json={"question": "anything"})
    assert resp.status_code == 500
    assert resp.json() == {"detail": "An internal error occurred."}
    assert "super secret internal detail" not in resp.text


def test_request_id_header_present():
    resp = client.get("/health")
    assert "X-Request-ID" in resp.headers


def test_session_create_and_history():
    resp = client.post("/session")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    history_resp = client.get(f"/session/{session_id}")
    assert history_resp.status_code == 200
    assert history_resp.json() == {"session_id": session_id, "history": []}

    query_resp = client.post("/query", json={"question": "hello there", "session_id": session_id})
    assert query_resp.status_code == 200

    history_resp2 = client.get(f"/session/{session_id}")
    history = history_resp2.json()["history"]
    assert history[0] == {"role": "user", "content": "hello there"}
    assert history[1]["role"] == "assistant"


def test_session_history_unknown_session_returns_404():
    resp = client.get("/session/does-not-exist")
    assert resp.status_code == 404


def test_answer_share_link_and_feedback():
    query_resp = client.post("/query", json={"question": "what is rust programming language"})
    answer_id = query_resp.json()["answer_id"]

    answer_resp = client.get(f"/answer/{answer_id}")
    assert answer_resp.status_code == 200
    assert answer_resp.json()["answer_id"] == answer_id

    feedback_resp = client.post("/feedback", json={"answer_id": answer_id, "vote": "up"})
    assert feedback_resp.status_code == 200
    assert feedback_resp.json() == {"status": "ok"}

    bad_vote_resp = client.post("/feedback", json={"answer_id": answer_id, "vote": "sideways"})
    assert bad_vote_resp.status_code == 400

    unknown_resp = client.post("/feedback", json={"answer_id": "does-not-exist", "vote": "up"})
    assert unknown_resp.status_code == 404


def test_answer_not_found():
    resp = client.get("/answer/does-not-exist")
    assert resp.status_code == 404


def test_query_stream_emits_chunks_and_final_payload():
    with client.stream(
        "GET", "/query/stream", params={"question": "what is go programming language"}
    ) as resp:
        assert resp.status_code == 200
        lines = [line for line in resp.iter_lines() if line]

    assert any('"chunk"' in line for line in lines)
    assert any('"done": true' in line or '"done":true' in line for line in lines)


def test_auth_enforced_when_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "secret-key")

    resp = client.post("/query", json={"question": "hello"})
    assert resp.status_code == 401

    resp_ok = client.post(
        "/query", json={"question": "hello"}, headers={"X-API-Key": "secret-key"}
    )
    assert resp_ok.status_code == 200


def test_answer_endpoint_is_public_even_when_auth_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    query_resp = client.post("/query", json={"question": "what is a compiler"})
    answer_id = query_resp.json()["answer_id"]

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "secret-key")
    resp = client.get(f"/answer/{answer_id}")
    assert resp.status_code == 200
