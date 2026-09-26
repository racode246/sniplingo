# SnipLingo — Game Overlay Translator

[日本語](README.ja.md) | **English**

A Windows 11 desktop app. **Drag-select a region** of the screen and it is captured →
text is extracted with the built-in **Windows OCR** (English) → translated into
**Japanese** → shown in a **translucent overlay**. It is aimed mainly at translating
in-game text (borderless / windowed games — exclusive fullscreen is not supported).

## Features
- **Official APIs only.**
  - Default: **Google Cloud Translation** (needs an API key; free for 500k characters/month — see below).
  - On failure: a short backoff and one retry, then automatic fallback to Google Cloud / DeepL (if its key is set).
    Permanent errors (bad key, quota exceeded) skip the retry. Gemini is never used as a fallback.
  - DeepL / **Gemini** are optional (enabled only when you set a key; Gemini keys are free from [Google AI Studio](https://aistudio.google.com/apikey)).
- OCR uses the built-in Windows engine (free, no key). English → Japanese (the language pair is config-driven).
- Translation happens on demand when you pick a region — there is no continuous polling, so it stays light.

## Requirements
- Windows 11 / Python **3.12**
- The English OCR language pack (present on most systems; see Troubleshooting if missing).

## Setup (development)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Getting a Google Cloud Translation API key
Translation uses Google's official **Cloud Translation API** (one-time setup).
1. In the [Google Cloud Console](https://console.cloud.google.com/), create (or pick) a project.
2. Enable **billing**. Cloud Translation is **free for the first 500,000 characters per month**; you pay only beyond that.
3. APIs & Services → Library → enable **Cloud Translation API**.
4. APIs & Services → Credentials → Create credentials → **API key**. Under **API restrictions**, restrict the key
   to Cloud Translation API only, so a leaked key can't be used for anything else.
5. In SnipLingo: tray → "翻訳設定…" (Translation settings) → paste it into **Google Cloud APIキー** → OK.

The key is stored only in `%APPDATA%\SnipLingo\config.json` and is written to logs as `****`.
To cap spending, set a daily character quota under Quotas in the Cloud Console.

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
7. **Logs**: the tray item **"ログフォルダを開く" (Open log folder)** opens `%APPDATA%\SnipLingo\logs`
   (`sniplingo.log`, rotated 1 MB × 3). Every backend attempt and failure is recorded there; API keys are masked.
   Set the environment variable `SNIPLINGO_LOG_LEVEL=DEBUG` for more detail.

## Configuration
Settings are stored in **`%APPDATA%\SnipLingo\config.json`** (never in the repo). Values of the wrong type or
outside the valid range fall back to the default. Main keys:

| Key | Default | Description |
|---|---|---|
| `source_lang` / `target_lang` | `en` / `ja` | Translation direction |
| `select_region_hotkey` | `<ctrl>+<alt>+r` | Region-select (→ auto-translate) hotkey (pynput format) |
| `default_backend` | `google_cloud` | `google_cloud` / `deepl` / `gemini` (a backend without its key is skipped) |
| `google_cloud_api_key` | `null` | Google Cloud Translation API key (never written to logs) |
| `deepl_api_key` | `null` | Enables DeepL only when set (never written to logs) |
| `gemini_api_key` | `null` | Enables Gemini only when set (never written to logs) |
| `gemini_model` | `gemini-2.5-flash` | Gemini model name (e.g. `gemini-2.5-flash-lite`, `gemini-2.5-pro`) |
| `overlay_opacity` | `0.85` | Overlay opacity, 0.1–1.0 (font is fixed at 16px) |
| `overlay_position` | `null` | Position `[x, y]` where you dragged the overlay (anchors below the region if unset) |
| `capture_padding` | `8` | Extra pixels captured around the selection, 0–64 (keeps OCR from clipping edge glyphs) |
| `ocr_scale` | `2` | Upscale factor before OCR, 1–4 |

**Fallback order**: `default_backend` first, then Google Cloud → DeepL (only those with a key).
Gemini is never a fallback — it is used only when chosen as `default_backend`.
With `gemini` as the default, the captured image goes straight to Gemini (Vision); if that fails, the
OCR + text chain runs without Gemini.

## Building the executable (.exe)
You can build a double-clickable exe instead of running a command (PyInstaller, one-folder).
```powershell
.\.venv\Scripts\python.exe -m PyInstaller sniplingo.spec --noconfirm --clean
```
- Output: **`dist\SnipLingo\SnipLingo.exe`** (distribute the whole `dist\SnipLingo\` folder; tray-resident, no console).
- Bundled: Windows OCR (winrt) / mss / requests / pynput / PySide6.
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

### OCR ground-truth corpus
Put an image and a same-named `.txt` holding the expected text side by side under `tests/data/ocr/`
(screenshots you can't redistribute go in the git-ignored `tests/data/ocr/local/`); every pair is then tested
through the real OCR path, with a similarity score per case. See [`tests/data/ocr/README.md`](tests/data/ocr/README.md).
```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr
```

## Troubleshooting
- **English OCR pack missing**: a tray notification appears on launch. In an admin PowerShell run:
  ```powershell
  Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
  ```
- **Nothing is translated / "失敗" (failure) shown**: the notification lists every backend that was tried and why
  it failed (details in the log — tray → "ログフォルダを開く"). Common causes: a wrong key (HTTP 400), or the Cloud Translation API not enabled / billing not set up
  (HTTP 403 — Google's explanation is shown in the notification). Setting a DeepL key gives the chain a fallback.
- **Overlay hidden behind the game**: switch the game to **borderless / windowed** mode (exclusive fullscreen is unsupported).
- **Hotkey doesn't work**: use the tray item "範囲を選択して翻訳" instead. If another resident app grabs the keys,
  change the combo via the tray's "範囲選択のショートカットを設定…" (or `select_region_hotkey` in `config.json`).

## Architecture / development flow
Dependencies point inward (`domain ← ports ← core ← adapters/ui`). `domain` / `core` never import Qt / Windows / network libraries.
See [`CLAUDE.md`](CLAUDE.md) and [`.claude/rules/`](.claude/rules); procedural skills live in [`.claude/skills/`](.claude/skills).
