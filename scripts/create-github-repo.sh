#!/usr/bin/env bash
# Create the private GitHub repo and push (run on your Mac with `gh auth login`).
set -euo pipefail
cd "$(dirname "$0")/.."

OWNER="${GITHUB_OWNER:-MoominDalen}"
REPO="${GITHUB_REPO:-StockWatch}"

if ! command -v gh >/dev/null; then
  echo "Install GitHub CLI: brew install gh && gh auth login" >&2
  exit 1
fi

gh repo create "${OWNER}/${REPO}" \
  --private \
  --description "John Lewis Pokemon TCG stock checker + Pokemon Center UK queue monitor (macOS)" \
  --source=. \
  --remote=origin \
  --push

echo "Repository: https://github.com/${OWNER}/${REPO}"
