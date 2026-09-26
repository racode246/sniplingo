"""Keep only the most recent translation request alive.

The user can fire the hotkey again before the previous translation finishes. Without
a gate the worker would grind through every queued request (burning rate limit) and
the GUI would flash stale results — anchored at the wrong region. The GUI issues a
job id per request; the worker skips ids that are no longer current, and the GUI drops
results whose id went stale while they were running. Thread-safe.
"""

from __future__ import annotations

import threading


class LatestJobGate:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest = 0

    def issue(self) -> int:
        """Register a new job and return its id; every earlier id becomes stale."""
        with self._lock:
            self._latest += 1
            return self._latest

    def is_current(self, job_id: int) -> bool:
        with self._lock:
            return job_id != 0 and job_id == self._latest
