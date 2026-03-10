# Life Dashboard

全ライフデータを横断的に分析し、インサイトを提供する統合スキル。

## Trigger Phrases

- 「今月の支出レポートを見せて」
- 「健康関連の出費はいくら？」
- 「来週買うべきものリスト」
- 「今週のライフレポートを作って」
- "Show me this month's spending report"
- "What should I buy this week?"

## Data Sources

| データ | ソース | 統合方法 |
|--------|--------|---------|
| 所有物・購入履歴 | PCE (SQLite) | 直接クエリ |
| レシートスキャン | PCE (SQLite) | 直接クエリ |
| 健康データ | Google Fit / Apple Health | 既存スキル or エクスポート |
| 食事ログ | OpenClawスキル | 既存データを参照 |
| 筋トレログ | ユーザー記録 | 既存データを参照 |
| 習慣チェックリスト | ユーザー記録 | 既存データを参照 |

## Analysis Commands

### 支出分析

```sql
-- 今月の支出サマリー（ソース別）
SELECT
    source,
    COUNT(*) AS items,
    SUM(price) AS total,
    currency
FROM purchase_history
WHERE purchase_date >= date('now', 'start of month')
GROUP BY source, currency
ORDER BY total DESC;

-- カテゴリ別支出
SELECT
    COALESCE(ph.category, p.category, 'uncategorized') AS category,
    COUNT(*) AS items,
    SUM(ph.price) AS total
FROM purchase_history ph
LEFT JOIN possessions p ON ph.possession_id = p.id
WHERE ph.purchase_date >= date('now', 'start of month')
GROUP BY category
ORDER BY total DESC;

-- 月別支出トレンド（過去6ヶ月）
SELECT
    strftime('%Y-%m', purchase_date) AS month,
    COUNT(*) AS items,
    SUM(price) AS total
FROM purchase_history
WHERE purchase_date >= date('now', '-6 months')
GROUP BY month
ORDER BY month;
```

### 消耗品予測

```sql
-- 今週補充が必要なアイテム
SELECT
    p.name,
    p.brand,
    p.last_replenished,
    p.estimated_lifespan_days,
    date(p.last_replenished, '+' || p.estimated_lifespan_days || ' days') AS estimated_empty,
    CAST(julianday(date(p.last_replenished, '+' || p.estimated_lifespan_days || ' days')) - julianday('now') AS INTEGER) AS days_remaining
FROM possessions p
WHERE p.is_consumable = 1
  AND p.last_replenished IS NOT NULL
  AND julianday(date(p.last_replenished, '+' || p.estimated_lifespan_days || ' days')) - julianday('now') <= 7
ORDER BY days_remaining ASC;
```

### 購入推奨リスト

```sql
-- 過去の購入パターンから定期購入候補を抽出
SELECT
    ph.item_name,
    COUNT(*) AS purchase_count,
    AVG(ph.price) AS avg_price,
    MAX(ph.purchase_date) AS last_purchased,
    CAST(julianday('now') - julianday(MAX(ph.purchase_date)) AS INTEGER) AS days_since_last
FROM purchase_history ph
WHERE ph.purchase_date >= date('now', '-1 year')
GROUP BY ph.item_name
HAVING purchase_count >= 2
ORDER BY days_since_last DESC;
```

### 所有物統計

```sql
-- カテゴリ別所有物数
SELECT category, COUNT(*) AS count
FROM possessions
GROUP BY category
ORDER BY count DESC;

-- 場所別所有物数
SELECT location, COUNT(*) AS count
FROM possessions
WHERE location IS NOT NULL
GROUP BY location
ORDER BY count DESC;

-- 最近登録されたアイテム
SELECT name, brand, category, created_at
FROM possessions
ORDER BY created_at DESC
LIMIT 10;
```

## Cross-Domain Analysis

以下のような横断クエリに応答する:

| ユーザーの質問 | 分析ロジック |
|--------------|------------|
| 「トレーニング強度上げてるけどプロテイン在庫大丈夫？」 | 筋トレログ + 消耗品DB |
| 「今月の健康関連支出はいくら？」 | purchase_history WHERE category IN ('supplement', 'food') |
| 「来週買うべきものリスト」 | 消耗品予測 + 定期購入パターン |
| 「最近の無駄遣い教えて」 | purchase_history の高額・低頻度アイテム |
| 「キッチンの整理をしたい」 | possessions WHERE location LIKE '%キッチン%' |

## Heartbeat Jobs

### 消耗品チェック（毎日 9:00）

```
消耗品の在庫チェックを実行して。
なくなりそうなものを以下のフォーマットで教えて:

⚠️ 補充が必要:
1. [アイテム名] — 残り約X日
2. ...

✅ まだ大丈夫:
- [アイテム名] — 残り約X日
```

### 週次ライフレポート（毎週日 20:00）

```
今週のライフレポートを作成して。以下を含めて:

📊 今週のサマリー
- 購入件数・金額
- 新規登録アイテム
- 消費した消耗品
- 来週の補充予定

💰 支出内訳（カテゴリ別）

📦 在庫アラート（なくなりそうなもの）
```

### 購入提案（毎週土 10:00）

```
消費パターンと在庫から今週の購入推奨リストを作って。
過去の購入履歴から定期的に買っているものも含めて。

フォーマット:
🛒 購入推奨リスト
- [ ] [アイテム名] — 理由 (推定価格: ¥X,XXX)
```

## Heartbeat Configuration

```json
{
  "pce-consumable-check": {
    "schedule": "0 9 * * *",
    "prompt": "消耗品の在庫チェックを実行して。なくなりそうなものを教えて。"
  },
  "pce-weekly-report": {
    "schedule": "0 20 * * 0",
    "prompt": "今週のライフダッシュボードレポートを作成して。"
  },
  "pce-purchase-suggest": {
    "schedule": "0 10 * * 6",
    "prompt": "消費パターンと在庫から今週の購入推奨を作って。"
  }
}
```

## Output Format

### 週次レポート例

```
📊 Weekly Life Report (2026-03-02 〜 2026-03-08)
=============================================

💰 支出サマリー
  Amazon:      ¥12,340 (5件)
  Rakuten:     ¥3,200  (2件)
  Receipt:     ¥8,750  (12件)
  合計:        ¥24,290

📦 新規登録アイテム
  - USB-C ケーブル (electronics)
  - 洗濯用洗剤 アタック (consumable)

🔄 消費済み
  - プロテイン SAVAS → empty (3/5)

⚠️ 来週の補充予定
  1. シャンプー — 残り約3日
  2. ボディソープ — 残り約5日

📈 月間トレンド
  2月: ¥89,200 → 3月(途中): ¥24,290
```
