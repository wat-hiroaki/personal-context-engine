# Purchase Importer

ECサイトやクレジットカード明細のCSVを読み取り、purchase_historyにインポートするスキル。
プラグイン方式で任意のECサイトに対応。

## Trigger Phrases

- 「Amazonの購入履歴をインポートして」
- 「楽天の注文CSVを取り込んで」
- 「クレカ明細を登録して」
- 「CSVから購入履歴を読み込んで」
- "Import my eBay purchase history"
- "Load Walmart CSV"

## Database

SQLite database at `~/.openclaw/workspace/data/personal.db`

## Supported Formats

Plugin definitions in `config/ec_formats.json`:

| Format Key | Name | Source |
|-----------|------|--------|
| `amazon_jp` | Amazon.co.jp | Japanese Amazon |
| `amazon_us` | Amazon.com | US Amazon |
| `rakuten` | Rakuten | 楽天市場 |
| `ebay` | eBay | eBay |
| `walmart` | Walmart | Walmart |
| `shopify` | Shopify Order Export | Shopify stores |
| `generic_credit_card` | Generic Credit Card | Any credit card CSV |

### Adding New Formats

Edit `config/ec_formats.json` and add a new entry under `formats`:

```json
{
  "my_store": {
    "name": "My Store",
    "source_key": "my_store",
    "encoding_hint": "utf-8",
    "columns": {
      "item_name": ["Product Name", "Item"],
      "price": ["Price", "Amount"],
      "purchase_date": ["Date", "Order Date"],
      "order_id": ["Order #"],
      "quantity": ["Qty"],
      "category": ["Category"]
    },
    "date_formats": ["%Y-%m-%d", "%m/%d/%Y"]
  }
}
```

No code changes required — the plugin importer auto-detects columns.

## Import Flow

1. ユーザーがCSVファイルパスを伝える
2. ファイルの存在を確認
3. フォーマットを自動判定（ヘッダーのカラム名マッチング）
   - 自動判定失敗時: ユーザーに確認 or `generic_credit_card` にフォールバック
4. `import_ec_plugins.py` を実行
5. インポート結果を報告

## Script Execution

```bash
# Auto-detect format
python3 ~/.openclaw/workspace/scripts/import_ec_plugins.py <csv_path>

# Specify format explicitly
python3 ~/.openclaw/workspace/scripts/import_ec_plugins.py <csv_path> --format amazon_jp

# List available formats
python3 ~/.openclaw/workspace/scripts/import_ec_plugins.py --list-formats

# Legacy scripts (still available for backward compatibility)
python3 ~/.openclaw/workspace/scripts/import_amazon.py <csv_path>
python3 ~/.openclaw/workspace/scripts/import_rakuten.py <csv_path>
python3 ~/.openclaw/workspace/scripts/import_csv_generic.py <csv_path> --source credit_card
```

## Duplicate Prevention

- `order_id` をキーとして重複チェック
- `order_id` がないソース: `source + item_name + purchase_date + price` の組み合わせで重複チェック

## Character Encoding

自動判定順序: `utf-8-sig` → `utf-8` → `shift_jis` → `cp932` → `iso-8859-1` → `latin-1`

`chardet` がインストールされている場合はフォールバックとして使用。

## Multi-Currency Support

通貨は以下の記号から自動判定:
- ¥ / ￥ → JPY
- $ → USD
- € → EUR
- £ → GBP
- ₩ → KRW

## Output Format

```
📦 Import complete (Amazon.co.jp)
  Format:   amazon_jp (auto-detected)
  Imported: 42
  Skipped:  3 (duplicate)
  Errors:   0
```
