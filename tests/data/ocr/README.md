# OCR 正解コーパス

画像と、その画像から **翻訳エンジンへ送られるべきテキスト**（正解）を同名ペアで置くと、
すべてのペアが網羅的にテストされます。

```
tests/data/ocr/
  synthetic_item_tooltip.png   ← 画像（.png / .jpg / .jpeg / .bmp）
  synthetic_item_tooltip.txt   ← 正解（UTF-8、1 行 = 翻訳に渡すべき 1 まとまり）
  local/                       ← git 管理外。ゲームのスクショなど再配布できない画像はここへ
    poe_gloves.jpg
    poe_gloves.txt
```

- サブフォルダも再帰的に探索します。ケース名は相対パス（例 `local/poe_gloves`）。
- `.txt` は **実際の画面の文字**を書きます（OCR の出力を写さない）。
  改行のルール: 画面幅で折り返された文章（段落）は **1 行につなげる**。ツールチップの各項目・メニュー項目など
  独立した行はそのまま 1 行ずつ。アプリも同じ規則で行をまとめてから翻訳に渡します
  （`domain/text_postprocess.clean_ocr_lines`）。比較時に
  大文字小文字・行頭行末や連続空白・空行は無視されます（ゲームのスモールキャップス対策）。
- 片方しかないファイルはユニットテスト（既定の `pytest`）が検出して落とします。

## 実行

実 OCR（Windows.Media.Ocr）を使うため統合テスト扱いです。

```powershell
# 全ケース（スコア一覧が最後に表示される）
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr
# 合格ラインを変える（既定 0.9、1.0 = 完全一致）
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr --ocr-min-similarity 0.8
# 1 ケースだけ
.\.venv\Scripts\python.exe -m pytest tests/integration/test_ocr_corpus_real.py -m windows_ocr -k poe_gloves
```

画像はアプリと同じ経路（前処理 → Windows OCR → 行クリーニング → `\n` 結合）を通り、
翻訳直前のテキストが正解と比較されます。失敗時は unified diff と類似度が表示されます。
