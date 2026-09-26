# CLAUDE.md — SnipLingo（ゲーム画面オーバーレイ翻訳）

## プロジェクト概要 / 目的
Windows 11 デスクトップアプリ。画面上で**範囲をドラッグ選択**すると、その範囲を
キャプチャ → Windows 標準 OCR で**英語**を抽出 → **日本語**に翻訳 → **透過オーバーレイ**で表示する。
主目的はゲーム内テキストの翻訳。対象はボーダーレス/ウィンドウモードのゲーム（排他的フルスクリーンは対象外）。

確定要件:
- 翻訳方向: 英語 → 日本語（言語は設定で変更可能な作り）
- **完全無料**（API キー・クレジットカード不要）。翻訳バックエンドは差し替え可能。
- トリガー: 範囲選択（ホットキー or トレイ）→ **自動翻訳**。専用の翻訳ホットキーは持たない。常時監視はしない。
- オーバーレイは操作可能（ドラッグで移動・位置を保存して次回も使用、× / 右クリック / Esc で閉じる）。
- 開発: 厳格な TDD

## 技術スタック
- Python **3.12** / GUI: **PySide6** / キャプチャ: **mss** / 画像: **Pillow**
- OCR: **PyWinRT**（`winrt-Windows.Media.Ocr` ほか namespace パッケージを直接使用。`winocr`/旧 `winrt` は使わない）
- 翻訳: **Google 無料 `client=gtx` API**（既定・キー不要）/ DeepL API v2（任意）/ Gemini（任意・Vision 対応）。いずれも **requests** で直接呼ぶ（`adapters/http.py` の共通注入口 `HttpPost`）
- ホットキー: **pynput**（`GlobalHotKeys`）→ Qt シグナルへブリッジ
- テスト: **pytest** + pytest-mock + pytest-qt + pytest-cov / Lint・整形: **ruff**

## ディレクトリ構成と依存方向（重要）
```
src/sniplingo/
  domain/    純粋ロジック・型（I/O・外部ライブラリ import 禁止）
  ports/     Protocol インターフェース（テストの継ぎ目）
  core/      オーケストレーション（domain/ports のみ依存）
  adapters/  ports の具体実装（mss/winrt/PIL/requests を import してよい唯一の場所）
  ui/        PySide6・pynput（薄く・core へ委譲）
tests/unit/         高速・外部依存なし（既定の pytest 対象）
tests/integration/  marker 付き・既定スキップ
tests/data/ocr/     OCR 正解コーパス（画像＋同名 .txt。local/ は git 管理外）
```
依存は内向きのみ: `domain ← ports ← core ← adapters/ui`。
`domain`/`ports`/`core` は実行時に標準ライブラリと `sniplingo` 以外を import しない（`TYPE_CHECKING` 内の型参照のみ可）。
層の依存方向・「adapters を import できるのは `ui/app.py` だけ」も含め `tests/unit/test_import_boundaries.py` で強制。
依存性はコンストラクタ注入。配線は `ui/app.py` のみ（どのバックエンドをどの順で使うかは `core/backend_plan.py` が決める）。詳細は **`.claude/rules/architecture.md`**。

## 開発フロー（TDD）
red（落ちるテスト）→ green（最小実装）→ refactor。各ユニット完了ごとに `pytest` を全緑に保つ。
pipeline/chain のテストは MagicMock ではなく **`ports` を実装した手書き Fake** を使う。
新機能は「domain → ports → core（テスト駆動）→ adapters/ui」の順。
手順は **`.claude/skills/tdd-cycle`**、検証コマンドは **`.claude/skills/run-checks`**、
翻訳バックエンド追加は **`.claude/skills/add-translator-backend`** を参照。

