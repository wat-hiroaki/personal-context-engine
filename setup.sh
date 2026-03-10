#!/usr/bin/env bash
#
# Personal Context Engine — Setup Script
# Creates database, tables, and copies files to OpenClaw workspace.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW_DIR="${HOME}/.openclaw/workspace"
DB_DIR="${OPENCLAW_DIR}/data"
DB_PATH="${DB_DIR}/personal.db"

echo "============================================"
echo "  Personal Context Engine — Setup"
echo "============================================"
echo ""

# 1. Create directories
echo "[1/4] Creating directories..."
mkdir -p "${DB_DIR}"
mkdir -p "${OPENCLAW_DIR}/skills"
mkdir -p "${OPENCLAW_DIR}/scripts"
mkdir -p "${OPENCLAW_DIR}/config"
echo "  Done."

# 2. Create database and tables
echo "[2/4] Setting up SQLite database..."
if [ -f "${DB_PATH}" ]; then
    echo "  Database already exists: ${DB_PATH}"
    echo "  Running migrations (IF NOT EXISTS)..."
else
    echo "  Creating new database: ${DB_PATH}"
fi
sqlite3 "${DB_PATH}" < "${SCRIPT_DIR}/schema/init.sql"
chmod 600 "${DB_PATH}"
echo "  Done."

# 3. Copy skills
echo "[3/4] Installing OpenClaw skills..."
for skill_dir in "${SCRIPT_DIR}/skills"/*/; do
    skill_name=$(basename "${skill_dir}")
    target_dir="${OPENCLAW_DIR}/skills/${skill_name}"
    mkdir -p "${target_dir}"
    cp -r "${skill_dir}"* "${target_dir}/"
    echo "  Installed: ${skill_name}"
done
echo "  Done."

# 4. Copy scripts and config
echo "[4/4] Copying scripts and config..."
cp "${SCRIPT_DIR}/scripts/"*.py "${OPENCLAW_DIR}/scripts/" 2>/dev/null || true
cp "${SCRIPT_DIR}/config/pce.json" "${OPENCLAW_DIR}/config/" 2>/dev/null || true

# Copy video processing script if it exists
if [ -f "${SCRIPT_DIR}/scripts/process_video.sh" ]; then
    cp "${SCRIPT_DIR}/scripts/process_video.sh" "${OPENCLAW_DIR}/scripts/"
    chmod +x "${OPENCLAW_DIR}/scripts/process_video.sh"
fi

echo "  Done."

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Database: ${DB_PATH}"
echo "Skills:   ${OPENCLAW_DIR}/skills/"
echo "Scripts:  ${OPENCLAW_DIR}/scripts/"
echo ""
echo "Test it by telling OpenClaw:"
echo '  「プロテインを登録して。SAVASのホエイ、Amazonで2980円で買った」'
echo ""
