"""Decide which translation backends run, and in what order, from the config alone.

Pure policy — no adapters are constructed here; ``ui/app.py`` turns the plan into
concrete translators. Rules:

- Every backend is keyed: it is *usable* only when its API key is configured.
- The chosen ``default_backend`` goes first if usable.
- The other usable backends follow as fallbacks: Google Cloud Translation, then DeepL.
- Gemini is **never** a fallback: it runs only when chosen as ``default_backend``, and
  then on the **Vision** path (image in, translation out). The text chain is Vision's
  fallback and leaves Gemini out — it would just hit the same limit that made Vision fail.
- With no usable backend the plan is empty; the UI asks for a key instead of running.
"""

from __future__ import annotations

from dataclasses import dataclass

from sniplingo.core.config import AppConfig
from sniplingo.domain.models import BackendName

_FALLBACK_ORDER = (BackendName.GOOGLE_CLOUD, BackendName.DEEPL)  # Gemini: primary only


@dataclass(frozen=True)
class BackendPlan:
    vision: BackendName | None  # image translator to try first, if any
    text: tuple[BackendName, ...]  # text translators in chain order (may be empty)

    @property
    def is_empty(self) -> bool:
        """Nothing can translate: no backend has its key configured."""
        return self.vision is None and not self.text


def plan_backends(config: AppConfig) -> BackendPlan:
    usable = {
        BackendName.GOOGLE_CLOUD: config.has_google_cloud,
        BackendName.DEEPL: config.has_deepl,
        BackendName.GEMINI: config.has_gemini,
    }
    primary = config.default_backend if usable[config.default_backend] else None
    vision = BackendName.GEMINI if primary is BackendName.GEMINI else None

    text: list[BackendName] = []
    for name in (primary, *_FALLBACK_ORDER):
        if name is not None and usable[name] and name is not vision and name not in text:
            text.append(name)
    return BackendPlan(vision=vision, text=tuple(text))