## コマンド
すべて venv の Python を使う（`.\.venv\Scripts\python.exe`）。`Activate.ps1` 有効化時は素の `python`/`pytest`/`ruff` でも可。
```powershell
# セットアップ（新規環境）
py -3.12 -m venv .venv          # この環境の Python: C:\Users\take3\AppData\Local\Programs\Python\Python312\python.exe
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# 検証
.\.venv\Scripts\python.exe -m pytest -q                  # 既定 = tests/unit
.\.venv\Scripts\python.exe -m ruff check . ; .\.venv\Scripts\python.exe -m ruff format .

# OCR 正解コーパス（tests/data/ocr の全ペアを実 OCR で検証・スコア一覧表示）
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr

# 起動
.\.venv\Scripts\python.exe -m sniplingo.ui.main

# exe ビルド（one-folder。出力 dist\SnipLingo\SnipLingo.exe）
.\.venv\Scripts\python.exe -m PyInstaller sniplingo.spec --noconfirm --clean
```

## exe パッケージング（PyInstaller）
`sniplingo.spec` で one-folder ビルド（`dist\SnipLingo\SnipLingo.exe`・コンソール無し）。
遅延 import の都合で hidden import を明示している: winrt は `collect_all("winrt")`、`mss`/`PIL.Image`/`pynput` を hiddenimports に追加（`requests` はモジュール先頭 import なので自動検出）。アイコンは `assets\sniplingo.ico`。

## 翻訳バックエンドの挙動
1. 既定 **Google 無料**（`translate.googleapis.com` の `client=gtx`・キー不要）。deep-translator の `GoogleTranslator` は `translate.google.com/m` をスクレイピングし IP 単位で CAPTCHA ブロック(429)されやすいため使わない。
2. **DeepL / Gemini** は任意。`%APPDATA%\SnipLingo\config.json` にキーがある時のみ有効化。
3. 順序は `core/backend_plan.py`: `default_backend`（キー無しなら Google）→ Google → DeepL（キー設定済みのみ）。
   **Gemini はフォールバックにしない**（既定バックエンドに選んだときだけ使う）。
   `gemini` が既定なら画像を直接 Gemini へ（Vision）、失敗時は Gemini を除くテキストチェーンへ。
4. 失敗の分類（`adapters/http.py`）: 通信エラー・408/429/5xx = `TranslationError`（バックオフ 1 回リトライ）、
   その他 4xx（キー不正 403・クォータ 456 等）= `PermanentTranslationError`（リトライせず次へ）。
   全滅時は全バックエンドの失敗理由をまとめた FAILED 結果を返す（`TranslationResult.attempts` に全試行を記録）。
   オフライン翻訳（Argos）は廃止済み。
キーの扱いは **`.claude/rules/secrets.md`** を厳守（リポジトリに置かない・ログに出さない）。

## ログ
`%APPDATA%\SnipLingo\logs\sniplingo.log`（1MB×3 ローテーション、トレイ「ログフォルダを開く」）。`sniplingo.*` ロガーのみ。
設定は `ui/logging_setup.py`（`RedactingFormatter` が設定済みキーを整形後の全文から `****` に置換）。`SNIPLINGO_LOG_LEVEL=DEBUG` で詳細。
「翻訳に失敗する」系の調査はまずこのログを見る（バックエンドごとの試行・失敗理由・所要時間が出る）。

## OCR メモ
- 起動時に `OcrEngine.is_language_supported(Language("en"))` を確認。無ければ管理者 PowerShell の
  `Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"` を案内し、クラッシュさせない。
- **この開発機では確認済み**: 利用可能な OCR 言語 = `en-US`, `ja`（`max_image_dimension = 10000`）。
- OCR 結果の `.lines`/`.words`（IVectorView）の列挙には `winrt-Windows.Foundation.Collections` が必要（依存に追加済み）。
- `asyncio.run(recognize_async(...))` と `mss.mss()` は GUI スレッドではなく**ワーカースレッド内**で生成・実行する。

## スレッドモデル（UI フリーズ回避）
3 スレッド: ①GUI（Qt イベントループ）②pynput 入力スレッド（コールバックは Qt シグナルを emit するだけ・**絶対にブロックしない**）③pipeline ワーカー（capture+OCR+translate）。ワーカー → GUI は `Qt.QueuedConnection` で marshaling。

## 規約（必読）
- `.claude/rules/tdd.md` — TDD の運用と完了の定義
- `.claude/rules/architecture.md` — レイヤと依存方向・禁止 import
- `.claude/rules/python-style.md` — スタイル・型・命名
- `.claude/rules/secrets.md` — シークレット/設定の扱い
