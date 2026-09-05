import pytest

from backend.errors import ConfigError
from backend.tools import nvidia_tool


def test_generate_raises_config_error_without_api_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        nvidia_tool.generate("hello", [])


def test_generate_raises_config_error_without_model(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key")
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)
    with pytest.raises(ConfigError):
        nvidia_tool.generate("hello", [])


def test_build_messages_never_includes_a_system_role():
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello there"},
    ]
    messages = nvidia_tool._build_messages(history, "what is the weather")

    assert all(m["role"] != "system" for m in messages)
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert "what is the weather" in messages[-1]["content"]
