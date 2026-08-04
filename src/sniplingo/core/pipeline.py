"""Orchestrates one translation: capture -> (image LLM) | (OCR -> translate).

Depends only on `ports` and `domain`. Concrete capturer / OCR / translator are
injected, so this is fully unit-testable with hand-written fakes.

Two paths:
- **Vision**: when an :class:`ImageTranslator` is provided (e.g. Gemini), the
  captured image is sent directly for combined OCR + translation, skipping
  Windows OCR and any text post-processing. This is the fast / high-quality path.
- **Text**: otherwise (or if Vision fails), Windows OCR extracts text, the
  cleaned lines are joined with ``\\n`` and sent to the :class:`Translator` chain
  in a single round-trip.
"""

from __future__ import annotations

from sniplingo.domain.errors import TranslationError
from sniplingo.domain.geometry import pad_region
from sniplingo.domain.models import Region, TranslationResult
from sniplingo.domain.text_postprocess import clean_ocr_lines
from sniplingo.ports.capture import ScreenCapturer
from sniplingo.ports.image_translate import ImageTranslator
from sniplingo.ports.ocr import OcrEngine
from sniplingo.ports.translate import Translator

# A small quiet zone around the selection. Windows OCR drops glyphs that touch the
# image edge, so a selection dragged flush to the text loses its first/last characters.
DEFAULT_CAPTURE_PADDING = 8


class TranslationPipeline:
    def __init__(
        self,
        capturer: ScreenCapturer,
        ocr: OcrEngine,
        translator: Translator,
        source: str = "en",
        target: str = "ja",
        image_translator: ImageTranslator | None = None,
        capture_padding: int = DEFAULT_CAPTURE_PADDING,
    ) -> None:
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
        image = self._capturer.capture(pad_region(region, self._capture_padding))

        if self._image_translator is not None:
            try:
                return self._image_translator.translate_image(image, self._source, self._target)
            except TranslationError:
                pass  # fall through to the OCR-based text path

        ocr_result = self._ocr.recognize(image, self._source)
        lines = clean_ocr_lines(ocr_result)
        if not lines:
            return TranslationResult(
                source_text="",
                translated_text="",
                source_lang=self._source,
                target_lang=self._target,
                backend="",
                error="no_text",
            )
        source_text = "\n".join(lines)
        return self._translator.translate(source_text, self._source, self._target)
