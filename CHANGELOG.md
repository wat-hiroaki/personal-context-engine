# Changelog

## [1.0.0] - 2026-03-11

### Added
- `pyproject.toml` for standard Python packaging
- `scripts/common.py` — shared utilities (encoding detection, price/date parsing, config loading)
- `tests/conftest.py` — pytest fixtures for database testing
- `schema/migrate_v1.0.sql` — adds `image_hash` column, removes restrictive source CHECK constraint
- `examples/` directory with sample CSV files for quick testing
- `CHANGELOG.md`
- Standalone usage documentation in README (no OpenClaw required)
- `scripts/bootstrap.py` documented in README

### Changed
- `raw_data` field now stores JSON instead of comma-separated key=value pairs
- Receipt duplicate detection uses dedicated `image_hash` column (SHA-256) instead of embedding hash in `image_path`
- `setup.sh` is now compatible with bash 3.x (macOS default)
- All scripts use shared `common.py` module for encoding detection and config loading
- `purchase_history.source` no longer has a restrictive CHECK constraint — any source string is accepted
- CI validates all scripts including `common.py` and `bootstrap.py`

### Fixed
- Missing `tests/conftest.py` — tests now actually run
- `setup.sh` bash associative array syntax incompatible with bash 3.x on macOS
- CI missing `bootstrap.py` and `import_receipt.py` from syntax validation

## [0.3.0] - 2026-03-10

### Added
- `skills/life-dashboard/` — cross-domain analysis, weekly reports, automated heartbeat jobs
- Spending analysis queries (by source, category, monthly trend)
- Consumable prediction and purchase recommendation queries
- Heartbeat job configurations (daily consumable check, weekly report, purchase suggestions)

## [0.2.0] - 2026-03-10

### Added
- `scripts/import_ec_plugins.py` — plugin-based EC CSV importer with auto-detection
- `config/ec_formats.json` — extensible column mappings for 7 EC site formats
- `scripts/import_receipt.py` — receipt OCR with Tesseract (Japanese + English)
- `scripts/process_video.py` — video frame extraction + Whisper transcription
- `schema/migrate_v0.2.sql` — receipt_scans, receipt_items, video_sessions tables
- `scripts/bootstrap.py` — interactive data bootstrap wizard
- Multi-currency support with automatic symbol detection
- Image preprocessing pipeline (grayscale, denoise, threshold, deskew)

## [0.1.0] - 2026-03-10

### Added
- Initial SQLite schema (possessions, purchase_history, consumption_log)
- `skills/possession-manager/` — item registration, search, consumable tracking
- `skills/purchase-importer/` — CSV import for Amazon and Rakuten
- `scripts/import_amazon.py` — Amazon.co.jp CSV importer
- `scripts/import_rakuten.py` — Rakuten CSV importer
- `scripts/import_csv_generic.py` — generic credit card CSV importer
- Duplicate detection by order_id and composite key
- Japanese and English column name auto-detection
