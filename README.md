# Personal Context Engine

**Give AI everything about you. A local-first personal data platform.**

Personal Context Engine (PCE) is an open-source data platform that structures your personal life data — possessions, purchases, receipts, consumables — so AI agents can access and analyze it across domains.

AI is already powerful enough. The problem is that AI doesn't know *you*. PCE bridges this gap.

> **Design philosophy**: Your data stays on your machine. PCE uses SQLite (a single file) with zero cloud dependencies. For remote access, use [Tailscale](https://tailscale.com/) or similar mesh VPN to securely reach your local machine from anywhere.

---

## Features

| Skill | Description | Status |
|-------|-------------|--------|
| **possession-manager** | Item registration, search, consumable tracking & replenishment alerts | v0.2 |
| **purchase-importer** | Plugin-based CSV import (Amazon, eBay, Walmart, Rakuten, Shopify, credit cards) | v0.2 |
| **receipt-scanner** | Receipt OCR with Tesseract (Japanese + English, local processing) | v0.2 |
| **video-cataloger** | Catalog items from video via ffmpeg + Whisper + vision AI | v0.2 |
| **life-dashboard** | Cross-domain analysis, weekly reports, automated heartbeat jobs | v0.3 |

## Quick Start

### Prerequisites

- Python 3.10+
- SQLite 3 (usually pre-installed)
- Optional: [OpenClaw](https://openclaw.ai) for natural language interface

### Optional Dependencies

| Dependency | Required For | Install |
|-----------|-------------|---------|
| Tesseract OCR | receipt-scanner | `brew install tesseract tesseract-lang` / `apt install tesseract-ocr` |
| ffmpeg | video-cataloger | [ffmpeg.org](https://ffmpeg.org/download.html) |
| openai-whisper | video audio transcription | `pip install -r requirements-video.txt` (includes PyTorch, ~2GB) |

### Installation

```bash
git clone https://github.com/wat-hiroaki/personal-context-engine.git
cd personal-context-engine

# Core + receipt OCR dependencies
pip install -r requirements.txt

# Video cataloger (optional, large install)
# pip install -r requirements-video.txt

chmod +x setup.sh
./setup.sh
```

### Try with Sample Data

```bash
# Import sample Amazon JP orders
python3 scripts/import_ec_plugins.py examples/sample_amazon_jp.csv

# Import sample credit card statement
python3 scripts/import_ec_plugins.py examples/sample_credit_card.csv

# Bootstrap your possessions interactively
python3 scripts/bootstrap.py
```

### With OpenClaw (optional)

If you have OpenClaw installed, you can use natural language:

```
Register my protein powder. SAVAS whey, bought on Amazon for 2980 yen.
```

Or in Japanese:

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

## Usage

### Import Purchase History (CSV)

```bash
# Auto-detect EC site format
python3 scripts/import_ec_plugins.py orders.csv

# Specify format
python3 scripts/import_ec_plugins.py orders.csv --format amazon_us

# List all supported formats
python3 scripts/import_ec_plugins.py --list-formats
```

**Supported formats**: Amazon (JP/US), Rakuten, eBay, Walmart, Shopify, generic credit card statements.

Add your own format by editing `config/ec_formats.json` — no code changes needed.

### Scan Receipts

```bash
# Japanese + English (default)
python3 scripts/import_receipt.py receipt.jpg

# English only
python3 scripts/import_receipt.py receipt.jpg --lang en
```

Uses Tesseract OCR locally — no API calls, no data sent externally.

### Catalog Items from Video

```bash
# Process video (extract frames + transcribe audio)
python3 scripts/process_video.py room_tour.mp4

# Custom settings
python3 scripts/process_video.py room_tour.mp4 --interval 3 --whisper-model medium
```

### Bootstrap Your Possessions

```bash
# Interactive wizard — walk through categories one by one
python3 scripts/bootstrap.py

# Non-interactive (pipe from file or other tools)
echo "kitchen:Rice cooker
supplement:Protein / SAVAS
electronics:MacBook Pro" | python3 scripts/bootstrap.py --non-interactive
```

### Natural Language (via OpenClaw)

```
"List everything in the kitchen"
"I opened the protein powder"
"What's running low?"
"Show me this month's spending by category"
"What should I buy this week?"
```

## Directory Structure

```
personal-context-engine/
├── skills/                     # OpenClaw skill definitions
│   ├── possession-manager/
│   ├── purchase-importer/
│   ├── receipt-scanner/
│   ├── video-cataloger/
│   └── life-dashboard/
├── scripts/                    # Python scripts
│   ├── common.py               # Shared utilities (encoding, parsing, config)
│   ├── import_ec_plugins.py    # Plugin-based EC importer
│   ├── import_receipt.py       # Receipt OCR
│   ├── process_video.py        # Video frame extraction + Whisper
│   ├── bootstrap.py            # Interactive possession bootstrap wizard
│   ├── import_amazon.py        # Amazon CSV (legacy)
│   ├── import_rakuten.py       # Rakuten CSV (legacy)
│   └── import_csv_generic.py   # Generic CSV (legacy)
├── examples/                   # Sample CSV files for testing
├── schema/                     # SQLite schema & migrations
├── config/                     # Configuration files
│   ├── pce.json                # Main configuration
│   └── ec_formats.json         # EC site column mappings (extensible)
├── tests/                      # pytest test suite
├── .github/workflows/ci.yml    # GitHub Actions CI
├── setup.sh                    # Installation script
├── requirements.txt            # Python deps (OCR)
└── requirements-video.txt      # Python deps (video, includes PyTorch)
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

## Privacy & Security

PCE is designed with a **local-first** architecture:

- **Storage**: All data in a single SQLite file on your machine. No cloud database, no sync service.
- **Receipt OCR**: Tesseract runs 100% locally. No images are sent to external APIs.
- **Video frames**: Automatically deleted after analysis for privacy protection.
- **Database permissions**: Set to `chmod 600` (owner-only).
- **Backup**: Copy `personal.db` — that's it.

### What does go external

When you use PCE through OpenClaw, your **natural language queries** (not the raw database) are sent to the LLM provider configured in OpenClaw (Claude, GPT, etc.). This is standard OpenClaw behavior, not specific to PCE. The database itself never leaves your machine.

### Remote Access

For accessing your data from other devices (e.g., checking your shopping list on your phone), we recommend [Tailscale](https://tailscale.com/) or a similar mesh VPN to securely connect to your local machine. This preserves the local-first design while giving you access from anywhere on your private network.

## Roadmap

| Phase | Content | Status |
|-------|---------|--------|
| v0.1 | DB schema + possession-manager + basic CSV import | Done |
| v0.2 | Plugin EC importer + receipt OCR + video-cataloger + Whisper | Done |
| v0.3 | life-dashboard + heartbeat automation | Done |
| v1.0 | Tests, CI, documentation, public release | Done |
| v1.x+ | MCP server / EC auto-order / semantic search | Future |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check scripts/ tests/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)

---

**Personal Context Engine — Give AI everything about you. That's the data platform for it.**
