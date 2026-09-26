"""PipelineRunner on a real QThread: only the latest request produces a result.
Run with: pytest tests/integration -m qt  (headless: QT_QPA_PLATFORM=offscreen)"""

import threading

import pytest

from sniplingo.domain.models import Region, TranslationResult
from sniplingo.ui.worker import PipelineRunner

pytestmark = pytest.mark.qt


class _BlockingPipeline:
    """The first run blocks until released, so later submits pile up behind it."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.started = threading.Event()
        self.ran: list[Region] = []

    def run(self, region: Region) -> TranslationResult:
        self.ran.append(region)
        if len(self.ran) == 1:
            self.started.set()
            self.release.wait(timeout=5)
        return TranslationResult(f"src{region.left}", f"訳{region.left}", "en", "ja", "fake")


def test_superseded_jobs_are_skipped_and_stale_results_dropped(qtbot):
    pipeline = _BlockingPipeline()
    runner = PipelineRunner(pipeline)
    received: list[tuple[Region, TranslationResult]] = []
    runner.finished.connect(lambda region, result: received.append((region, result)))
    try:
        a, b, c = Region(1, 0, 10, 10), Region(2, 0, 10, 10), Region(3, 0, 10, 10)
        runner.submit(a)
        assert pipeline.started.wait(timeout=5)  # A is running on the worker
        runner.submit(b)  # queued, then superseded by C before it starts
        runner.submit(c)
        pipeline.release.set()

        qtbot.waitUntil(lambda: len(received) == 1, timeout=5000)
        qtbot.wait(100)  # give a stray stale emission a chance to (wrongly) arrive
    finally:
        runner.shutdown()

    assert pipeline.ran == [a, c]  # B never ran
    assert len(received) == 1
    region, result = received[0]
    assert region == c  # overlay anchors to the region this result belongs to
    assert result.translated_text == "訳3"
