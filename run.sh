#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if missing
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Install/upgrade dependencies
pip install -q -r requirements.txt

# Copy .env if not present
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — edit it before running in production."
fi

echo ""
echo "  Bench Manager API starting on http://localhost:${BENCH_MANAGER_PORT:-8500}"
echo "  Scanning: ${BENCH_MANAGER_BENCH_ROOT:-$HOME}"
echo "  Frontend dev: cd frontend && npm install && npm run dev"
echo "  Frontend build: cd frontend && npm run build"
echo ""

python main.py
