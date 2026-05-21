# Rule: Python スタイル

- **対象バージョン**: Python 3.12（`requires-python = ">=3.12,<3.13"`）。
- **整形 / Lint**: `ruff`。`ruff format` で整形、`ruff check` で lint（設定は `pyproject.toml` の `[tool.ruff]`）。コミット相当の区切りごとに両方を通す。
- **型ヒント**: 公開関数・メソッドには型注釈を付ける。インターフェースは `typing.Protocol`。重い型（`PIL.Image.Image` 等）は文字列注釈 or `if TYPE_CHECKING:` で実 import を避け、境界を守る。
- **データ型**: 値オブジェクトは `@dataclass`（不変が望ましいものは `frozen=True`）。列挙は `enum.Enum` / `StrEnum`。
- **命名**: モジュール/関数/変数 `snake_case`、クラス `PascalCase`、定数 `UPPER_SNAKE`。port 実装の adapter は役割が分かる名前（例 `MssCapturer`, `WinRtOcrEngine`, `GoogleFreeTranslator`）。
- **docstring**: モジュール先頭とクラス/公開関数に簡潔な説明。日本語コメント可。
- **import**: 標準 → サードパーティ → 自プロジェクト の順（ruff の `I` ルールが自動整列）。`domain`/`core` での禁止 import は [`architecture.md`](architecture.md) を参照。
- **例外**: 失敗は握りつぶさない。adapter 層で外部例外を捕捉し、必要なら `core` が扱える独自例外/結果型に変換する。シークレットを例外メッセージやログに出さない（[`secrets.md`](secrets.md)）。
- **行長**: 100 桁。
