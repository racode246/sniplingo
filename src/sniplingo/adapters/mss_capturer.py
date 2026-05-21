"""Screen-capture adapter backed by `mss`.

`mss` is imported lazily and one instance is reused (it is not thread-safe across
threads, so the owning worker thread should create/use it). `region_to_monitor` is a
pure helper kept separate for unit testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sniplingo.domain.errors import CaptureError
from sniplingo.domain.models import Region

if TYPE_CHECKING:
    from PIL.Image import Image


def region_to_monitor(region: Region) -> dict[str, int]:
    """Map a `Region` to the dict shape `mss.grab` expects (virtual-desktop coords)."""
    return {
        "left": region.left,
        "top": region.top,
        "width": region.width,
        "height": region.height,
    }


class MssCapturer:
    def __init__(self) -> None:
        self._sct = None

    def capture(self, region: Region) -> Image:
        if region.is_empty:
            raise CaptureError("cannot capture an empty region")
        from PIL import Image

        sct = self._get_sct()
        try:
            shot = sct.grab(region_to_monitor(region))
        except Exception as exc:  # noqa: BLE001 - convert any mss failure at the boundary
            raise CaptureError(f"screen capture failed: {exc}") from exc
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def _get_sct(self):
        if self._sct is None:
            import mss

            self._sct = mss.MSS()
        return self._sct

    def close(self) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None
