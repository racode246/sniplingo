---
name: run-checks
description: sniplingo のテスト・lint・整形・統合テストの実行方法。変更後の検証や CI 相当のチェックを回すときに使う。
---

# run-checks

すべて venv の Python で実行する（`.\.venv\Scripts\python.exe`）。`Activate.ps1` で有効化すれば `python`/`pytest`/`ruff` を直接呼べる。

## 標準チェック（変更ごと）
```powershell
.\.venv\Scripts\python.exe -m pytest -q                 # 既定 = tests/unit（高速・外部依存なし）
.\.venv\Scripts\python.exe -m ruff check .              # lint
.\.venv\Scripts\python.exe -m ruff format --check .     # 整形チェック（修正は format を引数なしで）
```

## カバレッジ
```powershell
.\.venv\Scripts\python.exe -m pytest --cov=sniplingo --cov-report=term-missing
```
domain / core を重点的に高く保つ（UI/adapters は低めで可）。

## 統合テスト（任意・実機）
既定の `pytest` には含まれない。明示的に marker 指定で実行する:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration -m windows_ocr   # 要: 英語 OCR 言語パック
.\.venv\Scripts\python.exe -m pytest tests/integration -m display       # 要: デスクトップセッション(mss)
.\.venv\Scripts\python.exe -m pytest tests/integration -m network       # 要: ネット(翻訳 smoke・flaky 許容)
.\.venv\Scripts\python.exe -m pytest tests/integration -m qt            # 要: Qt(pytest-qt)。ヘッドレスは $env:QT_QPA_PLATFORM="offscreen"
```

## OCR 正解コーパス（OCR 前処理・行クリーニングを触ったら必ず）
`tests/data/ocr/`（と git 管理外の `tests/data/ocr/local/`）の「画像＋同名 .txt」全ペアを実 OCR 経路で検証し、最後にケース別類似度を表示する。
ペアの欠け（画像だけ／txt だけ）は既定のユニットテストが検出する。詳細は `tests/data/ocr/README.md`。
```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr --ocr-min-similarity 1.0  # 完全一致
```
変更前後でスコア一覧（mean）を比較し、下がったケースがないか確認する。

## アプリ起動（手動確認）
```powershell
.\.venv\Scripts\python.exe -m sniplingo.ui.main
```

## マーカー一覧
`windows_ocr` / `network` / `display` / `qt`（定義は `pyproject.toml` の `[tool.pytest.ini_options].markers`）。
