"""Decide which translation backends run, and in what order, from the config alone.

Pure policy — no adapters are constructed here; ``ui/app.py`` turns the plan into
concrete translators. Rules:

- A keyed backend (DeepL, Gemini) is *usable* only when its key is configured;
  Google free is always usable.
- The chosen ``default_backend`` goes first if usable, else Google free.
- The other usable backends follow as fallbacks: Google free, then DeepL.
- Gemini is **never** a fallback: it runs only when chosen as ``default_backend``, and
  then on the **Vision** path (image in, translation out). The text chain is Vision's
  fallback and leaves Gemini out — it would just hit the same limit that made Vision fail.
"""

from __future__ import annotations

from dataclasses import dataclass

from sniplingo.core.config import AppConfig
from sniplingo.domain.models import BackendName

_FALLBACK_ORDER = (BackendName.GOOGLE_FREE, BackendName.DEEPL)  # Gemini: primary only


@dataclass(frozen=True)
class BackendPlan:
    vision: BackendName | None  # image translator to try first, if any
    text: tuple[BackendName, ...]  # text translators in chain order (never empty)


def plan_backends(config: AppConfig) -> BackendPlan:
    usable = {
        BackendName.GOOGLE_FREE: True,
        BackendName.DEEPL: config.has_deepl,
        BackendName.GEMINI: config.has_gemini,
    }
    primary = config.default_backend if usable[config.default_backend] else BackendName.GOOGLE_FREE
    vision = BackendName.GEMINI if primary is BackendName.GEMINI else None

    text: list[BackendName] = []
    for name in (primary, *_FALLBACK_ORDER):
        if usable[name] and name is not vision and name not in text:
            text.append(name)
    return BackendPlan(vision=vision, text=tuple(text))
