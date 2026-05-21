"""Offline fallback translator backed by Argos Translate (`argostranslate`).

`argostranslate` is an optional dependency (``pip install -e ".[offline]"``) and is
imported lazily. The en->ja model must be downloaded once (see `install_package`);
afterwards translation works fully offline.
"""

from __future__ import annotations

from collections.abc import Callable

from sniplingo.domain.errors import TranslationError
from sniplingo.domain.models import BackendName, TranslationResult

TranslateFn = Callable[[str, str, str], str]


class ArgosTranslator:
    name = BackendName.ARGOS.value

    def __init__(self, translate_fn: TranslateFn | None = None) -> None:
        self._translate_fn = translate_fn or _default_translate

    def translate(self, text: str, source: str, target: str) -> TranslationResult:
        try:
            translated = self._translate_fn(text, source, target)
        except Exception as exc:  # noqa: BLE001 - argostranslate errors are untyped
            raise TranslationError(f"argos translate failed: {exc}") from exc
        if not translated:
            raise TranslationError("argos translate returned no text")
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source,
            target_lang=target,
            backend=self.name,
        )


def _default_translate(text: str, source: str, target: str) -> str:
    # Optional 'offline' extra; resolved only when Argos is actually used.
    import argostranslate.translate  # pyright: ignore[reportMissingImports]

    return argostranslate.translate.translate(text, source, target)


def install_package(source: str = "en", target: str = "ja") -> None:
    """One-time, network-required download+install of the offline model for source->target."""
    # Optional 'offline' extra; resolved only when installing the model.
    import argostranslate.package  # pyright: ignore[reportMissingImports]

    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    match = next((p for p in available if p.from_code == source and p.to_code == target), None)
    if match is None:
        raise TranslationError(f"no Argos package available for {source}->{target}")
    argostranslate.package.install_from_path(match.download())
