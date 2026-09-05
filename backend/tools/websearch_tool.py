from urllib.parse import parse_qs, unquote, urlparse

import requests

from backend.errors import ProviderError

DUCKDUCKGO_HTML_URL = "https://duckduckgo.com/html/"
MAX_RESULTS = 5


def search_web(query: str) -> list[str]:
    """Search DuckDuckGo's HTML endpoint and return a list of result URLs.

    The query is passed via params= so requests handles URL encoding,
    rather than being interpolated raw into the URL string.
    """
    try:
        response = requests.get(
            DUCKDUCKGO_HTML_URL,
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ProviderError(f"web search request failed: {exc}") from exc

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "html.parser")
    raw_links = [a["href"] for a in soup.select("a.result__a") if a.has_attr("href")]

    urls: list[str] = []
    for raw in raw_links:
        parsed = urlparse(raw)
        if parsed.netloc == "duckduckgo.com" and parsed.path.startswith("/l/"):
            real_url = parse_qs(parsed.query).get("uddg", [None])[0]
            if real_url:
                urls.append(unquote(real_url))
        elif raw.startswith("http"):
            urls.append(raw)

    if not urls:
        raise ProviderError("web search returned no results.")

    return urls[:MAX_RESULTS]
