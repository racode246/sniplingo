# Rule: シークレット / 個人設定の扱い

翻訳は公式 API のみを使い、どのバックエンドも API キーが必要（既定: Google Cloud Translation。DeepL / Gemini は任意）。
キーはユーザーが自分で設定する。

- **API キーをリポジトリに置かない**。コード・テスト・サンプル・コミットに**ハードコード禁止**。
- Google Cloud / DeepL / Gemini のキー等のユーザー設定は **`%APPDATA%\SnipLingo\config.json`**（ユーザー領域）にのみ保存する。リポジトリ内には置かない。
- キーやトークンを**ログ・例外メッセージ・診断出力に出さない**。表示が必要な場合は `****` でマスク。
  - キーは **HTTP ヘッダでのみ送る**（URL・クエリ・本文に載せない）。API のエラー文を表示するときは `post_json(..., secrets=[key])` でキーをマスクする。例外メッセージに `requests` の例外文（URL を含み得る）を埋め込まない（`adapters/http.py` の `post_json` は例外の型名だけを出す）。
  - config を記録するときは `AppConfig.redacted()` を使う。最後の防波堤として `ui/logging_setup.RedactingFormatter` が設定済みキーをログ全文（トレースバック含む）から `****` に置換する。キー変更時は `set_secrets()` で更新する。
- `config` はロード時に**信頼しない**: 型を検証し、未知キーは無視し、欠損は既定値で補う。壊れた JSON でクラッシュさせない。
- `.gitignore` は `config.json` と `*.log` を含む（万一プロジェクト内に生成されても追跡しないための保険）。
- ネットワーク先は翻訳エンドポイントのみ。テレメトリ・外部送信を勝手に追加しない。
