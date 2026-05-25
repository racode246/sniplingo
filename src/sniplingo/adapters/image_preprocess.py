"""Image preprocessing to make game text easier for Windows OCR.

Windows.Media.Ocr struggles with two things this module addresses:

* **small / low-contrast colored text** (e.g. red status text on a dark HUD) — fixed by
  flattening to high-contrast grayscale and upscaling;
* **text with no surrounding margin** — a selection dragged flush to the glyphs leaves no
  "quiet zone", and the engine drops the edge characters (or the whole line). We add a
  synthetic background-colored border so the read no longer depends on how tightly the
  user selected, nor on capturing extra (possibly noisy) screen pixels.

Pillow lives in the adapters layer only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageOps

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

# Windows OCR rejects images larger than this on a side (CLAUDE.md: max_image_dimension).
MAX_OCR_DIMENSION = 10000
# Quiet zone added around the text. Empirically ~16px is the threshold at which a flush
# crop of small HUD text becomes readable again; we add it on every side.
DEFAULT_OCR_MARGIN = 16


def preprocess_for_ocr(
    image: PILImage, scale: int = 2, margin: int = DEFAULT_OCR_MARGIN
) -> PILImage:
    """Return an OCR-friendly copy of `image`: grayscale, contrast-stretched, margined, upscaled.

    `scale` < 1 is treated as 1 (no upscale) and `margin` < 0 as 0. The border is filled
    with the detected background level so it reads as a quiet zone, not a frame around the
    text. The result is clamped so neither side exceeds :data:`MAX_OCR_DIMENSION`.
    """
    scale = max(1, int(scale))
    margin = max(0, int(margin))

    gray = ImageOps.autocontrast(image.convert("L"))
    if margin:
        gray = ImageOps.expand(gray, border=margin, fill=_background_level(gray))

    target_w = gray.width * scale
    target_h = gray.height * scale
    longest = max(target_w, target_h)
    if longest > MAX_OCR_DIMENSION:
        factor = MAX_OCR_DIMENSION / longest
        target_w = max(1, int(target_w * factor))
        target_h = max(1, int(target_h * factor))

    if (target_w, target_h) != gray.size:
        gray = gray.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return gray


def _background_level(gray: PILImage) -> int:
    """Median of the perimeter pixels of an "L" image — a robust background estimate.

    Using the median (not a corner) tolerates a glyph that happens to touch one edge.
    """
    w, h = gray.size
    px = gray.load()
    edge: list[int] = []
    for x in range(w):
        edge.append(px[x, 0])
        edge.append(px[x, h - 1])
    for y in range(h):
        edge.append(px[0, y])
        edge.append(px[w - 1, y])
    edge.sort()
    return edge[len(edge) // 2]
