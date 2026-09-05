import pytest

from backend.errors import ConfigError, ProviderError
from backend.retry import with_retry


def test_config_error_is_never_retried():
    calls = {"count": 0}

    @with_retry(max_attempts=3, base_delay=0)
    def func():
        calls["count"] += 1
        raise ConfigError("missing key")

    with pytest.raises(ConfigError):
        func()
    assert calls["count"] == 1


def test_provider_error_is_retried_up_to_max_attempts():
    calls = {"count": 0}

    @with_retry(max_attempts=3, base_delay=0)
    def func():
        calls["count"] += 1
        raise ProviderError("transient")

    with pytest.raises(ProviderError):
        func()
    assert calls["count"] == 3


def test_succeeds_after_transient_failures():
    calls = {"count": 0}

    @with_retry(max_attempts=3, base_delay=0)
    def func():
        calls["count"] += 1
        if calls["count"] < 2:
            raise ProviderError("transient")
        return "ok"

    assert func() == "ok"
    assert calls["count"] == 2
