import pytest

from boootie.geometry import (
    PHONE_ASPECT,
    Rect,
    content_rect,
    crop_box,
    image_size,
    make_frame,
    to_image,
    to_screen,
)

# Measured from a real iPhone Mirroring window (macOS 15): 318 x 701 pt, phone screen
# 302 x 655 pt, 8 pt border left/right/bottom, 38 pt on top.
WINDOW = Rect(x=1038, y=96, w=318, h=701)


def test_content_rect_matches_measured_window():
    c = content_rect(WINDOW)
    assert (c.x, c.w) == (1046, 302)
    assert c.y == pytest.approx(96 + 38, abs=0.6)
    assert c.h == pytest.approx(655, abs=0.6)
    assert c.y + c.h == pytest.approx(96 + 701 - 8)  # sits on the bottom border


def test_content_rect_without_margin_or_title_bar():
    win = Rect(0, 0, 330, 330 * PHONE_ASPECT)
    assert content_rect(win, margin=0) == win


def test_content_rect_override():
    c = content_rect(WINDOW, top_inset=40)
    assert c.y == 136 and c.h == pytest.approx(701 - 40 - 8)


def test_image_size_is_fixed_width_with_phone_aspect():
    w, h = image_size(content_rect(WINDOW), 460)
    assert w == 460
    assert h == round(460 * PHONE_ASPECT)


def test_image_size_does_not_depend_on_window_scale():
    # iPhone Mirroring can be zoomed (Cmd +/-). Same aspect -> same screenshot size.
    small = content_rect(Rect(0, 0, 300, 284 * PHONE_ASPECT + 38))
    big = content_rect(Rect(0, 0, 400, 384 * PHONE_ASPECT + 38))
    assert image_size(small, 460) == image_size(big, 460)


def test_corners_and_centre_map_onto_content():
    c = content_rect(WINDOW)
    f = make_frame(c, 460)
    assert to_screen(f, 0, 0) == pytest.approx((c.x, c.y))
    assert to_screen(f, f.img_w, f.img_h) == pytest.approx((c.x + c.w, c.y + c.h))
    assert to_screen(f, f.img_w / 2, f.img_h / 2) == pytest.approx(c.center)


def test_round_trip():
    f = make_frame(content_rect(WINDOW), 460)
    for x, y in [(0, 0), (12.5, 900), (230, 498), (459, 996)]:
        assert to_image(f, *to_screen(f, x, y)) == pytest.approx((x, y))


def test_window_on_secondary_display_with_negative_origin():
    win = Rect(-1500, -300, 318, 701)
    f = make_frame(content_rect(win), 460)
    assert to_screen(f, 0, 0) == pytest.approx((-1492, -262), abs=0.6)


def test_out_of_bounds_is_rejected():
    f = make_frame(content_rect(WINDOW), 460)
    with pytest.raises(ValueError):
        to_screen(f, -1, 10)
    with pytest.raises(ValueError):
        to_screen(f, 10, f.img_h + 1)


@pytest.mark.parametrize("scale", [1, 2, 3])
def test_crop_box_handles_retina(scale):
    c = content_rect(WINDOW)
    cap_w, cap_h = round(WINDOW.w * scale), round(WINDOW.h * scale)
    left, top, right, bottom = crop_box(WINDOW, c, cap_w, cap_h)
    assert (left, right) == (8 * scale, cap_w - 8 * scale)
    assert top == pytest.approx(38 * scale, abs=scale)
    assert bottom == cap_h - 8 * scale
