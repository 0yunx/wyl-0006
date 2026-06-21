# WebSearch MCP Server

基于 Python 3.12、FastMCP 和 httpx 的 DuckDuckGo 网页搜索 MCP Server。

## 运行

```bash
uv run main.py
```

以 MCP stdio 传输方式启动 `WebSearch` 服务器。

## 工具

### `web_search(query: str, count: int = 5) -> list[dict]`

使用 DuckDuckGo 搜索网页，按相关性返回结果列表。每条结果包含 `title`、`url`、`snippet`。
- `query`: 搜索关键词字符串
- `count`: 返回条数 (1-20，默认 5)

### `web_search_cache(query: str, count: int = 5) -> list[dict]`

与 `web_search` 相同，但启用 LRU 缓存（最多 64 条，TTL 300 秒，可通过环境变量 `WEB_SEARCH_CACHE_TTL` 调整）。缓存命中时，首条结果会附加 `_cached=True` 字段。

### `web_search_multi(queries: list[str], count: int = 3) -> dict[str, list[dict]]`

并发搜索多个关键词，返回以原始 query 字符串为 key 的嵌套 dict。
- `queries`: 1-5 个搜索关键词字符串组成的列表，每个元素必须是 `str` 类型
- `count`: 每个 query 返回条数 (1-5，默认 3)，所有 query 返回结果总数不超过 50 条

特点：
- 使用 `asyncio` + `httpx.AsyncClient` 并发请求，不阻塞
- 单个 query 超时或失败不会影响其他 query，失败对应 value 为 `[]` 空列表
- 结果按输入 query 顺序保留在返回 dict 的 key 中

## 依赖

见 `pyproject.toml`：
- `fastmcp>=0.5.0`
- `httpx>=0.27.0`

Python ≥ 3.12。
