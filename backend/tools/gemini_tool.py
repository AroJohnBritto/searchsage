import os
from typing import Optional

from backend.errors import ConfigError, ProviderError


def _build_contents(history: list[dict], question: str):
    from google.genai import types

    contents = []
    for turn in history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=question)]))
    return contents


def _apply_grounding_citations(response) -> tuple[str, list[str]]:
    """Parse groundingChunks/groundingSupports and insert [1][2] style inline
    citation markers into the answer text, matched to a numbered source list.
    """
    text = response.text or ""

    try:
        candidate = response.candidates[0]
        grounding_metadata = candidate.grounding_metadata
    except (IndexError, AttributeError, TypeError):
        return text, []

    if grounding_metadata is None:
        return text, []

    chunks = getattr(grounding_metadata, "grounding_chunks", None) or []
    supports = getattr(grounding_metadata, "grounding_supports", None) or []
    if not chunks:
        return text, []

    sources: list[str] = []
    chunk_to_source: dict[int, int] = {}
    for i, chunk in enumerate(chunks):
        web = getattr(chunk, "web", None)
        uri = getattr(web, "uri", None) if web else None
        if not uri:
            continue
        if uri not in sources:
            sources.append(uri)
        chunk_to_source[i] = sources.index(uri) + 1

    insertions: dict[int, str] = {}
    for support in supports:
        segment = getattr(support, "segment", None)
        indices = getattr(support, "grounding_chunk_indices", None) or []
        if segment is None or segment.end_index is None:
            continue
        markers = "".join(f"[{chunk_to_source[i]}]" for i in indices if i in chunk_to_source)
        if markers:
            insertions[segment.end_index] = insertions.get(segment.end_index, "") + markers

    for pos in sorted(insertions.keys(), reverse=True):
        if 0 <= pos <= len(text):
            text = text[:pos] + insertions[pos] + text[pos:]

    return text, sources


def generate(question: str, history: Optional[list[dict]] = None, use_grounding: bool = False) -> tuple[str, list[str]]:
    """Call Gemini, optionally with the native Google Search grounding tool.

    Returns (answer_text, sources). sources is empty when grounding was not
    attached or returned no grounding metadata.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ConfigError("GEMINI_API_KEY is not configured.")

    model = os.getenv("GEMINI_MODEL")
    if not model:
        raise ConfigError("GEMINI_MODEL is not configured.")

    history = history or []

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        contents = _build_contents(history, question)

        config = None
        if use_grounding:
            config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])

        response = client.models.generate_content(model=model, contents=contents, config=config)
    except Exception as exc:
        raise ProviderError(f"gemini call failed: {exc}") from exc

    text = (response.text or "").strip()
    if not text:
        raise ProviderError("gemini returned an empty response.")

    sources: list[str] = []
    if use_grounding:
        text, sources = _apply_grounding_citations(response)

    return text, sources
