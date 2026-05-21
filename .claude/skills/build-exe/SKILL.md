---
name: build-exe
description: sniplingo を PyInstaller で Windows 実行ファイル(exe)にビルドする手順。配布用 exe を作る/更新するときに使う。
---

# build-exe

PySide6 製のトレイ常駐 GUI を one-folder の exe にする。設定は `sniplingo.spec`。

## 前提
- `pip install -e ".[dev]"`（PyInstaller を含む）が済んでいること。
- exe 用アイコンは `assets\sniplingo.ico`（無い場合は Pillow で再生成可能）。

## ビルド
```powershell
.\.venv\Scripts\python.exe -m PyInstaller sniplingo.spec --noconfirm --clean
```
- 出力: `dist\SnipLingo\SnipLingo.exe`（`dist\SnipLingo\` フォルダごと配布）。

## spec のポイント（遅延 import 対策）
`sniplingo` は境界維持のため重い依存を関数内で遅延 import している → PyInstaller の静的解析では拾えない。`sniplingo.spec` で明示済み:
- `collect_all("winrt")` … Windows OCR のネイティブ `_winrt_*.pyd`
- hiddenimports に `mss` / `PIL.Image` / `collect_submodules("deep_translator")` / `collect_submodules("pynput")`
- `excludes` に `argostranslate, ctranslate2, sentencepiece, stanza, torch`（オフライン翻訳は同梱しない）

## 確認
- `dist\SnipLingo\_internal\winrt\_winrt_windows_media_ocr*.pyd` と `PySide6\plugins\platforms\qwindows.dll` が存在すること。
- ピュア Python（mss/deep_translator/pynput）はフォルダ展開されず PYZ に入る（`build\SnipLingo\PYZ-00.toc` で確認可）。
- `dist\SnipLingo\SnipLingo.exe` を起動 → トレイに常駐すれば OK。

## オフライン翻訳も同梱したい場合
`pip install -e ".[offline]"` 後、`sniplingo.spec` の `excludes` から `argostranslate` 等を外して再ビルド（容量が大きく増える）。
