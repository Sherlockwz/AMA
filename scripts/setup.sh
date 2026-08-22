#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "pnpm is required. Install it with: corepack enable pnpm"
  exit 1
fi

pnpm install --frozen-lockfile
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r python/requirements.txt
pnpm build

echo "AMA is ready. Link it with: openclaw plugins install --link . --force"
