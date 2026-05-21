# Rule: TDD（テスト駆動開発）

このプロジェクトは**厳格な TDD** で開発する。例外は UI 配線・サードパーティ adapter の薄いラッパのみ（それらは統合テスト or 手動で確認）。

## red → green → refactor サイクル
1. **red**: 追加したい振る舞いに対して、まず**落ちるテスト**を 1 つ書く。実行して「期待どおりに落ちる」ことを確認する（assert 内容の取り違えを防ぐ）。
2. **green**: テストを通す**最小限**の実装を書く。過剰実装しない。
3. **refactor**: 重複・命名・構造を整える。テストは緑のまま維持する。

## 必須の運用
- 各ユニットを終えるたびに `python -m pytest`（既定 = `tests/unit`）を**全緑**にしてから次へ進む。
- 実装ファイルを書く前に対応するテストファイルを作る（`src/sniplingo/X.py` には `tests/unit/test_X.py`）。
- **pipeline / chain などオーケストレーションのテストでは `MagicMock` を使わず、`ports` の Protocol を実装した手書き Fake を使う**（契約をドキュメント化し、リファクタに強い）。フェイクは `tests/conftest.py` か各テスト内に置く。
- 外部依存（実 OCR・実ネット翻訳・Qt）に触れるテストは**統合テスト**として `tests/integration/` に置き、marker（`windows_ocr` / `network` / `display` / `qt`）を付ける。既定の `pytest` 実行には含めない。
- 1 つのテストは 1 つの振る舞いを検証する。境界値・異常系（空入力・例外・短絡）を網羅する。
- バグ修正も同じ: まず**そのバグを再現する落ちるテスト**を書いてから直す。

## 完了の定義（Definition of Done）
- 対象の振る舞いに対するユニットテストがあり、`pytest` が全緑。
- `ruff check .` と `ruff format --check .` が通る。
- アーキ境界ガード（`tests/unit/test_import_boundaries.py`）が緑。

関連: [`architecture.md`](architecture.md) / [`python-style.md`](python-style.md)
