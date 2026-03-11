# Sample Data

These CSV files are for testing the import scripts. All data is fictional.

## Usage

```bash
# Import Japanese Amazon orders
python3 scripts/import_ec_plugins.py examples/sample_amazon_jp.csv --format amazon_jp

# Import US Amazon orders
python3 scripts/import_ec_plugins.py examples/sample_amazon_us.csv --format amazon_us

# Import credit card statement
python3 scripts/import_ec_plugins.py examples/sample_credit_card.csv

# Or use the legacy importers
python3 scripts/import_amazon.py examples/sample_amazon_jp.csv
```

All commands above require a database. Run `./setup.sh` first, or pass `--db-path :memory:` for a quick test (data won't persist).
