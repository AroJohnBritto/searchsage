import requests
from bs4 import BeautifulSoup

last_sources = []

def scrape_urls(url_list_str: str) -> str:
    global last_sources
    urls = url_list_str.strip().split("\n")
    contents = []
    last_sources.clear()

    for url in urls:
        try:
            print(f"Scraping URL: {url}")
            res = requests.get(url, timeout=8)
            soup = BeautifulSoup(res.text, "html.parser")

            paragraphs = [p.get_text() for p in soup.find_all("p") if p.get_text().strip()]
            text = " ".join(paragraphs[:8])
            if text:
                contents.append(text)
                last_sources.append(url)
        except Exception as e:
            print(f"[scrape_tool] Failed to scrape {url}: {e}")
            continue

    if not contents:
        print("[scrape_tool] No content extracted from any URLs.")
        return "We were unable to extract relevant content from the web."

    return "\n\n".join(contents[:2])
