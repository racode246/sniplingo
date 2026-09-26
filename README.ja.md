# SnipLingo — Game Overlay Translator

**日本語** | [English](README.md)

Windows 11 デスクトップアプリ。画面上で**範囲をドラッグ選択**し、**ホットキー**を押すと、その範囲を
キャプチャ → Windows 標準 OCR で英語を抽出 → **日本語**に翻訳 → **透過オーバーレイ**で表示します。
主にゲーム内テキストの翻訳が目的です（ボーダーレス/ウィンドウモードのゲーム対象。排他的フルスクリーンは非対応）。

## 特徴
- **公式 API で翻訳**。
  - 既定: **Google Cloud Translation**（API キーが必要。月 50 万文字まで無料。下記「API キーを用意する」参照）
  - 失敗時: 短いバックオフで 1 回リトライした後、Google Cloud / DeepL（キー設定時）へ自動フォールバック。
    キー不正・クォータ超過などの恒久的エラーはリトライせず即座に次へ。Gemini はフォールバックに使いません
  - DeepL / **Gemini** は任意（キーを設定したときだけ有効。Gemini は [Google AI Studio](https://aistudio.google.com/apikey) で無料発行可）
- OCR は Windows 標準（無料・キー不要）。英語→日本語（言語は設定で変更可能な作り）。
- ホットキーで「押した瞬間」だけ翻訳（常時監視しない＝軽い）。

## 必要環境
- Windows 11 / Python **3.12**
- 英語の OCR 言語パック（多くの環境で導入済み。無い場合は下記トラブルシュート参照）

## セットアップ（開発）
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Google Cloud Translation の API キーを用意する
翻訳には Google 公式の **Cloud Translation API** を使います（初回のみ設定）。
1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成（または既存を選択）。
2. **お支払い（課金アカウント）** を有効にする。Cloud Translation は **月 50 万文字まで無料**で、超えた分だけ課金されます。
3. 「API とサービス」→「ライブラリ」で **Cloud Translation API** を有効にする。
4. 「API とサービス」→「認証情報」→「認証情報を作成」→ **API キー**。作成したキーは
   **「API の制限」で Cloud Translation API のみに制限**しておくと、漏れたときの被害を抑えられます。
5. SnipLingo のトレイ →「翻訳設定…」→ **Google Cloud APIキー** に貼り付けて OK。

キーは `%APPDATA%\SnipLingo\config.json` にだけ保存され、ログには `****` で出力されます。
使いすぎが心配なら、Cloud Console の「割り当て」で 1 日あたりの文字数上限を設定できます。

## 起動と操作
```powershell
.\.venv\Scripts\python.exe -m sniplingo.ui.main      # または gui-script: sniplingo
```
1. 起動するとタスクトレイに常駐します（アイコン「訳」）。API キーが未設定なら、翻訳の代わりに設定画面が開きます。
2. **範囲選択 → 自動翻訳**: **範囲選択ホットキー（既定 `Ctrl+Alt+R`）** か トレイの **「範囲を選択して翻訳」** で
   領域をドラッグ選択（`Esc` でキャンセル）すると、**その場で翻訳**され透過オーバーレイに表示されます。
3. **オーバーレイ操作**:
   - **ドラッグで移動**できます。動かした位置は保存され、**次回の翻訳も同じ位置**に表示されます。
   - **× ボタン / 右クリック / `Esc`** で閉じられます。
4. **再翻訳**: トレイの **「現在の範囲を再翻訳」** で、同じ範囲をもう一度翻訳します（ゲーム内テキストが変わったとき用）。
5. **ショートカット変更**: トレイの **「範囲選択のショートカットを設定…」** で、設定したいキーを押すだけで登録できます
   （`config.json` に保存）。
6. トレイの「バックエンド: …」表示で、いまどの翻訳エンジンが使われたか分かります。
7. **ログ**: トレイの **「ログフォルダを開く」** で `%APPDATA%\SnipLingo\logs` を開けます（`sniplingo.log`、1MB×3 世代）。
   各バックエンドの試行と失敗理由が記録されます（API キーはマスク）。詳細が必要なら環境変数 `SNIPLINGO_LOG_LEVEL=DEBUG`。

## 設定
設定は **`%APPDATA%\SnipLingo\config.json`** に保存されます（リポジトリには置きません）。型違い・範囲外の値は既定値に戻ります。主な項目:

| キー | 既定 | 説明 |
|---|---|---|
| `source_lang` / `target_lang` | `en` / `ja` | 翻訳の言語方向 |
| `select_region_hotkey` | `<ctrl>+<alt>+r` | 範囲選択（→自動翻訳）のホットキー（pynput 形式） |
| `default_backend` | `google_cloud` | `google_cloud` / `deepl` / `gemini`（キー未設定のものは使われない） |
| `google_cloud_api_key` | `null` | Google Cloud Translation の API キー（ログに出力されません） |
| `deepl_api_key` | `null` | 設定時のみ DeepL が有効（ログに出力されません） |
| `gemini_api_key` | `null` | 設定時のみ Gemini が有効（ログに出力されません） |
| `gemini_model` | `gemini-2.5-flash` | 使用する Gemini モデル名（例: `gemini-2.5-flash-lite`, `gemini-2.5-pro`） |
| `overlay_opacity` | `0.85` | オーバーレイの不透明度 0.1〜1.0（フォントは 16px 固定） |
| `overlay_position` | `null` | オーバーレイをドラッグした位置 `[x, y]`（未設定なら範囲の下に表示） |
| `capture_padding` | `8` | 選択範囲の周囲に余分に取り込むピクセル数 0〜64（端の文字の欠け防止） |
| `ocr_scale` | `2` | OCR 前の拡大倍率 1〜4 |

**フォールバック順**: `default_backend` → Google Cloud → DeepL（キー設定済みのものだけ）。
Gemini はフォールバックにせず、`default_backend` に選んだときだけ使います。
`gemini` を既定にするとキャプチャ画像を Gemini に直接渡し（Vision）、失敗時は Gemini を除いた OCR＋テキスト翻訳で再試行します。

## 実行ファイル (exe) のビルド
コマンドではなくダブルクリックで起動できる exe を作れます（PyInstaller・one-folder）。
```powershell
.\.venv\Scripts\python.exe -m PyInstaller sniplingo.spec --noconfirm --clean
```
- 出力: **`dist\SnipLingo\SnipLingo.exe`**（`dist\SnipLingo\` フォルダごと配布。トレイ常駐・コンソール無し）。
- 同梱: Windows OCR(winrt) / mss / requests / pynput / PySide6。
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

### OCR 正解コーパス
`tests/data/ocr/` に画像と同名の `.txt`（正解テキスト）をペアで置くと、全ペアが実 OCR 経路で網羅的にテストされ、
ケースごとの類似度が表示されます（再配布できないスクショは git 管理外の `tests/data/ocr/local/` へ）。
詳細は [`tests/data/ocr/README.md`](tests/data/ocr/README.md)。
```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr
```

## トラブルシュート
- **OCR言語パックが無い**: 起動時に通知が出ます。管理者 PowerShell で:
  ```powershell
  Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"
  ```
- **翻訳されない / 「失敗」表示**: 通知に「試したバックエンドと各失敗理由」が出ます（詳細はトレイ →「ログフォルダを開く」）。
  よくある原因: キーの誤り（HTTP 400）、Cloud Translation API が未有効化・課金未設定（HTTP 403。通知に Google の説明が出ます）。
  DeepL のキーを設定しておくと、Google Cloud が失敗したときの自動フォールバック先になります。
- **オーバーレイがゲームに隠れる**: ゲームを**ボーダーレス/ウィンドウ**モードにしてください（排他的フルスクリーンは非対応）。
- **ホットキーが効かない**: トレイの「範囲を選択して翻訳」で代替できます。常駐ソフトとのキー競合時はトレイの「範囲選択のショートカットを設定…」（または `config.json` の `select_region_hotkey`）を変更してください。

## アーキテクチャ / 開発フロー
依存方向は内向き（`domain ← ports ← core ← adapters/ui`）。`domain`/`core` は Qt/Windows/ネットワークを import しません。
詳細は [`CLAUDE.md`](CLAUDE.md) と [`.claude/rules/`](.claude/rules)、手順スキルは [`.claude/skills/`](.claude/skills) を参照。
