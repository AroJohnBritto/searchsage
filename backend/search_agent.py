import logging
import os
import uuid

from backend import cache, db
from backend.errors import ConfigError, ProviderError
from backend.retry import with_retry
from backend.tools import gemini_tool, nvidia_tool, scrape_tool, websearch_tool
from backend.tools.query_classifier import needs_search
from backend.tools.sanitize import sanitize_web_content

logger = logging.getLogger(__name__)

FALLBACK_ANSWER = (
    "I was not able to find an answer right now. Please try again in a little while."
)

DEEPSEEK_MODEL = "deepseek/deepseek-r1:free"


@with_retry()
def _run_gemini(question: str, history: list[dict], use_grounding: bool) -> tuple[str, list[str]]:
    return gemini_tool.generate(question, history, use_grounding=use_grounding)


@with_retry()
def _run_nvidia(question: str, history: list[dict]) -> str:
    return nvidia_tool.generate(question, history)


@with_retry()
def _run_openrouter(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ConfigError("OPENROUTER_API_KEY is not configured.")

    app_url = os.getenv("APP_URL", "http://localhost:8000")

    try:
        from openai import OpenAI

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": app_url,
                "X-Title": "SearchSage",
            },
        )
    except Exception as exc:
        raise ProviderError(f"openrouter call failed: {exc}") from exc

    answer = response.choices[0].message.content
    if not answer or not answer.strip():
        raise ProviderError("openrouter returned an empty response.")

    return answer.strip()


def _try_tier1(question: str, history: list[dict]) -> tuple[str, list[str], str] | None:
    use_grounding = needs_search(question)
    try:
        answer, sources = _run_gemini(question, history, use_grounding)
        mode = "live" if sources else "general"
        return answer, sources, mode
    except ConfigError as exc:
        logger.info("tier1 skipped, not configured: %s", exc)
    except ProviderError as exc:
        logger.warning("tier1 failed: %s", exc)
    return None


def _try_tier2(question: str, history: list[dict]) -> tuple[str, list[str], str] | None:
    try:
        answer = _run_nvidia(question, history)
        return answer, [], "general"
    except ConfigError as exc:
        logger.info("tier2 skipped, not configured: %s", exc)
    except ProviderError as exc:
        logger.warning("tier2 failed: %s", exc)
    return None


def _try_tier3(question: str) -> tuple[str, list[str], str] | None:
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ConfigError("OPENROUTER_API_KEY is not configured.")

        urls = websearch_tool.search_web(question)
        scraped_text, sources = scrape_tool.scrape_urls(urls)
        if not scraped_text:
            raise ProviderError("no content could be scraped for this question.")

        sanitized = sanitize_web_content(scraped_text)
        prompt = (
            "Answer the question using only the reference data provided below.\n\n"
            f"Question: {question}\n\n"
            f"Reference data:\n{sanitized}\n\n"
            "Answer:"
        )
        answer = _run_openrouter(prompt)
        return answer, sources, "live"
    except ConfigError as exc:
        logger.info("tier3 skipped, not configured: %s", exc)
    except ProviderError as exc:
        logger.warning("tier3 failed: %s", exc)
    return None


def answer_question(question: str, session_id: str | None = None) -> dict:
    history = db.get_history(session_id) if session_id else []

    result = None
    if not session_id:
        cached = cache.get_cached_answer(question)
        if cached is not None:
            logger.info("cache hit for context-free question")
            result = (cached["answer"], cached["sources"], cached["mode"])

    if result is None:
        result = _try_tier1(question, history) or _try_tier2(question, history) or _try_tier3(question)

    if result is None:
        answer, sources, mode = FALLBACK_ANSWER, [], "general"
    else:
        answer, sources, mode = result
        if not session_id:
            cache.set_cached_answer(question, {"answer": answer, "sources": sources, "mode": mode})

    answer_id = uuid.uuid4().hex
    db.save_answer(answer_id, session_id, question, answer, sources, mode)

    if session_id:
        db.add_message(session_id, "user", question)
        db.add_message(session_id, "assistant", answer, answer_id=answer_id)

    return {"answer": answer, "sources": sources, "mode": mode, "answer_id": answer_id}
