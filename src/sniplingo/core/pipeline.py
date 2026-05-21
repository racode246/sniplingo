"""Orchestrates one translation: capture -> OCR -> post-process -> translate.

Depends only on `ports` and `domain`. Concrete capturer / OCR / translator are
injected, so this is fully unit-testable with hand-written fakes.
"""

from __future__ import annotations

from sniplingo.domain.models import Region, TranslationResult
from sniplingo.domain.text_postprocess import clean_ocr_text
from sniplingo.ports.capture import ScreenCapturer
from sniplingo.ports.ocr import OcrEngine
from sniplingo.ports.translate import Translator


class TranslationPipeline:
    def __init__(
        self,
        capturer: ScreenCapturer,
        ocr: OcrEngine,
        translator: Translator,
        source: str = "en",
        target: str = "ja",
    ) -> None:
        self._capturer = capturer
        self._ocr = ocr
        self._translator = translator
        self._source = source
        self._target = target

    def run(self, region: Region) -> TranslationResult:
        image = self._capturer.capture(region)
        ocr_result = self._ocr.recognize(image, self._source)
        text = clean_ocr_text(ocr_result)
        if not text:
            # Nothing recognized — don't waste a translation call.
            return TranslationResult(
                source_text="",
                translated_text="",
                source_lang=self._source,
                target_lang=self._target,
                backend="",
                error="no_text",
            )
        return self._translator.translate(text, self._source, self._target)
