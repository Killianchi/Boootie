"""End-to-end tests against the fake backend (no Mac needed)."""

import json

import pytest

from boootie import fake, killswitch
from boootie.phone import Phone


@pytest.fixture
def phone(tmp_path, monkeypatch):
    monkeypatch.setattr("boootie.runlog.DEFAULT_ROOT", tmp_path)
    monkeypatch.setattr(killswitch, "STATE", tmp_path / "KILLED")
    fake.events.clear()
    return Phone(fake=True)


def log(phone):
    return [json.loads(l) for l in (phone.log.dir / "log.jsonl").read_text().splitlines()]


def test_screenshot_crops_title_bar_and_has_fixed_size(phone):
    img = phone.screenshot()
    assert img.size == (460, 997)
    # no red title bar and no black border may survive the crop
    for x, y in [(230, 1), (1, 500), (458, 500), (230, 995)]:
        r, g, b = img.getpixel((x, y))
        assert not (r > 150 and g < 100), (x, y)
        assert r + g + b > 60, (x, y)


def test_tap_maps_to_screen_points(phone):
    phone.tap(0, 0)
    phone.tap(460, 997)
    downs = [e for e in fake.events if e[0] == "down"]
    assert downs[0][1:] == pytest.approx((1046, 134), abs=0.6)  # window + 8 pt border, + 38 pt top
    assert downs[1][1:] == pytest.approx((1348, 96 + 701 - 8), abs=0.6)


def test_action_is_logged_with_annotated_frame(phone):
    phone.swipe(400, 500, 50, 500)
    (entry,) = log(phone)
    assert entry["tool"] == "swipe" and "error" not in entry
    assert (phone.log.dir / entry["frame"]).exists()
    assert (phone.log.dir / entry["after"]).exists()
    assert entry["marks"][0]["kind"] == "arrow"


def test_type_text_splits_ascii_and_non_ascii(phone):
    phone.type_text("café über")
    typed = [e for e in fake.events if e[0] in ("type", "paste")]
    assert typed == [("type", "caf"), ("paste", "é"), ("type", " "), ("paste", "ü"), ("type", "ber")]


def test_dry_run_never_sends_input(phone):
    phone.dry_run = True
    phone.tap(100, 100)
    phone.home()
    assert fake.events == []
    assert len(log(phone)) == 2


def test_kill_switch_blocks_actions(phone):
    killswitch.set_killed(True)
    with pytest.raises(killswitch.Killed):
        phone.tap(10, 10)
    assert fake.events == []
    assert "KILL SWITCH" in log(phone)[0]["error"]
    phone.screenshot()  # looking is still allowed
    killswitch.set_killed(False)
    phone.tap(10, 10)
    assert fake.events


def test_out_of_bounds_tap_is_rejected_before_input(phone):
    with pytest.raises(ValueError):
        phone.tap(9999, 10)
    assert fake.events == []
