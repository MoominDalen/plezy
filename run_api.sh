#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
export API_HOST="${API_HOST:-127.0.0.1}"
export API_PORT="${API_PORT:-8765}"
if [[ -d .venv ]]; then
  exec .venv/bin/python -m api.server
fi
exec python3 -m api.server
