"""Run the translation pipeline off the GUI thread.

A single dedicated worker thread owns the pipeline so the `mss` instance and
`asyncio.run` (inside the OCR adapter) are always created/used on the same non-GUI
thread. Requests are marshaled in via a queued signal; results come back via signals.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from sniplingo.core.pipeline import TranslationPipeline
from sniplingo.domain.models import Region


class _Worker(QObject):
    finished = Signal(object)  # TranslationResult
    failed = Signal(str)

    def __init__(self, pipeline: TranslationPipeline) -> None:
        super().__init__()
        self._pipeline = pipeline

    @Slot(object)
    def process(self, region: Region) -> None:
        try:
            result = self._pipeline.run(region)
        except Exception as exc:  # noqa: BLE001 - report any pipeline failure to the UI
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class PipelineRunner(QObject):
    """GUI-facing facade: `submit(region)` runs the pipeline on the worker thread."""

    request = Signal(object)  # region -> worker
    finished = Signal(object)  # TranslationResult -> GUI
    failed = Signal(str)

    def __init__(self, pipeline: TranslationPipeline) -> None:
        super().__init__()
        self._thread = QThread()
        self._worker = _Worker(pipeline)
        self._worker.moveToThread(self._thread)
        self.request.connect(self._worker.process)  # cross-thread => queued
        self._worker.finished.connect(self.finished)
        self._worker.failed.connect(self.failed)
        self._thread.start()

    def submit(self, region: Region) -> None:
        self.request.emit(region)

    def shutdown(self) -> None:
        self._thread.quit()
        self._thread.wait()
