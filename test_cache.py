import asyncio
import os
import sys
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

SERVER = "main.py"


def _make_env(extra=None):
    env = dict(os.environ)
    if extra:
        env.update(extra)
    return env


async def test_basic():
    async with Client(SERVER) as client:
        tools = await client.list_tools()
        print("=== Registered tools ===")
        for t in tools:
            print(f"  - {t.name}")
        print()

        query = "Python programming language"
        print("=== Test 1: Cache miss then hit ===")
        r1 = await client.call_tool("web_search_cache", {"query": query, "count": 3})
        d1 = r1.data
        c1 = d1[0].get("_cached") if d1 else "N/A"
        print(f"  First call  _cached = {c1}  (expected False)")

        r2 = await client.call_tool("web_search_cache", {"query": query, "count": 3})
        d2 = r2.data
        c2 = d2[0].get("_cached") if d2 else "N/A"
        print(f"  Second call _cached = {c2}  (expected True)")

        assert c1 is False, f"Expected False, got {c1}"
        assert c2 is True, f"Expected True, got {c2}"
        print("  ✓ Cache hit/miss PASSED")
        print()

        print("=== Test 2: Different query produces cache miss ===")
        r3 = await client.call_tool("web_search_cache", {"query": "Rust programming language", "count": 3})
        d3 = r3.data
        c3 = d3[0].get("_cached") if d3 else "N/A"
        print(f"  Different query _cached = {c3}  (expected False)")
        assert c3 is False, f"Expected False, got {c3}"
        print("  ✓ Different query cache miss PASSED")
        print()

        print("=== Test 3: web_search tool still works (no _cached field) ===")
        r4 = await client.call_tool("web_search", {"query": "Java programming", "count": 1})
        d4 = r4.data
        has_cached = "_cached" in d4[0] if d4 else True
        print(f"  web_search has _cached field: {has_cached}  (expected False)")
        assert not has_cached, "web_search should not have _cached field"
        print("  ✓ web_search unchanged PASSED")
        print()


async def test_ttl():
    env = _make_env({"WEB_SEARCH_CACHE_TTL": "2"})
    transport = StdioTransport(
        command=sys.executable,
        args=["main.py"],
        env=env,
        cwd=os.getcwd(),
    )

    async with Client(transport) as client:
        query = "TTL test query unique 12345"
        print("=== Test 4: TTL expiry (2s TTL) ===")

        r1 = await client.call_tool("web_search_cache", {"query": query, "count": 1})
        d1 = r1.data
        c1 = d1[0].get("_cached") if d1 else "N/A"
        print(f"  First call  _cached = {c1}  (expected False)")
        assert c1 is False

        r2 = await client.call_tool("web_search_cache", {"query": query, "count": 1})
        d2 = r2.data
        c2 = d2[0].get("_cached") if d2 else "N/A"
        print(f"  Immediate second call _cached = {c2}  (expected True)")
        assert c2 is True

        print("  Waiting 3 seconds for TTL to expire...")
        await asyncio.sleep(3)

        r3 = await client.call_tool("web_search_cache", {"query": query, "count": 1})
        d3 = r3.data
        c3 = d3[0].get("_cached") if d3 else "N/A"
        print(f"  After TTL expiry _cached = {c3}  (expected False)")
        assert c3 is False
        print("  ✓ TTL expiry PASSED")
        print()


async def main_all():
    await test_basic()
    await test_ttl()
    print("=== All tests PASSED ===")


if __name__ == "__main__":
    asyncio.run(main_all())
