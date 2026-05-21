"""Pure geometry helpers for turning drag gestures into clamped capture regions."""

from __future__ import annotations

from sniplingo.domain.models import Region

Point = tuple[int, int]


def region_from_points(p1: Point, p2: Point) -> Region:
    """Build a `Region` from two drag endpoints, regardless of drag direction.

    Width/height are always non-negative; a zero-distance drag yields an empty region.
    """
    x1, y1 = p1
    x2, y2 = p2
    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    return Region(left=left, top=top, width=width, height=height)


def clamp_to_bounds(region: Region, bounds: Region) -> Region:
    """Intersect `region` with `bounds`. Returns an empty region when they don't overlap."""
    left = max(region.left, bounds.left)
    top = max(region.top, bounds.top)
    right = min(region.right, bounds.right)
    bottom = min(region.bottom, bounds.bottom)
    width = max(0, right - left)
    height = max(0, bottom - top)
    return Region(left=left, top=top, width=width, height=height)
