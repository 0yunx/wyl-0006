import re
import os
import time
import html
from collections import OrderedDict
from urllib.parse import urlparse, parse_qs, unquote

import httpx
from fastmcp import FastMCP

mcp = FastMCP("WebSearch")

SEARCH_URL = "https://html.duckduckgo.com/html/"
TIMEOUT = 10.0
MAX_COUNT = 20
_QUERY_SANITIZER = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_CACHE_MAX_SIZE = 64
_CACHE_TTL = int(os.environ.get("WEB_SEARCH_CACHE_TTL", "300"))
_search_cache: OrderedDict[str, tuple[float, list[dict]]] = OrderedDict()

_client = httpx.Client(
    timeout=TIMEOUT,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    },
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)


def _sanitize_query(query: str) -> str:
    cleaned = _QUERY_SANITIZER.sub("", query).strip()
    return cleaned


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
def web_search(query: str, count: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo and return results sorted by relevance.

    Args:
        query: The search query string.
        count: Number of results to return (1-20, default: 5).
    """
    query = _sanitize_query(query)
    if not query:
        return [
            {
                "title": "No results",
                "url": "",
                "snippet": "Empty query after sanitization",
            }
        ]

    count = max(1, min(count, MAX_COUNT))
    return _do_search(query, count)


def _cache_get(key: str) -> list[dict] | None:
    if key in _search_cache:
        ts, results = _search_cache[key]
        if time.time() - ts < _CACHE_TTL:
            _search_cache.move_to_end(key)
            return results
        del _search_cache[key]
    return None


def _cache_set(key: str, results: list[dict]) -> None:
    if key in _search_cache:
        del _search_cache[key]
    _search_cache[key] = (time.time(), results)
    while len(_search_cache) > _CACHE_MAX_SIZE:
        _search_cache.popitem(last=False)


def _do_search(query: str, count: int) -> list[dict]:
    try:
        response = _client.get(SEARCH_URL, params={"q": query})
        response.raise_for_status()
        results = _parse_search_results(response.text)
    except httpx.TimeoutException:
        return [
            {
                "title": "Request timed out",
                "url": "",
                "snippet": "The search request timed out, please try again later",
            }
        ]
    except httpx.HTTPError:
        return [
            {
                "title": "Request failed",
                "url": "",
                "snippet": "The search request failed due to a network error",
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


@mcp.tool()
def web_search_cache(query: str, count: int = 5) -> list[dict]:
    """
    Search the web using DuckDuckGo with LRU cache (max 64 entries, TTL 300s).
    Behaves identically to web_search but caches results; on cache hit the
    first result includes _cached=True so the caller knows the data may be stale.

    Args:
        query: The search query string.
        count: Number of results to return (1-20, default: 5).
    """
    query = _sanitize_query(query)
    if not query:
        return [
            {
                "title": "No results",
                "url": "",
                "snippet": "Empty query after sanitization",
                "_cached": False,
            }
        ]

    count = max(1, min(count, MAX_COUNT))
    cache_key = f"{query}\x00{count}"

    cached = _cache_get(cache_key)
    if cached is not None:
        results = [dict(r) for r in cached]
        if results:
            results[0]["_cached"] = True
        return results

    results = _do_search(query, count)
    _cache_set(cache_key, results)

    results = [dict(r) for r in results]
    if results:
        results[0]["_cached"] = False
    return results


def main():
    mcp.run()


if __name__ == "__main__":
    main()
