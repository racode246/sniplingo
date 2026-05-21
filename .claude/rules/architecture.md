# Rule: アーキテクチャと依存方向

ビジネスロジックを Qt / Windows / ネットワークから切り離し、TDD 可能に保つ。

## レイヤと依存方向（内向きのみ）

```
domain  ←  ports  ←  core  ←  adapters / ui
（純粋）   （I/F）   （統制）   （具体実装・フレームワーク）
```

- **domain** (`src/sniplingo/domain/`): 純粋ロジックとデータ型。**いかなる I/O も外部ライブラリも import しない**（標準ライブラリと自分自身のみ）。
- **ports** (`src/sniplingo/ports/`): `Protocol` で定義したインターフェース。テストの継ぎ目（seam）。型注釈以外の重い import を持たない（`PIL.Image` 等は文字列注釈 / `TYPE_CHECKING` で回避）。
- **core** (`src/sniplingo/core/`): オーケストレーション（pipeline / translator_chain / config / hotkey_parse）。**`domain` と `ports` のみに依存**。PySide6 / winrt / mss / pynput / deep_translator の実体を import しない（例外: `deep_translator.exceptions` の型参照は許容可だが、可能なら独自例外に変換する）。
- **adapters** (`src/sniplingo/adapters/`): `ports` の具体実装。**Windows / サードパーティを import してよい唯一の場所**（mss, winrt, deep_translator, argostranslate）。
- **ui** (`src/sniplingo/ui/`): PySide6・pynput。薄く保ち、処理は `core` に委譲する。

## 禁止 import（ガードテストで強制）
`domain` と `core` のモジュールは次を import してはならない: `PySide6`, `winrt`, `mss`, `pynput`, `deep_translator`, `argostranslate`, `requests`。
→ `tests/unit/test_import_boundaries.py` がソースを走査して検証する。違反したらテストが落ちる。

## 新機能の追加順序
1. 必要なら `domain` に型/純粋関数を追加（テスト先行）。
2. `ports` に Protocol を定義 or 拡張。
3. `core` をフェイクで**テスト駆動**実装。
4. 最後に `adapters`/`ui` に具体実装を足す（統合 marker テスト or 手動確認）。

依存性は**コンストラクタ注入**（DI）。`core` は具体クラスを new せず、`ports` 型を受け取る。配線は `ui/app.py` だけで行う。

関連: [`tdd.md`](tdd.md)
