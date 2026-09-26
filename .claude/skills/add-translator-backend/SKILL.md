---
name: add-translator-backend
description: sniplingo に新しい翻訳バックエンド（例 DeepL・別エンジン）を Translator port 実装として追加する手順。翻訳プロバイダを足す/差し替えるときに従う。
---

# add-translator-backend

翻訳は差し替え可能（プラグイン式）。`ports.translate.Translator` Protocol を実装する新クラスを追加する。

## 前提
- インターフェース: `src/sniplingo/ports/translate.py` の `Translator`（`name` 属性 + `translate(text, source, target) -> TranslationResult`）。
- フォールバック制御: `src/sniplingo/core/translator_chain.py`（`TranslationError` = リトライ後に次へ、`PermanentTranslationError` = 即座に次へ）。
- 使う順序: `src/sniplingo/core/backend_plan.py`（`plan_backends(config)`。フォールバックに入れるかは `_FALLBACK_ORDER` で決める。Gemini は既定選択時のみ）。
- HTTP: `src/sniplingo/adapters/http.py`（`HttpPost` 注入口 + `post_json` がステータスを transient/permanent に分類）。
- 設定: `src/sniplingo/core/config.py`（既定バックエンドや DeepL キー等）。

## 手順
1. **テスト先行**（`tests/unit/test_<backend>_backend.py`）:
   - 成功時に `TranslationResult` を返すこと。HTTP 系は `tests/fakes.py` の `FakeHttpPost` / `FakeHttpResponse` を `post=` に注入し、ネットに出ない。
   - 送信内容（URL・ヘッダ認証・本文）と、失敗時の例外の種類（429 → `TranslationError`、403 等 → `PermanentTranslationError`、壊れた応答 → `TranslationError`）を検証。
   - キーが URL・例外メッセージに出ないことを検証（`.claude/rules/secrets.md`）。
2. **実装**（`src/sniplingo/adapters/<backend>_backend.py`）:
   - `Translator` を実装。コンストラクタで `post: HttpPost = requests_post` を受け取り `post_json(...)` で呼ぶ（外部ライブラリの import は adapter 内のみ）。
   - 応答の形を検証して訳文を取り出し、空なら `TranslationError`。`name` を設定。
3. **配線**:
   - 必要なら `core/config.py` に設定項目を追加（DeepL キー等は `%APPDATA%\SnipLingo\config.json`、`.claude/rules/secrets.md` 厳守）。
   - `domain/models.BackendName` に追加 → `core/backend_plan.py` の usable 判定とフォールバック順に追加（テスト先行: `tests/unit/test_backend_plan.py`）→ `ui/app.py` の `_make_translator` に生成を追加 → `ui/settings_dialog.py` の選択肢に追加。
4. **統合テスト（任意）**: 実プロバイダに繋ぐ smoke は `tests/integration/` に `@pytest.mark.network` で追加（既定実行から除外）。
5. `tdd-cycle` の最終確認（pytest 全緑・ruff・境界ガード）を実施。

## 既存バックエンド
- `GoogleFreeTranslator`（`client=gtx` JSON API・既定・キー不要）
- `DeepLTranslator`（DeepL API v2 直呼び・任意・`:fx` キーは Free エンドポイント）
- `GeminiTranslator`（任意・テキスト翻訳と Vision〈画像直接〉の両方を実装）
