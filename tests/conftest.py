import os
import tempfile

# Must run before any backend module is imported, since backend.db reads
# DB_PATH into a module-level constant at import time.
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="searchsage_test_")
os.close(_TEST_DB_FD)
os.environ["DB_PATH"] = _TEST_DB_PATH
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("NVIDIA_API_KEY", None)
os.environ.pop("OPENROUTER_API_KEY", None)

import pytest

from backend import db

db.init_db()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("AUTH_ENABLED", "false")
    yield
