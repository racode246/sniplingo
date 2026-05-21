---
name: release
description: SnipLingo の新バージョンを GitHub Release として公開する完全手順。バージョン決定・リリースノート作成・gh 認証など、スクリプトで自動化できない人手の部分を補完する。リリースを作る/やり直すときに使う。
---

# release

`scripts/release.ps1` が機械的な手順（バージョン設定 → 検査 → exe ビルド → zip → コミット → タグ → push → GitHub Release）を自動化する。スクリプトで完結できない**人手の判断・入力**をここで補う。

## 0. 前提（初回のみ）
- 開発環境: `pip install -e ".[dev]"`（PyInstaller を含む）。
- `git` が使えること（無ければ `winget install Git.Git`）。`gh`（GitHub CLI）も必要（無ければ `winget install GitHub.cli`）。
- **GitHub 認証**（スクリプト不可・人手）: `gh auth status` で `Logged in` を確認。未ログインなら:
  ```powershell
  & "C:\Program Files\GitHub CLI\gh.exe" auth login
  ```
- 起動中の `SnipLingo.exe` があれば終了（ビルド時のファイルロック回避。スクリプトも自動で停止を試みる）。

## 1. バージョンを決める（人手）
セマンティックバージョニング `X.Y.Z`。バグ修正=patch / 機能追加=minor / 破壊的変更=major。

## 2. リリースノートを書く（人手・スクリプト不可）
`scripts/RELEASE_NOTES_TEMPLATE.md` をコピーして編集し、ファイルに保存:
```powershell
Copy-Item scripts\RELEASE_NOTES_TEMPLATE.md notes-0.2.0.md
# notes-0.2.0.md を編集（Added / Changed / Fixed・使い方の要点 など）
```
この内容が GitHub Release の本文になる。

## 3. 作業ツリーを整える（人手）
- リリース対象のコード変更はコミット済みにする（スクリプトは version の2ファイルだけをコミットする）。
- 無関係な未コミット変更はコミット or `git stash`。

## 4. スクリプト実行
```powershell
pwsh scripts/release.ps1 -Version 0.2.0 -NotesFile notes-0.2.0.md
```
オプション:
- `-DryRun` … push と Release を行わず、ローカルでビルド・タグまで（動作確認用）。
- `-SkipTests` … ruff + pytest ゲートを飛ばす（非推奨）。

スクリプトが行うこと:
1. `pyproject.toml` と `src/sniplingo/__init__.py` の version を設定
2. `ruff check` / `ruff format --check` / `pytest`（tests/unit）
3. `PyInstaller sniplingo.spec` でビルド → `dist/SnipLingo-X.Y.Z-win64.zip`
4. version 変更があれば `Release vX.Y.Z` をコミット、注釈タグ `vX.Y.Z` を作成
5. `git push` + タグ push、`gh release create` で zip を添付

## 5. 確認
```powershell
& "C:\Program Files\GitHub CLI\gh.exe" release view vX.Y.Z
```
ブラウザ: https://github.com/racode246/sniplingo/releases

## やり直し（失敗・取り消し）
```powershell
git push origin :refs/tags/vX.Y.Z ; git tag -d vX.Y.Z   # タグを remote+local から削除
gh release delete vX.Y.Z --yes                          # Release を削除（作成済みなら）
git reset --hard HEAD~1                                  # 直前の "Release vX.Y.Z" コミット取消（push 前のみ）
```

## メモ / 落とし穴
- `gh` は内部で `git` を呼ぶため、`git` が PATH に無いと `unable to find git executable` で失敗する。スクリプトは git のディレクトリを PATH に追加してから `gh` を呼ぶ。
- exe は one-folder。zip は `dist/SnipLingo/` 一式（`SnipLingo.exe` + `_internal`）。単体の exe では動かない。
- 認証情報（gh トークン）はログ・コミットに残さない。
- 関連スキル: `build-exe`（ビルド単体）、`run-checks`（検査）。
