"""Colab MCP entry that works with clients that (a) never re-list tools and (b) time out long tool calls.

Stock ``colab-mcp`` has two problems with clients such as cursor-agent:

1. It publishes ``add_code_cell`` and the other notebook tools only after the browser attaches, via
   ``notifications/tools/list_changed``. Clients that list tools once never see them.
   Fix: ``colab_list_tools`` and ``colab_call`` are registered up front and forward to the notebook.
2. ``open_colab_browser_connection`` blocks for 60 s waiting for the user to click Connect. Clients with a
   shorter request timeout cancel the call and often restart the server, which kills the websocket.
   Fix: the wait is cut to COLAB_UI_WAIT seconds (default 15), and ``colab_status`` /
   ``colab_wait_connected`` let the agent poll in short calls.

The stock ``ColabProxyClient.await_proxy_connection`` does
``asyncio.wait_for(gather(connection_live.wait(), self._start_task))``. On timeout or client
cancel, that gather is cancelled and ``_start_task`` with it. ``_start_task`` is what builds the
MCP session over the websocket. After it is cancelled, every browser connection is accepted and
dropped in the same second (``BrokenResourceError`` in ``_read_from_socket``). The replacement
below only polls and never cancels ``_start_task``, so a Connect click after ``open`` has
returned still attaches.

Usage for agents: call ``open_colab_browser_connection`` ONCE, have the user (or CUA) click Connect on
"Connect to a local Colab MCP server" in the browser, then poll ``colab_wait_connected`` until it says
connected. Do not call ``open_colab_browser_connection`` again while waiting: each call opens a new tab.
Set BROWSER (e.g. "open -a Helium %s") to choose the browser.
"""
import asyncio
import json
import logging
import os
import sys

import colab_mcp.session as _session
from colab_mcp import init_logger, mcp, parse_args
from colab_mcp.session import ColabSessionProxy

_session.UI_CONNECTION_TIMEOUT = float(os.environ.get("COLAB_UI_WAIT", "15"))
_proxy_client = None


async def _await_proxy_connection_polling(self):
    """Replacement for ColabProxyClient.await_proxy_connection.

    The stock version does wait_for(gather(connection_live.wait(), self._start_task)). On timeout (or when
    the client cancels the tool call) that cancels the gather and with it ``_start_task``, the task that
    builds the MCP session over the websocket. After that every browser connection is accepted and dropped
    at once. Polling never cancels ``_start_task``, so a late Connect click still works.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + _session.UI_CONNECTION_TIMEOUT
    while loop.time() < deadline:
        if self.is_connected():
            return
        await asyncio.sleep(0.25)


_session.ColabProxyClient.await_proxy_connection = _await_proxy_connection_polling


def _connected() -> bool:
    return _proxy_client is not None and _proxy_client.is_connected()


@mcp.tool()
async def colab_status() -> str:
    """Return JSON with whether the Colab notebook is connected. Cheap; safe to poll."""
    if _proxy_client is None:
        return json.dumps({"connected": False, "state": "server starting"})
    return json.dumps({
        "connected": _connected(),
        "websocket_live": _proxy_client.wss.connection_live.is_set(),
        "port": _proxy_client.wss.port,
        "hint": "" if _connected() else "call open_colab_browser_connection once, then click Connect in the browser",
    })


@mcp.tool()
async def colab_wait_connected(seconds: int = 20) -> str:
    """Wait up to `seconds` (1-25) for the Colab page to connect. Returns 'connected' or 'not connected yet'."""
    secs = max(1, min(int(seconds), 25))
    for _ in range(secs * 4):
        if _connected():
            return "connected"
        await asyncio.sleep(0.25)
    return "not connected yet"


@mcp.tool()
async def colab_list_tools() -> str:
    """List tools the connected Colab page is serving, with input schemas."""
    if not _connected():
        return "not connected. Call open_colab_browser_connection once, click Connect in the browser, then colab_wait_connected."
    tools = await _proxy_client.proxy_mcp_client.list_tools()
    if not tools:
        return "connected, but the notebook has not published tools yet. Click Connect in the browser."
    out = []
    for t in tools:
        schema = getattr(t, "inputSchema", None)
        if schema is None:
            schema = getattr(t, "input_schema", None)
        out.append({"name": t.name, "description": getattr(t, "description", "") or "", "inputSchema": schema})
    return json.dumps(out)


@mcp.tool()
async def colab_call(name: str, arguments_json: str = "{}") -> str:
    """Call a connected-notebook tool (e.g. add_code_cell, run_code_cell, get_cells). `arguments_json` is a JSON object."""
    if not _connected():
        return "not connected. Call open_colab_browser_connection once, click Connect in the browser, then colab_wait_connected."
    args = json.loads(arguments_json or "{}")
    if not isinstance(args, dict):
        return "arguments_json must be a JSON object"
    try:
        result = await _proxy_client.proxy_mcp_client.call_tool(name, args)
    except Exception as e:  # surface notebook-side errors as text instead of failing the MCP call
        return f"error from notebook tool {name}: {e}"
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
    logging.info("visible notebook tools + short UI wait (%ss)", _session.UI_CONNECTION_TIMEOUT)
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
