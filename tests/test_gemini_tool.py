from dataclasses import dataclass
from typing import Optional

import pytest

from backend.errors import ConfigError
from backend.tools import gemini_tool


def test_generate_raises_config_error_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        gemini_tool.generate("hello", [], use_grounding=False)


def test_generate_raises_config_error_without_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    with pytest.raises(ConfigError):
        gemini_tool.generate("hello", [], use_grounding=False)


@dataclass
class FakeWeb:
    uri: str
    title: str


@dataclass
class FakeChunk:
    web: FakeWeb


@dataclass
class FakeSegment:
    end_index: int


@dataclass
class FakeSupport:
    segment: FakeSegment
    grounding_chunk_indices: list


@dataclass
class FakeGroundingMetadata:
    grounding_chunks: list
    grounding_supports: list


@dataclass
class FakeCandidate:
    grounding_metadata: Optional[FakeGroundingMetadata]


@dataclass
class FakeResponse:
    text: str
    candidates: list


def test_apply_grounding_citations_inserts_markers_and_dedupes_sources():
    text = "Paris is the capital of France. It has a population of about 2 million."
    chunks = [
        FakeChunk(web=FakeWeb(uri="https://a.com", title="A")),
        FakeChunk(web=FakeWeb(uri="https://b.com", title="B")),
        FakeChunk(web=FakeWeb(uri="https://a.com", title="A again")),
    ]
    supports = [
        FakeSupport(segment=FakeSegment(end_index=32), grounding_chunk_indices=[0]),
        FakeSupport(segment=FakeSegment(end_index=len(text)), grounding_chunk_indices=[1, 2]),
    ]
    response = FakeResponse(
        text=text,
        candidates=[FakeCandidate(grounding_metadata=FakeGroundingMetadata(chunks, supports))],
    )

    result_text, sources = gemini_tool._apply_grounding_citations(response)

    assert sources == ["https://a.com", "https://b.com"]
    assert "[1]" in result_text
    assert "[2]" in result_text
    assert result_text.endswith("[2][1]") or result_text.endswith("[1][2]")


def test_apply_grounding_citations_returns_empty_sources_when_no_metadata():
    response = FakeResponse(text="plain answer", candidates=[FakeCandidate(grounding_metadata=None)])
    result_text, sources = gemini_tool._apply_grounding_citations(response)
    assert result_text == "plain answer"
    assert sources == []
