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
