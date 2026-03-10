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
echo "[1/5] Creating directories..."
mkdir -p "${DB_DIR}"
mkdir -p "${OPENCLAW_DIR}/skills"
mkdir -p "${OPENCLAW_DIR}/scripts"
mkdir -p "${OPENCLAW_DIR}/config"
echo "  Done."

# 2. Create database and tables
echo "[2/5] Setting up SQLite database..."
if [ -f "${DB_PATH}" ]; then
    echo "  Database already exists: ${DB_PATH}"
    echo "  Running migrations (IF NOT EXISTS)..."
else
    echo "  Creating new database: ${DB_PATH}"
fi
sqlite3 "${DB_PATH}" < "${SCRIPT_DIR}/schema/init.sql"

# Run v0.2 migration if available
if [ -f "${SCRIPT_DIR}/schema/migrate_v0.2.sql" ]; then
    echo "  Applying v0.2 migration..."
    sqlite3 "${DB_PATH}" < "${SCRIPT_DIR}/schema/migrate_v0.2.sql"
fi

chmod 600 "${DB_PATH}"
echo "  Done."

# 3. Copy skills
echo "[3/5] Installing OpenClaw skills..."
for skill_dir in "${SCRIPT_DIR}/skills"/*/; do
    skill_name=$(basename "${skill_dir}")
    target_dir="${OPENCLAW_DIR}/skills/${skill_name}"
    mkdir -p "${target_dir}"
    cp -r "${skill_dir}"* "${target_dir}/"
    echo "  Installed: ${skill_name}"
done
echo "  Done."

# 4. Copy scripts and config
echo "[4/5] Copying scripts and config..."
cp "${SCRIPT_DIR}/scripts/"*.py "${OPENCLAW_DIR}/scripts/" 2>/dev/null || true
cp "${SCRIPT_DIR}/scripts/"*.sh "${OPENCLAW_DIR}/scripts/" 2>/dev/null || true
cp "${SCRIPT_DIR}/config/"*.json "${OPENCLAW_DIR}/config/" 2>/dev/null || true
chmod +x "${OPENCLAW_DIR}/scripts/"*.sh 2>/dev/null || true
echo "  Done."

# 5. Check optional dependencies
echo "[5/5] Checking dependencies..."

# Python
if command -v python3 &>/dev/null; then
    PYTHON_VER=$(python3 --version 2>&1)
    echo "  Python: ${PYTHON_VER}"
else
    echo "  ⚠ Python 3 not found. Required for CSV import and receipt OCR."
fi

# ffmpeg
if command -v ffmpeg &>/dev/null; then
    echo "  ffmpeg: OK"
else
    echo "  ⚠ ffmpeg not found. Required for video-cataloger."
    echo "    Install: https://ffmpeg.org/download.html"
fi

# Tesseract
if command -v tesseract &>/dev/null; then
    TESS_VER=$(tesseract --version 2>&1 | head -1)
    echo "  Tesseract: ${TESS_VER}"
else
    echo "  ⚠ Tesseract not found. Required for receipt-scanner."
    echo "    macOS:   brew install tesseract tesseract-lang"
    echo "    Ubuntu:  sudo apt install tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng"
    echo "    Windows: https://github.com/UB-Mannheim/tesseract/wiki"
fi

# Python packages (use correct import names)
echo ""
echo "  Python packages:"
declare -A PKG_IMPORTS=(
    ["pytesseract"]="pytesseract"
    ["Pillow"]="PIL"
    ["opencv-python-headless"]="cv2"
    ["openai-whisper"]="whisper"
    ["chardet"]="chardet"
)
for pkg in pytesseract Pillow opencv-python-headless openai-whisper chardet; do
    import_name="${PKG_IMPORTS[$pkg]}"
    if python3 -c "import ${import_name}" 2>/dev/null; then
        echo "    ${pkg}: OK"
    else
        echo "    ${pkg}: not installed (optional)"
    fi
done 2>/dev/null || echo "    (Could not check Python packages)"
echo "  Install OCR deps:   pip install -r requirements.txt"
echo "  Install video deps: pip install -r requirements-video.txt"

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "Database: ${DB_PATH}"
echo "Skills:   ${OPENCLAW_DIR}/skills/"
echo "Scripts:  ${OPENCLAW_DIR}/scripts/"
echo ""
echo "Quick test — tell OpenClaw:"
echo '  「プロテインを登録して。SAVASのホエイ、Amazonで2980円で買った」'
echo ""
echo "Import CSV:"
echo "  python3 ${OPENCLAW_DIR}/scripts/import_ec_plugins.py <csv_file> --list-formats"
echo ""
echo "Scan receipt:"
echo "  python3 ${OPENCLAW_DIR}/scripts/import_receipt.py <image_file>"
echo ""
