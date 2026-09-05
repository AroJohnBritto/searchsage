import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend import db

DEFAULT_TTL_SECONDS = 3600


def _normalize_key(question: str) -> str:
    normalized = " ".join(question.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def get_cached_answer(question: str) -> Optional[dict]:
    """Look up a cached answer for a context-free question.

    Only context-free questions (no session) are cached, since a contextual
    answer depends on conversation history and is not safe to key by
    question text alone.
    """
    raw = db.cache_get(_normalize_key(question))
    if raw is None:
        return None
    return json.loads(raw)


def set_cached_answer(question: str, payload: dict, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
    db.cache_set(_normalize_key(question), json.dumps(payload), expires_at)
