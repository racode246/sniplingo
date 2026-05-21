"""OCR adapter backed by the Windows built-in engine (Windows.Media.Ocr) via PyWinRT.

Windows / winrt imports are lazy (inside methods) so the pure result-mapping helper
``_to_ocr_result`` stays unit-testable without winrt. ``asyncio.run`` and the engine
must be called from a worker thread (no running event loop) — see CLAUDE.md.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from sniplingo.domain.errors import OcrError, OcrLanguageUnavailableError
from sniplingo.domain.models import OcrLine, OcrResult, OcrWord

if TYPE_CHECKING:
    from PIL.Image import Image


class WinRtOcrEngine:
    def is_language_available(self, lang: str) -> bool:
        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine

        return OcrEngine.is_language_supported(Language(lang))

    def recognize(self, image: Image, lang: str) -> OcrResult:
        engine = self._create_engine(lang)
        bitmap = _pil_to_software_bitmap(image)

        async def _run():
            return await engine.recognize_async(bitmap)

        try:
            result = asyncio.run(_run())
        except Exception as exc:  # noqa: BLE001 - convert any winrt failure at the boundary
            raise OcrError(f"OCR recognition failed: {exc}") from exc
        return _to_ocr_result(result)

    def _create_engine(self, lang: str):
        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine

        language = Language(lang)
        if not OcrEngine.is_language_supported(language):
            raise OcrLanguageUnavailableError(
                f"OCR language pack for {lang!r} is not installed. In an admin PowerShell run: "
                f'Add-WindowsCapability -Online -Name "Language.OCR~~~{lang}-US~0.0.1.0"'
            )
        engine = OcrEngine.try_create_from_language(language)
        if engine is None:
            raise OcrLanguageUnavailableError(f"could not create an OCR engine for {lang!r}")
        return engine


def _pil_to_software_bitmap(image: Image):
    import winrt.windows.storage.streams as streams
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap

    rgba = image.convert("RGBA")
    writer = streams.DataWriter()
    writer.write_bytes(rgba.tobytes())
    return SoftwareBitmap.create_copy_from_buffer(
        writer.detach_buffer(), BitmapPixelFormat.RGBA8, rgba.width, rgba.height
    )


def _to_ocr_result(result) -> OcrResult:
    """Map a winrt OcrResult (duck-typed) into our domain OcrResult."""
    lines = []
    for line in result.lines:
        words = tuple(
            OcrWord(
                text=word.text,
                left=int(word.bounding_rect.x),
                top=int(word.bounding_rect.y),
                width=int(word.bounding_rect.width),
                height=int(word.bounding_rect.height),
            )
            for word in line.words
        )
        lines.append(OcrLine(text=line.text, words=words))
    return OcrResult(lines=tuple(lines))
