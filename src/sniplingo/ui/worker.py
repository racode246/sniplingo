"""Run the translation pipeline off the GUI thread.

A single dedicated worker thread owns the pipeline so the `mss` instance and
`asyncio.run` (inside the OCR adapter) are always created/used on the same non-GUI
thread. Requests are marshaled in via a queued signal; results come back via signals.

Only the latest request matters (see :class:`LatestJobGate`): the worker skips jobs
that went stale while queued, and each result carries its job id and region so the
GUI can drop stale results and anchor the overlay to the region that was translated.
"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, QThread, Signal, Slot

from sniplingo.core.job_gate import LatestJobGate
from sniplingo.core.pipeline import TranslationPipeline
from sniplingo.domain.models import Region

logger = logging.getLogger(__name__)


class _Worker(QObject):
    finished = Signal(int, object, object)  # job id, Region, TranslationResult
    failed = Signal(int, str)  # job id, message (unexpected exceptions only)

    def __init__(self, pipeline: TranslationPipeline, gate: LatestJobGate) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._gate = gate

    @Slot(int, object)
    def process(self, job_id: int, region: Region) -> None:
        if not self._gate.is_current(job_id):
            logger.debug("job %d skipped: superseded before it started", job_id)
            return
        started = time.perf_counter()
        try:
            result = self._pipeline.run(region)
        except Exception as exc:  # noqa: BLE001 - report any pipeline failure to the UI
            logger.exception("job %d crashed", job_id)
            self.failed.emit(job_id, str(exc))
            return
        logger.info(
            "job %d: %s via %s in %.0f ms; attempts=%s",
            job_id,
            result.status,
            result.backend,
            (time.perf_counter() - started) * 1000,
            [(a.backend, a.error or "ok") for a in result.attempts],
        )
        self.finished.emit(job_id, region, result)

    @Slot(object)
    def replace_pipeline(self, pipeline: TranslationPipeline) -> None:
        # Runs on the worker thread (queued signal), so it can't race with `process`.
        self._pipeline = pipeline


class PipelineRunner(QObject):
    """GUI-facing facade: `submit(region)` runs the pipeline on the worker thread."""

    request = Signal(int, object)  # job id, region -> worker
    pipeline_changed = Signal(object)  # new TranslationPipeline -> worker
    finished = Signal(object, object)  # Region, TranslationResult -> GUI (current job only)
    failed = Signal(str)

    def __init__(self, pipeline: TranslationPipeline) -> None:
        super().__init__()
        self._gate = LatestJobGate()
        self._thread = QThread()
        self._thread.setObjectName("pipeline-worker")
        self._worker = _Worker(pipeline, self._gate)
        self._worker.moveToThread(self._thread)
        self.request.connect(self._worker.process)  # cross-thread => queued
        self.pipeline_changed.connect(self._worker.replace_pipeline)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.failed.connect(self._on_worker_failed)
        self._thread.start()

    def submit(self, region: Region) -> int:
        """Queue `region`; any job still pending or running becomes stale. Returns the id."""
        job_id = self._gate.issue()
        self.request.emit(job_id, region)
        return job_id

    def set_pipeline(self, pipeline: TranslationPipeline) -> None:
        """Swap the pipeline used by the worker (queued; happens between jobs)."""
        self.pipeline_changed.emit(pipeline)

    def shutdown(self) -> None:
        self._thread.quit()
        self._thread.wait()

    # Runs on the GUI thread (auto connection from the worker's thread => queued).
    def _on_worker_finished(self, job_id: int, region: Region, result: object) -> None:
        if not self._gate.is_current(job_id):
            logger.debug("job %d result dropped: a newer request superseded it", job_id)
            return
        self.finished.emit(region, result)

    def _on_worker_failed(self, job_id: int, message: str) -> None:
        if self._gate.is_current(job_id):
            self.failed.emit(message)
