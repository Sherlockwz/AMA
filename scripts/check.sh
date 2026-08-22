#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

cmp -s SKILL.md skills/ama-memory/SKILL.md || {
  echo "Root SKILL.md and plugin-bundled skill are out of sync."
  exit 1
}

pnpm typecheck
pnpm test
PYTHON_BIN="python3"
if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
fi
"${PYTHON_BIN}" -m unittest discover -s python/tests -p 'test_*.py'
"${PYTHON_BIN}" -m compileall -q python
pnpm build
