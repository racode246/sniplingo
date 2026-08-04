import pytest

from sniplingo.domain.geometry import clamp_to_bounds, pad_region, region_from_points
from sniplingo.domain.models import Region


@pytest.mark.parametrize(
    "p1,p2,expected",
    [
        ((10, 20), (40, 60), Region(10, 20, 30, 40)),  # natural direction
        ((40, 60), (10, 20), Region(10, 20, 30, 40)),  # reversed both axes
        ((40, 20), (10, 60), Region(10, 20, 30, 40)),  # reversed x only
        ((10, 60), (40, 20), Region(10, 20, 30, 40)),  # reversed y only
        ((-30, -10), (-10, 10), Region(-30, -10, 20, 20)),  # negative coords
    ],
)
def test_region_from_points_normalizes(p1, p2, expected):
    assert region_from_points(p1, p2) == expected


def test_region_from_points_zero_area_is_empty():
    r = region_from_points((5, 5), (5, 5))
    assert r == Region(5, 5, 0, 0)
    assert r.is_empty


def test_clamp_within_bounds_unchanged():
    bounds = Region(0, 0, 1920, 1080)
    r = Region(100, 100, 200, 200)
    assert clamp_to_bounds(r, bounds) == r


def test_clamp_partial_overlap_is_trimmed():
    bounds = Region(0, 0, 100, 100)
    r = Region(50, 50, 100, 100)  # spills past right/bottom edges
    assert clamp_to_bounds(r, bounds) == Region(50, 50, 50, 50)


def test_clamp_handles_negative_monitor():
    bounds = Region(-1920, 0, 1920, 1080)  # a monitor to the left of primary
    r = Region(-2000, -50, 200, 200)
    assert clamp_to_bounds(r, bounds) == Region(-1920, 0, 120, 150)


def test_clamp_no_overlap_is_empty():
    bounds = Region(0, 0, 100, 100)
    r = Region(200, 200, 50, 50)
    assert clamp_to_bounds(r, bounds).is_empty


def test_pad_region_grows_symmetrically_on_all_sides():
    # +8 on each side: left/top move out by 8, width/height grow by 16.
    assert pad_region(Region(100, 50, 30, 40), 8) == Region(92, 42, 46, 56)


def test_pad_region_zero_padding_is_unchanged():
    r = Region(10, 20, 30, 40)
    assert pad_region(r, 0) == r


def test_pad_region_may_go_negative_for_edge_selections():
    # A selection flush against the top-left of the desktop pads into negative coords;
    # off-screen pixels come back as a black quiet zone, which OCR is happy with.
    assert pad_region(Region(0, 0, 100, 50), 8) == Region(-8, -8, 116, 66)


def test_pad_region_negative_padding_is_a_no_op():
    r = Region(10, 20, 30, 40)
    assert pad_region(r, -5) == r
