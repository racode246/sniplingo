# SnipLingo — Game Overlay Translator

[日本語](README.ja.md) | **English**

A Windows 11 desktop app. **Drag-select a region** of the screen and it is captured →
text is extracted with the built-in **Windows OCR** (English) → translated into
**Japanese** → shown in a **translucent overlay**. It is aimed mainly at translating
in-game text (borderless / windowed games — exclusive fullscreen is not supported).

## Features
- **Completely free** (no API key, no credit card).
  - Default: Google's free endpoint (`deep-translator`).
  - On failure (rate limit / network error): a short backoff, then automatic fallback to **Argos offline**.
  - DeepL is optional (enabled only when you set a key).
- OCR uses the built-in Windows engine (free, no key). English → Japanese (the language pair is config-driven).
- Translation happens on demand when you pick a region — there is no continuous polling, so it stays light.

## Requirements
- Windows 11 / Python **3.12**
- The English OCR language pack (present on most systems; see Troubleshooting if missing).

## Setup (development)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"            # to also use offline translation: pip install -e ".[dev,offline]"
```

## Run & usage
```powershell
.\.venv\Scripts\python.exe -m sniplingo.ui.main      # or the gui-script: sniplingo
```
1. On launch it lives in the system tray (the "訳" icon).
2. **Select a region → auto-translate**: with the **region hotkey (default `Ctrl+Alt+R`)** or the tray item
   **"範囲を選択して翻訳" (Select region & translate)**, drag a region (`Esc` cancels). It is **translated
   immediately** and shown in the translucent overlay.
3. **Overlay controls**:
   - **Drag to move it.** The new position is saved and reused for the **next translation**.
   - Close it with the **× button / right-click / `Esc`**.
4. **Re-translate**: the tray item **"現在の範囲を再翻訳" (Re-translate current region)** runs the same region
   again (handy when in-game text changes).
5. **Change the shortcut**: the tray item **"範囲選択のショートカットを設定…" (Set region-select shortcut…)**
   lets you register a new combo just by pressing the keys (saved to `config.json`).
6. The tray status line "バックエンド: …" (Backend: …) shows which translation engine was used last.

## Configuration
Settings are stored in **`%APPDATA%\SnipLingo\config.json`** (never in the repo). Main keys:

| Key | Default | Description |
|---|---|---|
| `source_lang` / `target_lang` | `en` / `ja` | Translation direction |
| `select_region_hotkey` | `<ctrl>+<alt>+r` | Region-select (→ auto-translate) hotkey (pynput format) |
| `default_backend` | `google_free` | `google_free` / `argos` / `deepl` |
| `enable_offline_fallback` | `true` | Fall back to Argos on failure |
| `deepl_api_key` | `null` | Enables DeepL only when set (never written to logs) |
| `overlay_opacity` | `0.85` | Overlay opacity (font is fixed at 16px) |
| `overlay_position` | `null` | Position `[x, y]` where you dragged the overlay (anchors below the region if unset) |

## Installing the offline (Argos) model
The offline fallback needs a one-time model download (no network needed afterward).
```powershell
pip install -e ".[offline]"
.\.venv\Scripts\python.exe -c "from sniplingo.adapters.argos_backend import install_package; install_package('en','ja')"
```

## Building the executable (.exe)
You can build a double-clickable exe instead of running a command (PyInstaller, one-folder).
```powershell
.\.venv\Scripts\python.exe -m PyInstaller sniplingo.spec --noconfirm --clean
```
- Output: **`dist\SnipLingo\SnipLingo.exe`** (distribute the whole `dist\SnipLingo\` folder; tray-resident, no console).
- Bundled: Windows OCR (winrt) / mss / deep_translator / pynput / PySide6. **Offline translation (argos) is intentionally excluded** to keep the size down.
  - To bundle offline translation too, run `pip install -e ".[offline]"`, then rebuild after removing `argostranslate` (and friends) from `excludes` in `sniplingo.spec`.
- The icon is `assets\sniplingo.ico`.
- Note: stop any running `SnipLingo.exe` before rebuilding (`Get-Process SnipLingo | Stop-Process`), otherwise the bundled DLLs are locked.

## Tests / static checks
```powershell
.\.venv\Scripts\python.exe -m pytest -q                 # default = fast unit tests (tests/unit)
.\.venv\Scripts\python.exe -m ruff check . ; .\.venv\Scripts\python.exe -m ruff format --check .

# integration tests (real machine, opt-in)
.\.venv\Scripts\python.exe -m pytest tests/integration -m windows_ocr   # needs the English OCR pack
.\.venv\Scripts\python.exe -m pytest tests/integration -m display       # needs a desktop session
.\.venv\Scripts\python.exe -m pytest tests/integration -m network       # needs network
$env:QT_QPA_PLATFORM="offscreen"; .\.venv\Scripts\python.exe -m pytest tests/integration -m qt
```

## Troubleshooting
- **English OCR pack missing**: a tray notification appears on launch. In an admin PowerShell run:
  ```powershell
  Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
  ```
- **Nothing is translated / "失敗" (failure) shown**: usually rate limiting from rapid use or a flaky connection.
  Wait a moment, or install Argos offline (above).
- **Overlay hidden behind the game**: switch the game to **borderless / windowed** mode (exclusive fullscreen is unsupported).
- **Hotkey doesn't work**: use the tray item "範囲を選択して翻訳" instead. If another resident app grabs the keys,
  change the combo via the tray's "範囲選択のショートカットを設定…" (or `select_region_hotkey` in `config.json`).

## Architecture / development flow
Dependencies point inward (`domain ← ports ← core ← adapters/ui`). `domain` / `core` never import Qt / Windows / network libraries.
See [`CLAUDE.md`](CLAUDE.md) and [`.claude/rules/`](.claude/rules); procedural skills live in [`.claude/skills/`](.claude/skills).
