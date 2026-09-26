import logging
import sys
import threading

import pytest

from sniplingo.ui.logging_setup import (
    LOG_FILE_NAME,
    RedactingFormatter,
    configure_logging,
    install_exception_hooks,
)


@pytest.fixture
def app_logger():
    """Restore the `sniplingo` logger after each test (configure_logging mutates it)."""
    logger = logging.getLogger("sniplingo")
    saved = (logger.level, list(logger.handlers), logger.propagate)
    yield logger
    for handler in logger.handlers:
        if handler not in saved[1]:
            handler.close()
    logger.setLevel(saved[0])
    logger.handlers[:] = saved[1]
    logger.propagate = saved[2]


def _read(log_dir) -> str:
    for handler in logging.getLogger("sniplingo").handlers:
        handler.flush()
    return (log_dir / LOG_FILE_NAME).read_text(encoding="utf-8")


def test_writes_app_logs_to_file_in_created_dir(tmp_path, app_logger):
    log_dir = tmp_path / "logs"
    configure_logging(log_dir)

    logging.getLogger("sniplingo.core.pipeline").info("hello %s", "world")

    text = _read(log_dir)
    assert "hello world" in text
    assert "sniplingo.core.pipeline" in text and "INFO" in text


def test_level_filters_debug_by_default(tmp_path, app_logger):
    configure_logging(tmp_path)
    logging.getLogger("sniplingo.x").debug("quiet")
    assert "quiet" not in _read(tmp_path)


def test_calling_twice_does_not_duplicate_lines(tmp_path, app_logger):
    configure_logging(tmp_path)
    configure_logging(tmp_path)
    logging.getLogger("sniplingo.x").warning("once")
    assert _read(tmp_path).count("once") == 1


def test_secrets_are_masked_in_messages_and_tracebacks(tmp_path, app_logger):
    formatter = configure_logging(tmp_path, secrets=["super-secret-key"])
    log = logging.getLogger("sniplingo.x")

    log.warning("key=%s", "super-secret-key")
    try:
        raise RuntimeError("boom with super-secret-key inside")
    except RuntimeError:
        log.exception("failed")

    formatter.set_secrets(["rotated-key-123"])
    log.warning("new %s", "rotated-key-123")

    text = _read(tmp_path)
    assert "super-secret-key" not in text
    assert "rotated-key-123" not in text
    assert text.count("****") >= 3


def test_short_values_are_not_treated_as_secrets():
    # Masking "a" or "" would shred every log line.
    formatter = RedactingFormatter("%(message)s", secrets=["", "ab"])
    record = logging.LogRecord("sniplingo", logging.INFO, __file__, 1, "abc", None, None)
    assert formatter.format(record) == "abc"


def test_uncaught_exceptions_are_logged_and_passed_on(tmp_path, app_logger, monkeypatch):
    passed_on: list[str] = []
    monkeypatch.setattr(sys, "excepthook", lambda *exc: passed_on.append("sys"))
    monkeypatch.setattr(threading, "excepthook", lambda args: passed_on.append("thread"))
    configure_logging(tmp_path)
    install_exception_hooks()

    try:
        raise ValueError("main-thread crash")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    try:
        raise KeyError("thread crash")
    except KeyError:
        exc_type, exc, tb = sys.exc_info()
        worker = threading.Thread(name="pipeline-worker")
        threading.excepthook(threading.ExceptHookArgs([exc_type, exc, tb, worker]))

    text = _read(tmp_path)
    assert "main-thread crash" in text
    assert "thread crash" in text and "pipeline-worker" in text
    assert passed_on == ["sys", "thread"]  # the previous hooks still run
