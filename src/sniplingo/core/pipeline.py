"""Orchestrates one translation: capture -> (image LLM) | (OCR -> translate).

Depends only on `ports` and `domain`. Concrete capturer / OCR / translator are
injected, so this is fully unit-testable with hand-written fakes.

Two paths:
- **Vision**: when an :class:`ImageTranslator` is provided (e.g. Gemini), the
  captured image is sent directly for combined OCR + translation, skipping
  Windows OCR and any text post-processing. This is the fast / high-quality path.
- **Text**: otherwise (or if Vision fails and a text translator exists), Windows
  OCR extracts text, the cleaned lines are joined with ``\\n`` and sent to the
  :class:`Translator` chain in a single round-trip. ``translator`` may be ``None``
  for a Vision-only setup.

Expected failures never raise: capture / OCR errors become a FAILED result and a
failed Vision attempt is recorded in :attr:`TranslationResult.attempts`.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from sniplingo.domain.errors import CaptureError, OcrError, TranslationError
from sniplingo.domain.geometry import pad_region
from sniplingo.domain.models import BackendAttempt, Region, TranslationResult
from sniplingo.domain.text_postprocess import clean_ocr_lines
from sniplingo.ports.capture import ScreenCapturer
from sniplingo.ports.image_translate import ImageTranslator
from sniplingo.ports.ocr import OcrEngine
from sniplingo.ports.translate import Translator

logger = logging.getLogger(__name__)

# A small quiet zone around the selection. Windows OCR drops glyphs that touch the
# image edge, so a selection dragged flush to the text loses its first/last characters.
DEFAULT_CAPTURE_PADDING = 8


class TranslationPipeline:
    def __init__(
        self,
        capturer: ScreenCapturer,
        ocr: OcrEngine,
        translator: Translator | None,
        source: str = "en",
        target: str = "ja",
        image_translator: ImageTranslator | None = None,
        capture_padding: int = DEFAULT_CAPTURE_PADDING,
    ) -> None:
        if translator is None and image_translator is None:
            raise ValueError("TranslationPipeline needs a text or an image translator")
        self._capturer = capturer
        self._ocr = ocr
        self._translator = translator
        self._source = source
        self._target = target
        self._image_translator = image_translator
        self._capture_padding = capture_padding

    def run(self, region: Region) -> TranslationResult:
        # Capture a padded rectangle so edge text keeps a margin; the original `region`
        # is still what the UI anchors the overlay to. The margin also helps Vision:
        # a selection dragged flush to the text clips edge glyphs for any recognizer.
        try:
            image = self._capturer.capture(pad_region(region, self._capture_padding))
        except CaptureError as exc:
            logger.warning("capture failed for %s: %s", region, exc)
            return self._failed("", str(exc))

        vision_attempts: tuple[BackendAttempt, ...] = ()
        if self._image_translator is not None:
            label = f"{self._image_translator.name}:vision"
            try:
                result = self._image_translator.translate_image(image, self._source, self._target)
            except TranslationError as exc:
                logger.warning("%s failed: %s", label, exc)
                vision_attempts = (BackendAttempt(label, str(exc)),)
            else:
                return replace(result, attempts=(BackendAttempt(label),))
            if self._translator is None:  # Vision-only setup: nothing to fall back to
                return self._failed("", str(vision_attempts[0].error), vision_attempts)

        try:
            ocr_result = self._ocr.recognize(image, self._source)
        except OcrError as exc:
            logger.warning("OCR failed: %s", exc)
            return self._failed("", str(exc), vision_attempts)
        lines = clean_ocr_lines(ocr_result)
        logger.debug("OCR: %d raw lines -> %d cleaned", len(ocr_result.lines), len(lines))
        if not lines:
            return TranslationResult.no_text(self._source, self._target, attempts=vision_attempts)

        source_text = "\n".join(lines)
        result = self._translator.translate(source_text, self._source, self._target)
        return replace(result, attempts=(*vision_attempts, *result.attempts))

    def _failed(
        self, source_text: str, error: str, attempts: tuple[BackendAttempt, ...] = ()
    ) -> TranslationResult:
        return TranslationResult.failed(
            source_text, self._source, self._target, error=error, attempts=attempts
        )
