#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  exec python3 run_theremin.py
fi

if command -v python >/dev/null 2>&1; then
  exec python run_theremin.py
fi

echo "Error: Python no encontrado. Instala Python 3 desde https://www.python.org/downloads/"
read -r -p "Presiona Enter para cerrar..."
