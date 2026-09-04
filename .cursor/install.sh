#!/usr/bin/env bash
# Idempotent repository bootstrap for the options-evaluator project.
# Installs uv (if missing), then provisions the pinned Python (3.14) and all
# project dependencies from uv.lock into a local .venv.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

cd "$(dirname "$0")/.."

# Installs the interpreter from .python-version and syncs from uv.lock.
uv sync --frozen
