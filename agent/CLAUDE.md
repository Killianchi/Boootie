# boootie agent

This folder is an MCP server (`boootie`) that lets you see and control the user's
iPhone through macOS iPhone Mirroring. When the user asks you to do something on
their phone, use the `boootie` tools and follow this guide. The same guide is
sent to every client as the server's instructions, so Claude Desktop gets it too.

@boootie/guide.md

## Extra rules when working in this repo
- Before a phone task, call `screenshot` once to confirm the mirroring window is
  connected and the phone is unlocked into iOS (not the "iPhone in use" screen).
- After a task from `tasks.md`, tell the user the number of actions you used
  and anything that went wrong, so they can record it.
- Debug a failed run by reading `runs/<latest>/log.jsonl` and the annotated
  frames (`NNN_tool.png` shows where you aimed).

## Code map
- `boootie/geometry.py` screenshot pixels <-> screen points (the one mapping; tested)
- `boootie/mac.py` window lookup, capture, CGEvent mouse/keyboard, permissions
- `boootie/phone.py` actions + settle-wait + dry-run + logging (used by server and scripts)
- `boootie/inputs.py` how input is delivered: `SystemInput` (real pointer) or `CuaInput` (Cua Driver, background)
- `boootie/cursor.py` the AI's iOS-style pointer overlay (helper process, AppKit)
- `boootie/server.py` MCP tools; `boootie/killswitch.py`; `boootie/runlog.py`
- `boootie/fake.py` pretend phone; `uv run pytest` and `uv run scripts/mcp_smoke.py` run anywhere
