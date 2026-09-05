import pytest
import requests

from backend.errors import ProviderError
from backend.tools import websearch_tool


class FakeResponse:
    def __init__(self, text, status_ok=True):
        self.text = text
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.RequestException("bad status")


def test_search_web_passes_query_via_params(monkeypatch):
    captured = {}

    html = '<a class="result__a" href="https://real-site.com/page">Result</a>'

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse(html)

    monkeypatch.setattr(websearch_tool.requests, "get", fake_get)

    urls = websearch_tool.search_web("hello world & special chars?")
    assert captured["params"] == {"q": "hello world & special chars?"}
    assert urls == ["https://real-site.com/page"]


def test_search_web_resolves_duckduckgo_redirect(monkeypatch):
    html = (
        '<a class="result__a" '
        'href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpath&amp;rut=1">Result</a>'
    )

    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(html)

    monkeypatch.setattr(websearch_tool.requests, "get", fake_get)

    urls = websearch_tool.search_web("example")
    assert urls == ["https://example.com/path"]


def test_search_web_raises_provider_error_on_request_failure(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        raise requests.RequestException("timeout")

    monkeypatch.setattr(websearch_tool.requests, "get", fake_get)

    with pytest.raises(ProviderError):
        websearch_tool.search_web("anything")


def test_search_web_raises_provider_error_on_no_results(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse("<html><body>no results here</body></html>")

    monkeypatch.setattr(websearch_tool.requests, "get", fake_get)

    with pytest.raises(ProviderError):
        websearch_tool.search_web("anything")
