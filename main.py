import re
import html
from typing import Optional
from urllib.parse import urlparse, parse_qs, unquote

import httpx
from fastmcp import FastMCP

mcp = FastMCP("WebSearch")

SEARCH_URL = "https://html.duckduckgo.com/html/"
TIMEOUT = 10.0


def _extract_real_url(ddg_url: str) -> str:
    if "uddg=" in ddg_url:
        parsed = urlparse(ddg_url)
        params = parse_qs(parsed.query)
        if "uddg" in params:
            return unquote(params["uddg"][0])
    if ddg_url.startswith("//"):
        return "https:" + ddg_url
    return ddg_url


def _parse_search_results(search_html: str) -> list[dict]:
    results: list[dict] = []
    pattern = re.compile(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
        r'[\s\S]*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    for match in pattern.finditer(search_html):
        raw_url = match.group(1).strip()
        title = html.unescape(re.sub(r"<[^>]+>", "", match.group(2)).strip())
        snippet = html.unescape(re.sub(r"<[^>]+>", "", match.group(3)).strip())
        real_url = _extract_real_url(raw_url)
        if real_url and title:
            results.append(
                {
                    "title": title,
                    "url": real_url,
                    "snippet": snippet,
                }
            )
    return results


@mcp.tool()
def web_search(query: str, count: Optional[int] = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo and return results sorted by relevance.

    Args:
        query: The search query string.
        count: Number of results to return (1-20, default: 5).
    """
    if count is None:
        count = 5
    if count < 1:
        count = 1
    if count > 20:
        count = 20

    results: list[dict] = []

    try:
        response = httpx.get(
            SEARCH_URL,
            params={"q": query},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        results = _parse_search_results(response.text)
    except (httpx.TimeoutException, httpx.HTTPError, Exception) as exc:
        return [
            {
                "error": f"Search request failed: {exc}",
                "title": "",
                "url": "",
                "snippet": "",
            }
        ]

    if not results:
        return [
            {
                "title": "No results",
                "url": "",
                "snippet": f"No results found for query: {query}",
            }
        ]

    return results[:count]


def main():
    mcp.run()


if __name__ == "__main__":
    main()
