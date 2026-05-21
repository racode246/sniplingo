"""Port: capture a screen region into an image."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from sniplingo.domain.models import Region

if TYPE_CHECKING:
    from PIL.Image import Image


class ScreenCapturer(Protocol):
    def capture(self, region: Region) -> Image:
        """Grab `region` (virtual-desktop coords) and return it as a PIL image."""
        ...
