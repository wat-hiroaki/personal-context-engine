# Contributing to Personal Context Engine

Thank you for your interest in contributing!

## Getting Started

1. Fork and clone the repository
2. Run the setup: `chmod +x setup.sh && ./setup.sh`
3. Install dev dependencies: `pip install pytest ruff`
4. Run tests: `pytest tests/ -v`

## Development Workflow

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Make your changes
3. Run tests: `pytest tests/ -v`
4. Run linter: `ruff check scripts/ tests/`
5. Submit a pull request

## Project Structure

- `schema/` — SQLite schema and migrations
- `scripts/` — Python scripts (importers, OCR, video processing)
- `skills/` — OpenClaw skill definitions (SKILL.md)
- `config/` — Configuration files (JSON)
- `tests/` — pytest test suite

## Guidelines

### Adding a New EC Format

Just edit `config/ec_formats.json` — no code changes needed. See existing formats for examples.

### Adding a New Skill

1. Create `skills/your-skill/SKILL.md`
2. Follow the YAML frontmatter format used in existing skills
3. Add database tables via a migration file in `schema/`

### Modifying the Schema

1. **Never** modify `init.sql` for existing columns (breaks existing databases)
2. Create a new migration file: `schema/migrate_vX.Y.sql`
3. Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`
4. Update `setup.sh` to apply the new migration

### Code Style

- Python 3.10+ (use `type | None` syntax, not `Optional`)
- Use `sqlite3` context managers for transaction safety
- Always enable `PRAGMA foreign_keys = ON`
- Include row numbers in error messages

### Testing

- All new features should include tests in `tests/`
- Test both happy paths and edge cases
- Use the `db_path` fixture for database tests

## Pull Requests

- Write descriptions in English or Japanese
- Reference any related issues
- Include test results in the PR description

## Reporting Issues

- Use GitHub Issues
- Include: OS, Python version, steps to reproduce
- For import issues: include (sanitized) CSV header format

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
