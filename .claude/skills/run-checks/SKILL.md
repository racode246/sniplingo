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
.\.venv\Scripts\python.exe -m pytest tests/integration -m qt            # 要: Qt(pytest-qt)
```

## アプリ起動（手動確認）
```powershell
.\.venv\Scripts\python.exe -m sniplingo.ui.main
```

## マーカー一覧
`windows_ocr` / `network` / `display` / `qt`（定義は `pyproject.toml` の `[tool.pytest.ini_options].markers`）。
