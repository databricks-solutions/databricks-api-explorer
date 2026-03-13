#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Databricks API Explorer — startup script (macOS / Linux)
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"
PORT="${DATABRICKS_APP_PORT:-8050}"

# ── Ensure Python is available ────────────────────────────────────────
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: $PYTHON not found. Install Python 3.11+ and try again."
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo "ERROR: Python 3.11+ required (found $PY_VERSION)."
    exit 1
fi

echo "Using Python $PY_VERSION"

# ── Create virtual environment if missing ─────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# ── Activate virtual environment ──────────────────────────────────────
source "$VENV_DIR/bin/activate"

# ── Install / update dependencies ─────────────────────────────────────
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# ── Launch ────────────────────────────────────────────────────────────
echo ""
echo "Starting Databricks API Explorer on http://localhost:$PORT"
echo "Press Ctrl+C to stop."
echo ""
python app.py
