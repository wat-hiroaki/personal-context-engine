---
name: possession-manager
description: Register, search, update, and track personal possessions with consumable replenishment alerts
version: 0.2.0
triggers:
  - pattern: "(register|add|bought|buy|購入|登録|買った)"
  - pattern: "(list|search|show|一覧|検索|リスト)"
  - pattern: "(opened|empty|low|開けた|なくなった)"
  - pattern: "(replenish|restock|補充|なくなるもの)"
tools:
  - sqlite3
---

# Possession Manager

所有物の登録・検索・更新・削除、および消耗品の残量追跡と補充リマインドを行う中核スキル。

## Trigger Phrases

- 「XXXを登録して」「XXXを買った」→ アイテム登録
- 「キッチンにあるもの一覧」「電子機器リスト」→ 検索
- 「プロテイン開けた」「XXXがなくなった」→ 消費ログ記録
- 「そろそろなくなるものある？」→ 消耗品チェック

## Database

SQLite database at `~/.openclaw/workspace/data/personal.db`

## Commands

### Register Item

ユーザーがアイテム名を伝えたら:

1. カテゴリを自動分類（確信がない場合はユーザーに確認）
   - categories: `electronics`, `clothing`, `consumable`, `food`, `supplement`, `furniture`, `kitchen`, `bathroom`, `office`, `other`
2. 消耗品かどうか判定（食品・サプリ・洗剤・日用品等は自動で消耗品判定）
3. 消耗品の場合: `config/pce.json` の `consumable_defaults` から推定消費日数を設定
4. SQLiteにINSERTし、登録完了を報告

```sql
INSERT INTO possessions (name, category, brand, purchase_date, purchase_price, purchase_source, location, condition, is_consumable, estimated_lifespan_days, last_replenished, notes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
```

### Search Items

ユーザーのクエリに応じてSELECTする:

```sql
-- カテゴリ検索
SELECT * FROM possessions WHERE category = ?;

-- 場所検索
SELECT * FROM possessions WHERE location LIKE ?;

-- フリーテキスト検索
SELECT * FROM possessions WHERE name LIKE ? OR brand LIKE ? OR notes LIKE ?;
```

結果はテーブル形式で見やすく表示する。

### Update Item

```sql
UPDATE possessions SET {column} = ? WHERE id = ?;
```

### Delete Item

```sql
DELETE FROM possessions WHERE id = ?;
```

削除前に必ずユーザーに確認する。

### Log Consumption

消耗品の使用状況を記録する:

```sql
INSERT INTO consumption_log (possession_id, event_type, notes)
VALUES (?, ?, ?);
```

event_type: `opened`, `half_used`, `low`, `empty`, `replaced`, `disposed`

- 「開けた」→ `opened` + `last_replenished` を今日に更新
- 「半分くらい」→ `half_used`
- 「もうすぐなくなる」→ `low`
- 「なくなった」→ `empty`
- 「新しいのに替えた」→ `replaced` + `last_replenished` を今日に更新
- 「捨てた」→ `disposed`

### Consumable Check (補充予測)

消耗品の補充時期を予測する:

```sql
SELECT
    p.id,
    p.name,
    p.brand,
    p.last_replenished,
    p.estimated_lifespan_days,
    date(p.last_replenished, '+' || p.estimated_lifespan_days || ' days') AS estimated_empty_date,
    julianday(date(p.last_replenished, '+' || CAST(p.estimated_lifespan_days * 0.8 AS INTEGER) || ' days')) - julianday('now') AS days_until_alert
FROM possessions p
WHERE p.is_consumable = 1
  AND p.last_replenished IS NOT NULL
  AND julianday(date(p.last_replenished, '+' || CAST(p.estimated_lifespan_days * 0.8 AS INTEGER) || ' days')) <= julianday('now')
ORDER BY days_until_alert ASC;
```

#### 補充予測アルゴリズム

1. **初回**: `estimated_lifespan_days` のデフォルト値を使用（pce.json の consumable_defaults）
2. **学習**: `consumption_log` の実績データから実際の消費サイクルを計算

```sql
-- 実績ベースの消費サイクル計算
SELECT
    p.id,
    p.name,
    AVG(julianday(cl2.logged_at) - julianday(cl1.logged_at)) AS avg_cycle_days
FROM consumption_log cl1
JOIN consumption_log cl2 ON cl1.possession_id = cl2.possession_id
    AND cl2.event_type IN ('empty', 'replaced')
    AND cl1.event_type = 'opened'
    AND cl2.logged_at > cl1.logged_at
JOIN possessions p ON p.id = cl1.possession_id
GROUP BY p.id;
```

3. **アラート**: `last_replenished + 推定日数 × 0.8 < 今日` の場合に通知（20%の余裕）

## Output Format

アイテム登録時:
```
✅ 登録完了
名前: プロテイン SAVAS ホエイ
カテゴリ: supplement
ブランド: SAVAS
購入元: Amazon
価格: ¥2,980
消耗品: はい（推定60日で消費）
```

消耗品チェック時:
```
⚠️ そろそろ補充が必要なアイテム:
1. プロテイン SAVAS ホエイ — 残り約5日（3/15頃にはなくなる見込み）
2. シャンプー — 残り約8日
```
