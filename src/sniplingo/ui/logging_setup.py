"""File logging for the (console-less) app: ``%APPDATA%\\SnipLingo\\logs\\sniplingo.log``.

Only the ``sniplingo.*`` logger tree is captured (third-party chatter like urllib3 stays
out). The file rotates (1 MB x 3). Every formatted line — message *and* traceback — is
scrubbed of configured secrets by :class:`RedactingFormatter`, as a backstop to
``.claude/rules/secrets.md``. Set ``SNIPLINGO_LOG_LEVEL=DEBUG`` for more detail.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from collections.abc import Iterable
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "sniplingo.log"
_APP_LOGGER = "sniplingo"
_FORMAT = "%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s"
_MASK = "****"
_MIN_SECRET_LENGTH = 4  # shorter values would mask ordinary words
_HANDLER_MARK = "_sniplingo_file_handler"


class RedactingFormatter(logging.Formatter):
    def __init__(self, fmt: str, *, secrets: Iterable[str] = ()) -> None:
        super().__init__(fmt)
        self._secrets: tuple[str, ...] = ()
        self.set_secrets(secrets)

    def set_secrets(self, secrets: Iterable[str]) -> None:
        """Replace the values to mask (e.g. after the user changes an API key)."""
        unique = {s for s in secrets if s and len(s) >= _MIN_SECRET_LENGTH}
        # Longest first so a secret containing another is masked whole.
        self._secrets = tuple(sorted(unique, key=len, reverse=True))

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        for secret in self._secrets:
            text = text.replace(secret, _MASK)
        return text


def configure_logging(
    log_dir: Path, *, secrets: Iterable[str] = (), level: int | str | None = None
) -> RedactingFormatter:
    """Attach the rotating file handler (idempotent) and return its formatter."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_APP_LOGGER)
    for handler in [h for h in logger.handlers if getattr(h, _HANDLER_MARK, False)]:
        logger.removeHandler(handler)
        handler.close()

    formatter = RedactingFormatter(_FORMAT, secrets=secrets)
    handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(formatter)
    setattr(handler, _HANDLER_MARK, True)
    logger.addHandler(handler)
    logger.setLevel(level or os.environ.get("SNIPLINGO_LOG_LEVEL", "INFO").upper())
    return formatter


def install_exception_hooks() -> None:
    """Log uncaught exceptions (main thread and worker threads) before the defaults run."""
    logger = logging.getLogger(_APP_LOGGER)
    previous_sys_hook = sys.excepthook
    previous_thread_hook = threading.excepthook

    def sys_hook(exc_type, exc, tb) -> None:
        logger.critical("uncaught exception", exc_info=(exc_type, exc, tb))
        previous_sys_hook(exc_type, exc, tb)

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        name = args.thread.name if args.thread else "?"
        logger.critical(
            "uncaught exception in thread %s",
            name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        previous_thread_hook(args)

    sys.excepthook = sys_hook
    threading.excepthook = thread_hook
