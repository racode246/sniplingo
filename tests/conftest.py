"""Pytest configuration. Hand-written fakes live in `tests/fakes.py` and are imported
directly by the unit tests (enabled by `pythonpath = ["."]` in pyproject.toml).
"""

from __future__ import annotations

import pytest
from tests.ocr_corpus import OCR_CORPUS_SCORES


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--ocr-min-similarity",
        type=float,
        default=0.9,
        help="OCR corpus pass mark: normalized text similarity in [0, 1] (1.0 = exact).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.stash[OCR_CORPUS_SCORES] = []


def pytest_terminal_summary(terminalreporter, exitstatus, config: pytest.Config) -> None:
    scores = config.stash.get(OCR_CORPUS_SCORES, [])
    if not scores:
        return
    threshold = config.getoption("--ocr-min-similarity")
    terminalreporter.section(f"OCR corpus similarity (pass >= {threshold:.2f})")
    for name, score in sorted(scores):
        mark = "ok  " if score >= threshold else "FAIL"
        terminalreporter.write_line(f"  {mark} {score:6.3f}  {name}")
    mean = sum(s for _, s in scores) / len(scores)
    terminalreporter.write_line(f"  mean {mean:.3f} over {len(scores)} case(s)")
