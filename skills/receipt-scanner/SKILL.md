# Receipt Scanner

レシート画像から店名・日付・商品・金額をOCRで読み取り、購入履歴に登録するスキル。

## Trigger Phrases

- 「このレシートを読み取って」
- 「レシートを登録して」
- 「Scan this receipt」
- 「レシートの写真を送る」

## Dependencies

- Tesseract OCR (system install)
  - macOS: `brew install tesseract tesseract-lang`
  - Ubuntu: `sudo apt install tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng`
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Python packages: `pytesseract`, `Pillow`, `opencv-python-headless`

## Processing Flow

1. ユーザーがレシート画像を送信（JPG/PNG）
2. 画像前処理（グレースケール → ノイズ除去 → 二値化 → 傾き補正）
3. Tesseract OCR で文字認識（日本語 + 英語）
4. 構造化パーサーで以下を抽出:
   - 店名（先頭数行のヒューリスティック）
   - 日付（正規表現パターン）
   - 商品名 + 金額（行ごとの価格パターンマッチ）
   - 合計金額（「合計」「Total」等のキーワード行）
   - 通貨（¥/$/ €/£ 記号から自動判定）
5. 抽出結果をユーザーに表示し確認を依頼
6. 確定後:
   - `receipt_scans` テーブルにスキャン情報を保存
   - `receipt_items` テーブルに個別商品を保存
   - `purchase_history` テーブルにも連携登録

## Script Execution

```bash
python3 ~/.openclaw/workspace/scripts/import_receipt.py <image_path> [db_path] [--lang LANG]
```

### Language Options

| Option | Tesseract Lang | Use Case |
|--------|---------------|----------|
| `ja` | `jpn` | Japanese receipts only |
| `en` | `eng` | English receipts only |
| `ja+en` | `jpn+eng` | Mixed (default) |

## OCR Quality Tips

- 照明が均一な環境で撮影
- レシートを平らに伸ばす（しわを最小限に）
- カメラを真上から（斜めに撮らない）
- 解像度は 300dpi 以上推奨
- 感熱紙のレシートは早めに（色あせる前に）

## Output Format

```
🧾 レシート読み取り結果
================================
店名:   セブンイレブン 渋谷店
日付:   2026-03-10
通貨:   JPY
信頼度: 87.3%

商品 (3件):
  1. おにぎり 鮭                     ¥150
  2. サントリー天然水 500ml           ¥110
  3. ファミチキ                       ¥220

合計: ¥480

DB保存完了 (receipt_id=12)
  3件を purchase_history に登録
```

## Error Handling

- OCR信頼度が50%未満の場合: 「読み取り精度が低いです。撮り直すか手動入力をお勧めします」
- テキストが空の場合: 「文字を検出できませんでした。画像を確認してください」
- Tesseract未インストール: インストール手順を案内
