#!/usr/bin/env bash
# run-demo.sh — Start the mTLS demo web app for customer presentation.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEMO_DIR="${PROJECT_DIR}/demo"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  API Gateway mTLS — Demo Web App                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check config
if [[ ! -f "${PROJECT_DIR}/config.env" ]]; then
  echo "ERROR: config.env not found. Run deployment first."
  exit 1
fi

# Set up venv if needed
if [[ ! -d "${DEMO_DIR}/.venv" ]]; then
  echo "  Setting up Python virtual environment..."
  python3 -m venv "${DEMO_DIR}/.venv"
  "${DEMO_DIR}/.venv/bin/pip" install -q -r "${DEMO_DIR}/requirements.txt"
  echo "  Done."
  echo ""
fi

echo "  Starting demo server at http://localhost:5001"
echo "  Press Ctrl+C to stop."
echo ""

"${DEMO_DIR}/.venv/bin/python" "${DEMO_DIR}/app.py"
