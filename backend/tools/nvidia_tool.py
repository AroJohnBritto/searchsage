import os
from typing import Optional

from backend.errors import ConfigError, ProviderError

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer questions using your existing "
    "knowledge. If you are not confident about something time-sensitive, "
    "say so plainly instead of guessing."
)


def _build_messages(history: list[dict], question: str) -> list[dict]:
    """Build a messages list with no system role.

    Some hosted instruct models (Mistral's chat template among them) reject
    a system role message outright, so the guidance is folded into the
    latest user turn instead of sent as a separate message.
    """
    messages = []
    for turn in history:
        role = "assistant" if turn["role"] == "assistant" else "user"
        messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": f"{SYSTEM_PROMPT}\n\n{question}"})
    return messages


def generate(question: str, history: Optional[list[dict]] = None) -> str:
    """Knowledge-only fallback, no live search."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ConfigError("NVIDIA_API_KEY is not configured.")

    model = os.getenv("NVIDIA_MODEL")
    if not model:
        raise ConfigError("NVIDIA_MODEL is not configured.")

    history = history or []

    try:
        from openai import OpenAI

        client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=_build_messages(history, question),
            temperature=0.5,
        )
    except Exception as exc:
        raise ProviderError(f"nvidia call failed: {exc}") from exc

    answer = response.choices[0].message.content
    if not answer or not answer.strip():
        raise ProviderError("nvidia returned an empty response.")

    return answer.strip()
