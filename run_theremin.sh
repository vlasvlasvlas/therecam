#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT_DIR/run_theremin.py"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$ROOT_DIR/run_theremin.py"
fi

echo "Error: no se encontro Python 3 en el sistema."
echo "Instala Python desde https://www.python.org/downloads/"
exit 1
