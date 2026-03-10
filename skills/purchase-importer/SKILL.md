# Purchase Importer

ECサイトやクレジットカード明細のCSVを読み取り、purchase_historyにインポートするスキル。

## Trigger Phrases

- 「Amazonの購入履歴をインポートして」
- 「楽天の注文CSVを取り込んで」
- 「クレカ明細を登録して」
- 「CSVから購入履歴を読み込んで」

## Database

SQLite database at `~/.openclaw/workspace/data/personal.db`

## Supported Formats

| ソース | フォーマット | 取得方法 |
|--------|-------------|---------|
| Amazon.co.jp | CSV（注文履歴レポート） | アカウント → 注文履歴 → レポート |
| 楽天市場 | CSV（購入履歴） | my Rakuten → 購入履歴 → CSVダウンロード |
| クレジットカード | CSV（各社明細） | カード会社Web明細 → CSVダウンロード |

## Import Flow

1. ユーザーがCSVファイルパスを伝える
2. ファイルの存在を確認
3. ソースを自動判定（ファイル名やヘッダーから推測、不明ならユーザーに確認）
4. 対応するPythonスクリプトを実行:
   - Amazon: `~/.openclaw/workspace/scripts/import_amazon.py`
   - 楽天: `~/.openclaw/workspace/scripts/import_rakuten.py`
   - その他: `~/.openclaw/workspace/scripts/import_csv_generic.py`
5. インポート結果を報告

## Script Execution

```bash
# Amazon
python3 ~/.openclaw/workspace/scripts/import_amazon.py <csv_path> <db_path>

# Rakuten
python3 ~/.openclaw/workspace/scripts/import_rakuten.py <csv_path> <db_path>

# Generic CSV
python3 ~/.openclaw/workspace/scripts/import_csv_generic.py <csv_path> <db_path> --source <source_name>
```

## Duplicate Prevention

- `order_id` をキーとして重複チェック
- `order_id` がないソース: `source + item_name + purchase_date + price` の組み合わせで重複チェック

## Character Encoding

日本語CSVの文字コードは以下の順序で自動判定:
`utf-8-sig` → `utf-8` → `shift_jis` → `cp932`

判定失敗時はユーザーにエンコーディングを確認する。

## Possession Linking

インポート後、既存の possessions レコードと名前が類似するアイテムを提案:

```sql
SELECT id, name, brand FROM possessions
WHERE name LIKE '%' || ? || '%' OR brand LIKE '%' || ? || '%';
```

ユーザーが確認したら `purchase_history.possession_id` を更新する。

## Output Format

```
📦 インポート完了（Amazon）
- 取り込み: 42件
- スキップ（重複）: 3件
- エラー: 0件
- 期間: 2025-01-01 〜 2026-03-01
- 合計金額: ¥187,320
```
