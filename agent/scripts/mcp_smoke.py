"""Talk to the server over real MCP stdio, like Claude does.

    uv run scripts/mcp_smoke.py            against the fake phone (works anywhere)
    uv run scripts/mcp_smoke.py --dry-run  against the real phone, without touching it
    uv run scripts/mcp_smoke.py --fake --input cua   any server options can be passed
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    flags = sys.argv[1:] or ["--fake"]
    params = StdioServerParameters(command=sys.executable, args=["-m", "boootie.server", *flags],
                                    env=dict(os.environ))
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        init = await s.initialize()
        print("server:", init.server_info.name, "| instructions:", len(init.instructions or ""), "chars")
        tools = (await s.list_tools()).tools
        print("tools:", ", ".join(t.name for t in tools))
        for name, args in [("screenshot", {}), ("tap", {"x": 230, "y": 500}),
                           ("swipe", {"x1": 400, "y1": 500, "x2": 60, "y2": 500}),
                           ("type_text", {"text": "café"}), ("spotlight", {"query": "Settings"}),
                           ("tap", {"x": 5000, "y": 1})]:
            res = await s.call_tool(name, args)
            kinds = [c.type for c in res.content]
            text = next((c.text for c in res.content if c.type == "text"), "")
            print(f"{name:11} error={res.is_error!s:5} {kinds} {text[:90]}")


asyncio.run(main())
