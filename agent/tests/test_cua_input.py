"""CuaInput against a fake cua-driver: the calls and coordinates boootie sends."""

import json
from pathlib import Path

import pytest

from boootie import fake, killswitch
from boootie.phone import Phone

FAKE_BIN = Path(__file__).parent / "fakes" / "cua-driver"


@pytest.fixture
def phone(tmp_path, monkeypatch):
    monkeypatch.setattr("boootie.runlog.DEFAULT_ROOT", tmp_path)
    monkeypatch.setattr(killswitch, "STATE", tmp_path / "KILLED")
    monkeypatch.setenv("BOOOTIE_CUA_BIN", str(FAKE_BIN))
    monkeypatch.setenv("FAKE_CUA_LOG", str(tmp_path / "cua.jsonl"))
    fake.events.clear()
    p = Phone(fake=True, input_mode="cua")
    p.cua_log = tmp_path / "cua.jsonl"
    return p


def calls(phone, tool=None):
    rows = [json.loads(l) for l in phone.cua_log.read_text().splitlines()]
    return [r for r in rows if tool is None or r["tool"] == tool]


def test_session_starts_on_first_action_and_cua_cursor_is_hidden(phone):
    assert not phone.cua_log.exists()  # nothing at startup: a missing driver can't crash the server
    phone.tap(10, 10)
    assert [c["tool"] for c in calls(phone)][:2] == ["start_session", "set_agent_cursor_enabled"]
    assert calls(phone, "set_agent_cursor_enabled")[0]["args"]["enabled"] is False


def test_tap_sends_window_pixels_and_never_moves_the_pointer(phone):
    phone.tap(0, 0)
    phone.tap(460, 997)
    (snap,) = calls(phone, "get_window_state")  # one snapshot, then cached
    assert snap["args"]["max_image_dimension"] == 0
    c1, c2 = (c["args"] for c in calls(phone, "click"))
    # window 318x701 pt at x=1038,y=96, phone screen starts 8 pt in and ~38 pt down; 2 px per pt
    assert (c1["x"], c1["y"]) == pytest.approx((16, 76.6), abs=1.2)
    assert (c2["x"], c2["y"]) == pytest.approx((636 - 16, 1402 - 16), abs=1.2)
    assert c1["pid"] == 1 and c1["window_id"] == 1 and c1["session"] == "boootie"
    assert not [e for e in fake.events if e[0] in ("move", "down", "up")]  # real pointer untouched


def test_swipe_and_long_press_are_drags(phone):
    phone.swipe(400, 500, 60, 500, duration_ms=300)
    phone.long_press(100, 100, seconds=1.2)
    swipe, hold = (c["args"] for c in calls(phone, "drag"))
    assert swipe["from_x"] > swipe["to_x"] and swipe["duration_ms"] == 300
    assert (hold["from_x"], hold["from_y"]) == (hold["to_x"], hold["to_y"])
    assert hold["duration_ms"] == 1200


def test_keys_shortcuts_and_scroll(phone):
    phone.home()
    phone.press_key("enter")
    phone.press_key("backspace")
    phone.scroll("down", 2)
    assert calls(phone, "hotkey")[0]["args"]["keys"] == ["cmd", "1"]
    assert [c["args"]["key"] for c in calls(phone, "press_key")] == ["return", "delete"]
    sc = calls(phone, "scroll")[0]["args"]
    assert sc["direction"] == "down" and sc["amount"] == 2


def test_non_ascii_goes_through_the_clipboard(phone):
    phone.spotlight("café")
    assert [c["args"]["text"] for c in calls(phone, "type_text")] == ["caf"]
    assert ("clipboard", "é") in fake.events
    assert [c["args"]["keys"] for c in calls(phone, "hotkey")] == [["cmd", "3"], ["cmd", "v"]]


def test_failure_is_reported_with_cua_output(phone, monkeypatch):
    monkeypatch.setenv("FAKE_CUA_FAIL", "click")
    with pytest.raises(RuntimeError, match="simulated failure"):
        phone.tap(10, 10)
    entry = json.loads((phone.log.dir / "log.jsonl").read_text().splitlines()[-1])
    assert "cua_calls" in entry and "simulated failure" in entry["error"]


def test_uses_one_persistent_mcp_connection(phone):
    phone.tap(10, 10)
    phone.home()
    assert {c["via"] for c in calls(phone)} == {"mcp"}
    entry = json.loads((phone.log.dir / "log.jsonl").read_text().splitlines()[-1])
    t = entry["timing"]
    assert {"grab_ms", "input_ms", "settle_ms"} <= set(t)
    assert [c["tool"] for c in t["cua_calls"]] == ["hotkey"]


def test_falls_back_to_one_process_per_call(tmp_path, monkeypatch):
    monkeypatch.setattr("boootie.runlog.DEFAULT_ROOT", tmp_path)
    monkeypatch.setattr(killswitch, "STATE", tmp_path / "KILLED")
    monkeypatch.setenv("BOOOTIE_CUA_BIN", str(FAKE_BIN))
    monkeypatch.setenv("FAKE_CUA_LOG", str(tmp_path / "cua.jsonl"))
    monkeypatch.setenv("FAKE_CUA_NO_MCP", "1")
    p = Phone(fake=True, input_mode="cua")
    p.cua_log = tmp_path / "cua.jsonl"
    p.tap(10, 10)
    assert {c["via"] for c in calls(p)} == {"call"}
    assert calls(p, "click")


def test_cua_glide_is_made_instant(phone):
    phone.tap(10, 10)
    (m,) = calls(phone, "set_agent_cursor_motion")
    assert m["args"]["glide_duration_ms"] == 1 and m["args"]["dwell_after_click_ms"] == 0


def test_skips_cua_post_action_wait_and_typing_is_fast(phone):
    phone.tap(10, 10)
    phone.type_text("hi")
    assert calls(phone, "click")[0]["args"]["post_action_wait"] == "none"
    assert calls(phone, "type_text")[0]["args"]["delay_ms"] == 8


def test_drops_post_action_wait_if_this_cua_rejects_it(phone, monkeypatch):
    monkeypatch.setenv("FAKE_CUA_NO_WAIT_ARG", "1")
    phone.tap(10, 10)
    phone.tap(20, 20)
    clicks = [c["args"] for c in calls(phone, "click")]
    # first click: tried with the argument, rejected, retried without; second: straight without
    assert ["post_action_wait" in c for c in clicks] == [True, False, False]
