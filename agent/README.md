# boootie agent: Claude operates your iPhone

A local MCP server. Claude (Claude Code or Claude Desktop, on your subscription, no
API key) is the brain. This server is the eyes and hands: it screenshots the
**iPhone Mirroring** window and sends synthetic mouse and keyboard events into it.

```
Claude ⇄ MCP (stdio) ⇄ boootie-mcp ⇄ iPhone Mirroring window ⇄ your iPhone
```

## Requirements
- Mac with macOS 15+, iPhone with iOS 18+, iPhone Mirroring set up and connected
  (same Apple ID, Wi-Fi + Bluetooth on, phone **locked** and nearby).
- [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`

```bash
cd agent
uv sync
```

## Milestone 1: permissions + capture
```bash
uv run boootie-check
```
It checks three permissions for **your terminal app** and opens System Settings for any that are missing:

| Permission | Why |
|---|---|
| Screen Recording | screenshots of the mirroring window |
| Accessibility | synthetic clicks and key presses |
| Input Monitoring | kill-switch hotkey only (optional) |

Turn your terminal on in each list, then **quit and reopen the terminal** (Cmd+Q).
Then it prints the window bounds and saves `window_full.png` (red box = phone area)
and `screenshot.png` to `runs/<timestamp>_check/`. The red box must hug the phone
screen. `screenshot.png` should show the phone edge to edge, no black border.

## Milestone 2: input from a test script
```bash
uv run scripts/m2_input.py corners      # cursor visits the 4 corners: checks the mapping
uv run scripts/m2_input.py home         # Cmd+1
uv run scripts/m2_input.py center       # tap centre
uv run scripts/m2_input.py swipe        # page left/right on the home screen
uv run scripts/m2_input.py scroll       # wheel down/up (open Settings first)
uv run scripts/m2_input.py spotlight Settings
uv run scripts/m2_input.py spotlight "café über"   # non-ASCII goes via the clipboard
uv run scripts/m2_input.py switcher     # Cmd+2
```
Each step writes annotated frames to `runs/`. Add `--dry-run` to only draw targets.

## Milestone 3: Claude Code
```bash
cd agent
claude mcp add boootie -- uv run --directory "$PWD" boootie-mcp
claude            # then: "open Settings on my phone"
```
Run `claude` from `agent/` so it also loads `CLAUDE.md`. Dry-run variant:
`claude mcp add boootie-dry -- uv run --directory "$PWD" boootie-mcp --dry-run`.

## Milestone 4: Claude Desktop
Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Settings → Developer → Edit Config).
Use absolute paths, since the desktop app doesn't see your shell's PATH (`which uv`, `pwd`):

```json
{
  "mcpServers": {
    "boootie": {
      "command": "/Users/YOU/.local/bin/uv",
      "args": ["run", "--directory", "/Users/YOU/path/to/Boootie/agent", "boootie-mcp"]
    }
  }
}
```
Restart Claude Desktop. Give **Claude.app** Screen Recording and Accessibility too:
it is the app that launches the server there, so your terminal's permissions don't apply.

## Tools
`screenshot`, `tap(x,y)`, `long_press(x,y)`, `swipe(x1,y1,x2,y2)`, `scroll(direction, amount)`,
`type_text(text)`, `press_key(enter|backspace|escape|…)`, `home()` (Cmd+1),
`app_switcher()` (Cmd+2), `spotlight(query)` (Cmd+3).

Coordinates are pixels in the screenshot (fixed 460 px wide, about 997 px high).
Every action waits until the screen stops changing (checks every 200 ms, gives up at 3 s)
and returns a fresh screenshot.

## Safety
- **Kill switch:** `Ctrl+Option+Cmd+K` blocks all actions; `Ctrl+Option+Cmd+R` resumes.
  Or `uv run boootie-kill on|off|status`. The state is a file (`~/.boootie/KILLED`), so it
  survives restarts and covers every server and script. Screenshots still work.
  The hotkey needs Input Monitoring; the command always works.
- **Dry run:** `boootie-mcp --dry-run` logs and draws every target, never moves the mouse.
- The tool descriptions and server instructions tell Claude to ask you before sending,
  posting, paying, deleting or calling.
- While Claude acts it really moves your Mac's cursor and types. Don't use the Mac at the
  same time, and keep the mirroring window visible.

## Debugging
Each server start creates `runs/<timestamp>/` with `log.jsonl` (args, screen points,
window bounds, timings, errors) plus `NNN_tool.png` (target drawn: red dot = tap,
blue = long press, arrow = swipe/scroll) and `NNN_tool_after.jpg`.
`uv run boootie-runs` summarises recent runs.

Without a Mac: `uv run pytest` and `uv run scripts/mcp_smoke.py` use a fake phone (`--fake`).

## Settings (env vars)
| Var | Default | Use |
|---|---|---|
| `BOOOTIE_MARGIN` | 8 | black border (points) around the phone screen inside the window |
| `BOOOTIE_TOP_INSET` | auto | top edge of the phone screen (points from the window top) if the auto crop is wrong |
| `BOOOTIE_ASPECT` | 2556/1179 | phone height/width (e.g. 1.778 for an iPhone SE) |
| `BOOOTIE_SCROLL_INVERT` | off | set to 1 if `scroll("down")` goes up |

## Known limits
- iPhone Mirroring only works while the phone is **locked**. Unlocking it pauses
  mirroring. It also disconnects after a while idle; reconnect in the app.
- Face ID, passcode and Apple Pay prompts can't be completed through mirroring.
- Key typing assumes a US layout. If letters come out wrong, use `type_text(..., method="paste")`.
  Non-ASCII text always goes through Universal Clipboard (needs Handoff on), which
  overwrites your Mac clipboard and can lag.
- The phone area is found from measured window layout: an 8 pt border on the sides and
  bottom, the phone's aspect ratio, and the rest on top as title bar. Measured on macOS 15
  at the default zoom. Check it with `boootie-check` if you zoom the window or update macOS.
- `CGWindowListCreateImage` is deprecated by Apple. If it stops working, capture falls back
  to the slower `screencapture` command.
- The kill switch blocks the *next* action. One already in progress (at most a few hundred ms
  of input) finishes.
- Animated screens (videos, maps) never "settle", so those actions take the full 3 s.
- macOS asks every so often to re-confirm Screen Recording. Click Allow.
