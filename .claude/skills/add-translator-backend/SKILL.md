---
name: add-translator-backend
description: sniplingo に新しい翻訳バックエンド（例 DeepL・別エンジン）を Translator port 実装として追加する手順。翻訳プロバイダを足す/差し替えるときに従う。
---

# add-translator-backend

翻訳は差し替え可能（プラグイン式）。`ports.translate.Translator` Protocol を実装する新クラスを追加する。

## 前提
- インターフェース: `src/sniplingo/ports/translate.py` の `Translator`（`name` 属性 + `translate(text, source, target) -> TranslationResult`）。
- フォールバック制御: `src/sniplingo/core/translator_chain.py`（primary 失敗時に次へ）。
- 設定: `src/sniplingo/core/config.py`（既定バックエンドや DeepL キー等）。

## 手順
1. **テスト先行**（`tests/unit/test_<backend>_backend.py`）:
   - 成功時に `TranslationResult` を返すこと（外部 SDK は Fake/モンキーパッチで差し替え、ネットに出ない）。
   - 失敗時に**送出する例外の種類**を定義し、それを検証（chain がフォールバック判定に使う）。
2. **実装**（`src/sniplingo/adapters/<backend>_backend.py`）:
   - `Translator` を実装。外部ライブラリの import は**この adapter 内のみ**（`.claude/rules/architecture.md`）。
   - 外部例外を捕捉し、chain が扱える例外/結果に変換。`name` を設定。
3. **配線**:
   - 必要なら `core/config.py` に設定項目を追加（DeepL キー等は `%APPDATA%\SnipLingo\config.json`、`.claude/rules/secrets.md` 厳守）。
   - `ui/app.py` の DI で `translator_chain` の候補に登録（既定/フォールバック順）。
4. **統合テスト（任意）**: 実プロバイダに繋ぐ smoke は `tests/integration/` に `@pytest.mark.network` で追加（既定実行から除外）。
5. `tdd-cycle` の最終確認（pytest 全緑・ruff・境界ガード）を実施。

## 既存バックエンド
- `GoogleFreeTranslator`（deep-translator・既定・キー不要）
- `ArgosTranslator`（オフライン・フォールバック・`[offline]` extra）
- `DeepLTranslator`（任意・キー設定時のみ有効）
