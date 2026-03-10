# Personal Context Engine

**AIに自分の全てを渡すための個人データ基盤**

Personal Context Engine (PCE) は、個人の生活データを構造化し、AIエージェントが横断的にアクセス・分析できるようにするオープンソースのデータ基盤です。

AIの能力は既に十分高い。問題はAIが「あなた」を知らないこと。PCEはこのギャップを埋めます。

---

## Features

- **possession-manager** — 所有物の登録・検索・更新・削除、消耗品の残量追跡と補充リマインド
- **purchase-importer** — Amazon・楽天・クレカ明細のCSVインポート
- **video-cataloger** — 動画/写真からの所有物一括カタログ化 *(v0.2)*
- **life-dashboard** — 全ライフデータの横断分析 *(v0.3)*

## Quick Start

### Prerequisites

- [OpenClaw](https://openclaw.dev) installed and running
- Python 3.10+
- SQLite 3 (usually pre-installed)
- ffmpeg (optional, for video-cataloger)

### Installation

```bash
git clone https://github.com/wat-hiroaki/personal-context-engine.git
cd personal-context-engine
chmod +x setup.sh
./setup.sh
```

### Verify

Tell OpenClaw:

```
プロテインを登録して。SAVASのホエイ、Amazonで2980円で買った
```

## Architecture

```
┌───────────────────────────────────────────────┐
│  Chat Interface (WhatsApp / Telegram / etc.)  │
└───────────────────────┬───────────────────────┘
                        │
               ┌────────▼────────┐
               │  OpenClaw Gateway │
               └──┬──┬──┬──┬────┘
                  │  │  │  │
        ┌─────────┘  │  │  └─────────┐
        ▼            ▼  ▼            ▼
  ┌───────────┐┌────────┐┌────────┐┌──────────┐
  │ possession ││purchase││ video  ││  life-   │
  │  -manager  ││-import ││catalog ││dashboard │
  └─────┬─────┘└───┬────┘└───┬────┘└────┬─────┘
        │          │         │          │
        └──────────▼─────────▼──────────┘
          ┌──────────────────────┐
          │  SQLite (personal.db) │
          └──────────────────────┘
```

All data stays on your local machine. No data is sent to external servers.

## Directory Structure

```
~/.openclaw/workspace/
├── skills/
│   ├── possession-manager/SKILL.md
│   ├── purchase-importer/SKILL.md
│   ├── video-cataloger/SKILL.md
│   └── life-dashboard/SKILL.md
├── scripts/
│   ├── import_amazon.py
│   ├── import_rakuten.py
│   ├── import_csv_generic.py
│   └── process_video.sh
├── data/
│   └── personal.db
└── config/
    └── pce.json
```

## CSV Import

### Amazon

1. Go to Amazon → Account → Order History → Download Reports
2. Download CSV
3. Run: `python3 ~/.openclaw/workspace/scripts/import_amazon.py <csv_path>`

### Rakuten

1. Go to my Rakuten → Purchase History → CSV Download
2. Run: `python3 ~/.openclaw/workspace/scripts/import_rakuten.py <csv_path>`

### Credit Card / Other

```bash
python3 ~/.openclaw/workspace/scripts/import_csv_generic.py <csv_path> --source credit_card
```

## Roadmap

| Phase | Content | Status |
|-------|---------|--------|
| v0.1 | DB schema + possession-manager + purchase-importer | Current |
| v0.2 | video-cataloger + Whisper integration | Planned |
| v0.3 | life-dashboard + heartbeat automation | Planned |
| v1.0 | Documentation + setup.sh + public release | Planned |
| v1.x+ | Receipt OCR / MCP server / EC auto-order / i18n | Future |

## Privacy & Security

- All data is stored locally in SQLite — no cloud sync
- Video frames are auto-deleted after analysis
- Database file permission set to `600` (owner-only)
- Backup = copy `personal.db`

## Contributing

Contributions welcome! Please:

- Follow existing SKILL.md format for new skills
- Provide migration scripts for schema changes
- Document any privacy-impacting changes
- Write PR descriptions in Japanese or English

## License

[MIT](LICENSE)

---

**Personal Context Engine — AIに自分の全てを渡せ。そのためのデータ基盤。**
