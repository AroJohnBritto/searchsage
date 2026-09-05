import re

_LIVE_KEYWORDS = [
    "today", "current", "currently", "now", "latest", "recent", "recently",
    "this week", "this month", "this year", "yesterday", "tomorrow",
    "price", "stock", "weather", "score", "scores", "news", "headline",
    "election", "who won", "who is winning", "release date", "upcoming",
    "live", "breaking",
]

_DEFINITIONAL_PATTERNS = [
    r"^what is\b",
    r"^what are\b",
    r"^what does\b.*\bmean\b",
    r"^define\b",
    r"^explain\b",
    r"^how (do|does|to|can) i?\b",
    r"^why (is|are|does|do)\b",
    r"^difference between\b",
    r"\bhow to\b",
    r"^write (a|an|some)\b",
    r"^translate\b",
    r"^calculate\b",
]

_YEAR_PATTERN = re.compile(r"\b20(2[4-9]|[3-9]\d)\b")

_COMPILED_DEFINITIONAL = [re.compile(pattern, re.IGNORECASE) for pattern in _DEFINITIONAL_PATTERNS]


def needs_search(question: str) -> bool:
    """Heuristic deciding whether a question needs live web grounding.

    Time-sensitive keywords or a recent/future year mention always trigger
    search. Otherwise, definitional or how-to phrasing skips it to save
    latency. Anything else defaults to using search, since a false negative
    (skipping search when it was needed) is worse than the extra latency of
    a false positive.
    """
    lowered = question.strip().lower()

    if any(keyword in lowered for keyword in _LIVE_KEYWORDS):
        return True

    if _YEAR_PATTERN.search(lowered):
        return True

    if any(pattern.search(lowered) for pattern in _COMPILED_DEFINITIONAL):
        return False

    return True
