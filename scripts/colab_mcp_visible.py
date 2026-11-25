"""Colab MCP entry that keeps notebook tools visible to clients.

Stock ``colab-mcp`` publishes ``add_code_cell`` and the other notebook tools only after
Helium attaches, via ``notifications/tools/list_changed``. This client lists tools once,
at process start, and does not apply that notification, so those tools never become
callable. This entry registers two stable tools before the first ``tools/list``:

- ``colab_list_tools`` returns the live notebook tool names and input schemas
- ``colab_call`` forwards one call to the connected notebook

``open_colab_browser_connection`` still comes from the stock server.
"""
import asyncio
import json
import sys

from colab_mcp import init_logger, mcp, parse_args
from colab_mcp.session import ColabSessionProxy

_proxy_client = None


def _connected() -> bool:
    return _proxy_client is not None and _proxy_client.is_connected()


@mcp.tool()
async def colab_list_tools() -> str:
    """List tools the connected Colab page is serving, with input schemas."""
    if not _connected():
        return "not connected. Call open_colab_browser_connection and click Connect in Helium."
    tools = await _proxy_client.proxy_mcp_client.list_tools()
    if not tools:
        return "connected, but the notebook has not published tools yet. Click Connect in Helium."
    out = []
    for t in tools:
        schema = getattr(t, "inputSchema", None)
        if schema is None:
            schema = getattr(t, "input_schema", None)
        out.append({
            "name": t.name,
            "description": getattr(t, "description", "") or "",
            "inputSchema": schema,
        })
    return json.dumps(out)


@mcp.tool()
async def colab_call(name: str, arguments_json: str = "{}") -> str:
    """Call a connected-notebook tool. ``arguments_json`` is a JSON object."""
    if not _connected():
        return "not connected. Call open_colab_browser_connection and click Connect in Helium."
    args = json.loads(arguments_json or "{}")
    if not isinstance(args, dict):
        return "arguments_json must be a JSON object"
    result = await _proxy_client.proxy_mcp_client.call_tool(name, args)
    parts = []
    for c in getattr(result, "content", None) or []:
        text = getattr(c, "text", None)
        parts.append(text if text else str(c))
    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    if structured is not None:
        parts.append(json.dumps(structured))
    return "\n".join(parts) if parts else str(result)


async def main_async():
    global _proxy_client
    args = parse_args(sys.argv[1:])
    init_logger(args.log)
    logging_note = "enabling visible notebook tools plus session proxy"
    import logging
    logging.info(logging_note)
    session_mcp = ColabSessionProxy()
    await session_mcp.start_proxy_server()
    _proxy_client = session_mcp.middleware[0].proxy_client
    mcp.mount(session_mcp.proxy_server)
    for middleware in session_mcp.middleware:
        mcp.add_middleware(middleware)
    try:
        await mcp.run_async()
    finally:
        await session_mcp.cleanup()


if __name__ == "__main__":
    asyncio.run(main_async())
