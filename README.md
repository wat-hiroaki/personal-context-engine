# Personal Context Engine

**AIに自分の全てを渡すための個人データ基盤**

Personal Context Engine (PCE) is an open-source data platform that structures your personal life data so AI agents can access and analyze it across domains.

AI is already powerful enough. The problem is that AI doesn't know *you*. PCE bridges this gap.

---

## Features

| Skill | Description | Status |
|-------|-------------|--------|
| **possession-manager** | Item registration, search, consumable tracking & replenishment alerts | v0.1 |
| **purchase-importer** | Plugin-based CSV import (Amazon, eBay, Walmart, Rakuten, Shopify, credit cards) | v0.2 |
| **receipt-scanner** | Receipt OCR with Tesseract (Japanese + English, local processing) | v0.2 |
| **video-cataloger** | Catalog items from video via ffmpeg + Whisper + vision AI | v0.2 |
| **life-dashboard** | Cross-domain analysis, weekly reports, automated heartbeat jobs | v0.3 |

## Quick Start

### Prerequisites

- [OpenClaw](https://openclaw.dev) installed and running
- Python 3.10+
- SQLite 3 (usually pre-installed)

### Optional Dependencies

| Dependency | Required For | Install |
|-----------|-------------|---------|
| ffmpeg | video-cataloger | [ffmpeg.org](https://ffmpeg.org/download.html) |
| Tesseract OCR | receipt-scanner | `brew install tesseract tesseract-lang` / `apt install tesseract-ocr` |
| openai-whisper | video audio transcription | `pip install openai-whisper` |

### Installation

```bash
git clone https://github.com/wat-hiroaki/personal-context-engine.git
cd personal-context-engine
pip install -r requirements.txt   # Optional: for OCR & video features
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
               └┬──┬──┬──┬──┬───┘
                │  │  │  │  │
     ┌──────────┘  │  │  │  └──────────┐
     ▼             ▼  ▼  ▼             ▼
┌──────────┐┌────────┐┌───────┐┌────────┐┌──────────┐
│possession││purchase││receipt││ video  ││  life-   │
│ -manager ││-import ││scanner││catalog ││dashboard │
└────┬─────┘└───┬────┘└──┬────┘└───┬────┘└────┬─────┘
     │          │        │         │          │
     └──────────▼────────▼─────────▼──────────┘
          ┌──────────────────────────┐
          │   SQLite (personal.db)    │
          └──────────────────────────┘
```

All data stays on your local machine. No data is sent to external servers.

## Usage

### Import Purchase History (CSV)

```bash
# Auto-detect EC site format
python3 ~/.openclaw/workspace/scripts/import_ec_plugins.py orders.csv

# Specify format
python3 ~/.openclaw/workspace/scripts/import_ec_plugins.py orders.csv --format amazon_us

# List all supported formats
python3 ~/.openclaw/workspace/scripts/import_ec_plugins.py --list-formats
```

**Supported formats**: Amazon (JP/US), Rakuten, eBay, Walmart, Shopify, generic credit card statements.

Add your own format by editing `config/ec_formats.json` — no code changes needed.

### Scan Receipts

```bash
# Japanese + English (default)
python3 ~/.openclaw/workspace/scripts/import_receipt.py receipt.jpg

# English only
python3 ~/.openclaw/workspace/scripts/import_receipt.py receipt.jpg --lang en

# Japanese only
python3 ~/.openclaw/workspace/scripts/import_receipt.py receipt.jpg --lang ja
```

Uses Tesseract OCR locally — no API calls, no data sent externally.

### Catalog Items from Video

```bash
# Process video (extract frames + transcribe audio)
python3 ~/.openclaw/workspace/scripts/process_video.py room_tour.mp4

# Custom settings
python3 ~/.openclaw/workspace/scripts/process_video.py room_tour.mp4 --interval 3 --whisper-model medium

# Clean up frames after done
python3 ~/.openclaw/workspace/scripts/process_video.py --cleanup /tmp/pce_video_xxx/frames
```

### Natural Language (via OpenClaw)

```
「キッチンにあるもの一覧」
「プロテイン開けた」
「そろそろなくなるものある？」
「今月の支出レポート見せて」
「来週買うべきものリスト」
"Show me this month's spending by category"
```

## Directory Structure

```
~/.openclaw/workspace/
├── skills/
│   ├── possession-manager/SKILL.md
│   ├── purchase-importer/SKILL.md
│   ├── receipt-scanner/SKILL.md
│   ├── video-cataloger/SKILL.md
│   └── life-dashboard/SKILL.md
├── scripts/
│   ├── import_ec_plugins.py      # Plugin-based EC importer
│   ├── import_amazon.py          # Amazon CSV (legacy)
│   ├── import_rakuten.py         # Rakuten CSV (legacy)
│   ├── import_csv_generic.py     # Generic CSV (legacy)
│   ├── import_receipt.py         # Receipt OCR
│   ├── process_video.py          # Video frame extraction + Whisper
│   └── process_video.sh          # Shell wrapper for ffmpeg
├── data/
│   └── personal.db
└── config/
    ├── pce.json                  # Main configuration
    └── ec_formats.json           # EC site column mappings
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `possessions` | Items you own (name, category, brand, location, consumable tracking) |
| `purchase_history` | Purchase records from EC sites, credit cards, receipts |
| `consumption_log` | Consumable usage events (opened, low, empty, replaced) |
| `receipt_scans` | OCR scan metadata (store, total, confidence, raw text) |
| `receipt_items` | Individual items extracted from receipts |
| `video_sessions` | Video processing session metadata |

## Roadmap

| Phase | Content | Status |
|-------|---------|--------|
| v0.1 | DB schema + possession-manager + basic CSV import | Done |
| v0.2 | Plugin EC importer + receipt OCR + video-cataloger + Whisper | Current |
| v0.3 | life-dashboard + heartbeat automation | Current |
| v1.0 | Documentation + setup.sh + public release | Planned |
| v1.x+ | MCP server / EC auto-order / semantic search / i18n | Future |

## Privacy & Security

- **Local-first**: All data stored in SQLite on your machine — no cloud sync
- **No external API for OCR**: Tesseract runs locally
- **Video frames auto-deleted**: Extracted images removed after analysis
- **Database permissions**: `chmod 600` (owner-only access)
- **Backup**: Just copy `personal.db`

## Extending

### Add a New EC Format

Edit `config/ec_formats.json`:

```json
{
  "my_store": {
    "name": "My Store",
    "source_key": "my_store",
    "columns": {
      "item_name": ["Product", "Name"],
      "price": ["Price", "Total"],
      "purchase_date": ["Date"],
      "order_id": ["Order #"]
    },
    "date_formats": ["%Y-%m-%d"]
  }
}
```

### Add a New Skill

Create `skills/my-skill/SKILL.md` following the existing format.

## Contributing

Contributions welcome! Please:

- Follow existing SKILL.md format for new skills
- Provide migration scripts for schema changes
- Document any privacy-impacting changes
- Write PR descriptions in Japanese or English

## License

[MIT](LICENSE)

---

**Personal Context Engine — Give AI everything about you. That's the data platform for it.**
