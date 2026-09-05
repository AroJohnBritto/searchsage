import uuid

from backend import cache, db


def test_session_create_and_history_round_trip():
    session_id = uuid.uuid4().hex
    db.create_session(session_id)
    assert db.session_exists(session_id) is True
    assert db.session_exists("nonexistent") is False

    db.add_message(session_id, "user", "hello")
    db.add_message(session_id, "assistant", "hi there", answer_id="abc123")

    history = db.get_history(session_id)
    assert history == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


def test_save_and_get_answer():
    answer_id = uuid.uuid4().hex
    db.save_answer(answer_id, None, "what is python", "a programming language", ["https://x.com"], "general")

    result = db.get_answer(answer_id)
    assert result == {
        "answer_id": answer_id,
        "answer": "a programming language",
        "sources": ["https://x.com"],
        "mode": "general",
    }
    assert db.get_answer("missing") is None


def test_feedback_insert_does_not_raise():
    answer_id = uuid.uuid4().hex
    db.save_answer(answer_id, None, "q", "a", [], "general")
    db.save_feedback(answer_id, "up")


def test_cache_round_trip_and_expiry():
    question = f"cache test question {uuid.uuid4().hex}"
    payload = {"answer": "42", "sources": [], "mode": "general"}

    assert cache.get_cached_answer(question) is None

    cache.set_cached_answer(question, payload, ttl_seconds=60)
    assert cache.get_cached_answer(question) == payload

    cache.set_cached_answer(question, payload, ttl_seconds=-1)
    assert cache.get_cached_answer(question) is None
