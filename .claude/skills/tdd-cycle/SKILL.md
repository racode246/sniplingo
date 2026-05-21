---
name: tdd-cycle
description: sniplingo で 1 つの振る舞いを red→green→refactor で実装する手順。新しい純粋関数・core ロジック・バグ修正を実装する前に従う。
---

# tdd-cycle

1 ユニットの振る舞いを TDD で実装するための手順。詳細な方針は `.claude/rules/tdd.md` を参照。

## 手順
1. **置き場所を決める**: 実装先 `src/sniplingo/<layer>/<mod>.py` に対しテストは `tests/unit/test_<mod>.py`。レイヤと依存方向は `.claude/rules/architecture.md` に従う。
2. **red**: 望む振る舞いを表す最小のテストを書く。境界値・異常系（空・例外・短絡）も 1 ケースずつ。
   - 実行して**意図どおり落ちる**ことを確認:
     ```powershell
     .\.venv\Scripts\python.exe -m pytest tests/unit/test_<mod>.py -q
     ```
3. **green**: 通すだけの**最小実装**を書く。再実行して緑にする。
4. **refactor**: 重複除去・命名改善・型付け。テストは緑のまま。
5. **全体確認**:
   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check . ; .\.venv\Scripts\python.exe -m ruff format .
   ```
6. アーキ境界ガード `tests/unit/test_import_boundaries.py` が緑であることを確認。

## 注意
- pipeline / chain のテストは `MagicMock` ではなく `ports` Protocol を実装した**手書き Fake**を使う。
- 外部依存（実 OCR・実ネット・Qt）に触れるなら unit ではなく `tests/integration/` に置き marker を付ける（`run-checks` スキル参照）。
