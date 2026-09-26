# Rule: アーキテクチャと依存方向

ビジネスロジックを Qt / Windows / ネットワークから切り離し、TDD 可能に保つ。

## レイヤと依存方向（内向きのみ）

```
domain  ←  ports  ←  core  ←  adapters / ui
（純粋）   （I/F）   （統制）   （具体実装・フレームワーク）
```

- **domain** (`src/sniplingo/domain/`): 純粋ロジックとデータ型。**いかなる I/O も外部ライブラリも import しない**（標準ライブラリと自分自身のみ）。
- **ports** (`src/sniplingo/ports/`): `Protocol` で定義したインターフェース。テストの継ぎ目（seam）。実行時の import は標準ライブラリと `domain` のみ（`PIL.Image` 等は `TYPE_CHECKING` 内で型参照）。
- **core** (`src/sniplingo/core/`): オーケストレーションと方針（pipeline / translator_chain / backend_plan / job_gate / config / settings_update / hotkey_parse）。**`domain` と `ports` のみに依存**し、実行時は標準ライブラリのみ（`logging`・`threading` は可）。
- **adapters** (`src/sniplingo/adapters/`): `ports` の具体実装。**Windows / サードパーティを import してよい唯一の場所**（mss, winrt, PIL, requests）。`core`・`ui` は import しない。HTTP は `adapters/http.py` の `HttpPost` 注入口と `post_json` を共通で使う。
- **ui** (`src/sniplingo/ui/`): PySide6・pynput。薄く保ち、処理は `core` に委譲する。adapters を import してよいのは **`ui/app.py`（composition root）だけ**。

## import ルール（ガードテストで強制）
`tests/unit/test_import_boundaries.py` がソースを AST 走査して検証する（違反でテストが落ちる）:
1. `domain` / `ports` / `core` は実行時に**標準ライブラリ（`sys.stdlib_module_names`）と `sniplingo` のみ** import 可。`if TYPE_CHECKING:` 内の型参照は除外。
2. 層の依存方向: domain→{domain} / ports→{domain, ports} / core→{domain, ports, core} / adapters→{domain, ports, adapters} / ui→{全層}（型参照の import も対象）。
3. `ui` の中で `adapters` を import できるのは `ui/app.py` のみ。
4. 相対 import 禁止（上記チェックをすり抜けるため）。

## 新機能の追加順序
1. 必要なら `domain` に型/純粋関数を追加（テスト先行）。
2. `ports` に Protocol を定義 or 拡張。
3. `core` をフェイクで**テスト駆動**実装。
4. 最後に `adapters`/`ui` に具体実装を足す（統合 marker テスト or 手動確認）。

依存性は**コンストラクタ注入**（DI）。`core` は具体クラスを new せず、`ports` 型を受け取る。配線は `ui/app.py` だけで行う。

関連: [`tdd.md`](tdd.md)
