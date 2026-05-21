# SnipLingo — Game Overlay Translator

**日本語** | [English](README.md)

Windows 11 デスクトップアプリ。画面上で**範囲をドラッグ選択**し、**ホットキー**を押すと、その範囲を
キャプチャ → Windows 標準 OCR で英語を抽出 → **日本語**に翻訳 → **透過オーバーレイ**で表示します。
主にゲーム内テキストの翻訳が目的です（ボーダーレス/ウィンドウモードのゲーム対象。排他的フルスクリーンは非対応）。

## 特徴
- **完全無料**（APIキー・クレジットカード不要）。
  - 既定: Google 無料エンドポイント（`deep-translator`）
  - 失敗時（レート制限/通信エラー）: 短いバックオフ後に **Argos オフライン**へ自動フォールバック
  - DeepL は任意（キーを設定したときだけ有効）
- OCR は Windows 標準（無料・キー不要）。英語→日本語（言語は設定で変更可能な作り）。
- ホットキーで「押した瞬間」だけ翻訳（常時監視しない＝軽い）。

## 必要環境
- Windows 11 / Python **3.12**
- 英語の OCR 言語パック（多くの環境で導入済み。無い場合は下記トラブルシュート参照）

## セットアップ（開発）
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"            # オフライン翻訳も使うなら: pip install -e ".[dev,offline]"
```

## 起動と操作
```powershell
.\.venv\Scripts\python.exe -m sniplingo.ui.main      # または gui-script: sniplingo
```
1. 起動するとタスクトレイに常駐します（アイコン「訳」）。
2. **範囲選択 → 自動翻訳**: **範囲選択ホットキー（既定 `Ctrl+Alt+R`）** か トレイの **「範囲を選択して翻訳」** で
   領域をドラッグ選択（`Esc` でキャンセル）すると、**その場で翻訳**され透過オーバーレイに表示されます。
3. **オーバーレイ操作**:
   - **ドラッグで移動**できます。動かした位置は保存され、**次回の翻訳も同じ位置**に表示されます。
   - **× ボタン / 右クリック / `Esc`** で閉じられます。
4. **再翻訳**: トレイの **「現在の範囲を再翻訳」** で、同じ範囲をもう一度翻訳します（ゲーム内テキストが変わったとき用）。
5. **ショートカット変更**: トレイの **「範囲選択のショートカットを設定…」** で、設定したいキーを押すだけで登録できます
   （`config.json` に保存）。
6. トレイの「バックエンド: …」表示で、いまどの翻訳エンジンが使われたか分かります。

## 設定
設定は **`%APPDATA%\SnipLingo\config.json`** に保存されます（リポジトリには置きません）。主な項目:

| キー | 既定 | 説明 |
|---|---|---|
| `source_lang` / `target_lang` | `en` / `ja` | 翻訳の言語方向 |
| `select_region_hotkey` | `<ctrl>+<alt>+r` | 範囲選択（→自動翻訳）のホットキー（pynput 形式） |
| `default_backend` | `google_free` | `google_free` / `argos` / `deepl` |
| `enable_offline_fallback` | `true` | 失敗時に Argos へフォールバック |
| `deepl_api_key` | `null` | 設定時のみ DeepL が有効（ログに出力されません） |
| `overlay_opacity` | `0.85` | オーバーレイの不透明度（フォントは 16px 固定） |
| `overlay_position` | `null` | オーバーレイをドラッグした位置 `[x, y]`（未設定なら範囲の下に表示） |

## オフライン翻訳（Argos）モデルの導入
オフライン・フォールバックを使うには一度だけモデルのダウンロードが必要です（以降はネット不要）。
```powershell
pip install -e ".[offline]"
.\.venv\Scripts\python.exe -c "from sniplingo.adapters.argos_backend import install_package; install_package('en','ja')"
```

## 実行ファイル (exe) のビルド
コマンドではなくダブルクリックで起動できる exe を作れます（PyInstaller・one-folder）。
```powershell
.\.venv\Scripts\python.exe -m PyInstaller sniplingo.spec --noconfirm --clean
```
- 出力: **`dist\SnipLingo\SnipLingo.exe`**（`dist\SnipLingo\` フォルダごと配布。トレイ常駐・コンソール無し）。
- 同梱: Windows OCR(winrt) / mss / deep_translator / pynput / PySide6。**オフライン翻訳(argos)は意図的に除外**（容量削減）。
  - exe にオフライン翻訳も含めたい場合は `pip install -e ".[offline]"` 後に再ビルドし、`sniplingo.spec` の `excludes` から `argostranslate` 等を外してください。
- アイコンは `assets\sniplingo.ico`。

## テスト / 静的検査
```powershell
.\.venv\Scripts\python.exe -m pytest -q                 # 既定 = 高速ユニット (tests/unit)
.\.venv\Scripts\python.exe -m ruff check . ; .\.venv\Scripts\python.exe -m ruff format --check .

# 統合テスト（実機・任意）
.\.venv\Scripts\python.exe -m pytest tests/integration -m windows_ocr   # 要: 英語OCRパック
.\.venv\Scripts\python.exe -m pytest tests/integration -m display       # 要: デスクトップ
.\.venv\Scripts\python.exe -m pytest tests/integration -m network       # 要: ネット
$env:QT_QPA_PLATFORM="offscreen"; .\.venv\Scripts\python.exe -m pytest tests/integration -m qt
```

## トラブルシュート
- **OCR言語パックが無い**: 起動時に通知が出ます。管理者 PowerShell で:
  ```powershell
  Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
  ```
- **翻訳されない / 「失敗」表示**: 連打のレート制限や通信不調が原因のことがあります。少し待つか、
  Argos オフライン（上記）を導入してください。
- **オーバーレイがゲームに隠れる**: ゲームを**ボーダーレス/ウィンドウ**モードにしてください（排他的フルスクリーンは非対応）。
- **ホットキーが効かない**: トレイの「範囲を選択して翻訳」で代替できます。常駐ソフトとのキー競合時はトレイの「範囲選択のショートカットを設定…」（または `config.json` の `select_region_hotkey`）を変更してください。

## アーキテクチャ / 開発フロー
依存方向は内向き（`domain ← ports ← core ← adapters/ui`）。`domain`/`core` は Qt/Windows/ネットワークを import しません。
詳細は [`CLAUDE.md`](CLAUDE.md) と [`.claude/rules/`](.claude/rules)、手順スキルは [`.claude/skills/`](.claude/skills) を参照。
