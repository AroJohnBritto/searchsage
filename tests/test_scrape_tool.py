import requests

from backend.tools import scrape_tool


class FakeResponse:
    def __init__(self, text, status_ok=True):
        self.text = text
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.RequestException("bad status")


def test_scrape_urls_extracts_paragraphs(monkeypatch):
    html = "<html><body><p>First paragraph.</p><p>Second paragraph.</p></body></html>"

    def fake_get(url, headers=None, timeout=None):
        return FakeResponse(html)

    monkeypatch.setattr(scrape_tool.requests, "get", fake_get)

    text, sources = scrape_tool.scrape_urls(["https://example.com"])
    assert "First paragraph." in text
    assert "Second paragraph." in text
    assert sources == ["https://example.com"]


def test_scrape_urls_skips_failed_url(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        raise requests.RequestException("network down")

    monkeypatch.setattr(scrape_tool.requests, "get", fake_get)

    text, sources = scrape_tool.scrape_urls(["https://example.com"])
    assert text == ""
    assert sources == []


def test_scrape_urls_no_placeholder_text_on_empty_page(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return FakeResponse("<html><body></body></html>")

    monkeypatch.setattr(scrape_tool.requests, "get", fake_get)

    text, sources = scrape_tool.scrape_urls(["https://example.com"])
    assert text == ""
    assert sources == []
