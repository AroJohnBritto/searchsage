import requests

MAX_PAGES = 2
MAX_PARAGRAPHS_PER_PAGE = 8


def scrape_urls(urls: list[str]) -> tuple[str, list[str]]:
    """Scrape each URL and return (combined_text, sources).

    Returns a tuple rather than storing state in a module-level variable,
    since FastAPI runs each request in a thread-pool executor and a shared
    global would get clobbered between concurrent requests. On failure a
    URL is skipped silently, never replaced with placeholder text that
    could get fed to the LLM as if it were real page content.
    """
    from bs4 import BeautifulSoup

    contents: list[str] = []
    sources: list[str] = []

    for url in urls:
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            response.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
        if not paragraphs:
            continue

        contents.append(" ".join(paragraphs[:MAX_PARAGRAPHS_PER_PAGE]))
        sources.append(url)

        if len(contents) >= MAX_PAGES:
            break

    if not contents:
        return "", []

    return "\n\n".join(contents), sources
