import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote

def search_web(query: str) -> str:
    try:
        url = f"https://duckduckgo.com/html/?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        raw_links = [a["href"] for a in soup.select("a.result__a") if a.has_attr("href")]
        final_links = []

        for raw in raw_links:
            parsed = urlparse(raw)
            if parsed.netloc == "duckduckgo.com" and parsed.path.startswith("/l/"):
                # Extract actual target from uddg param
                params = parse_qs(parsed.query)
                real_url = params.get("uddg", [None])[0]
                if real_url:
                    final_links.append(unquote(real_url))
            else:
                final_links.append(raw)

        return "\n".join(final_links[:5])  # return top 5 clean URLs

    except Exception as e:
        print(f"[websearch_tool] Search failed: {e}")
        return ""
