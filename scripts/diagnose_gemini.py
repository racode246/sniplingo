"""Quick diagnostic for the Gemini backend.

Reads ``%APPDATA%\\SnipLingo\\config.json``, prints what the app would see (key
masked), and tries one real translate call so you can see the actual error from
Gemini instead of just a tray "失敗" notification.

Run from the project root:

    .\\.venv\\Scripts\\python.exe scripts\\diagnose_gemini.py
"""

from __future__ import annotations

import sys

from sniplingo.adapters.gemini_backend import GeminiTranslator
from sniplingo.core.config import default_config_path, load_config
from sniplingo.domain.errors import TranslationError


def main() -> int:
    path = default_config_path()
    config = load_config(path)

    masked = "(set)" if config.has_gemini else "(MISSING)"
    print(f"config path        : {path}")
    print(f"config exists      : {path.exists()}")
    print(f"default_backend    : {config.default_backend}")
    print(f"gemini_api_key     : {masked}")
    print(f"gemini_model       : {config.gemini_model}")
    print(f"source/target lang : {config.source_lang} -> {config.target_lang}")

    if not config.has_gemini:
        print("\n[NG] gemini_api_key が設定されていません。'翻訳設定…' から登録するか")
        print("    config.json に gemini_api_key を追加してください。")
        return 1

    if config.default_backend != "gemini":
        print(
            f"\n[!]  default_backend が '{config.default_backend}' のため、UI からは"
            " Gemini が呼ばれません。"
        )
        print("    Gemini を試すため、ここでは直接呼び出します。")

    print("\n→ Gemini に 'Hello world' を翻訳依頼します...")
    backend = GeminiTranslator(config.gemini_api_key or "", model=config.gemini_model)
    try:
        result = backend.translate("Hello world", config.source_lang, config.target_lang)
    except TranslationError as exc:
        print(f"[NG] TranslationError: {exc}")
        cause = exc.__cause__
        if cause is not None:
            print(f"    cause: {type(cause).__name__}: {cause}")
        return 2
    except Exception as exc:  # noqa: BLE001 - diagnostic; show whatever happened
        print(f"[NG] {type(exc).__name__}: {exc}")
        return 3

    print(f"[OK] translated_text = {result.translated_text!r}")
    print(f"[OK] backend         = {result.backend}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
