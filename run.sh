#!/usr/bin/env bash
# Start the County Content Console.
#
# One command, one process, one port. Builds the console if it is missing or
# out of date, then serves it and the API together from http://localhost:8000
#
#   ./run.sh          start on port 8000
#   PORT=9000 ./run.sh
#
# For editing the console itself, `npm --prefix web run dev` gives hot reload
# against this same API.

set -euo pipefail

cd "$(dirname "$0")"
PORT="${PORT:-8000}"

if [ ! -d .venv ]; then
  echo "Creating the Python environment..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -e ".[console]" || \
    ./.venv/bin/pip install --quiet pyyaml python-docx fastapi "uvicorn[standard]" python-multipart
fi

# Rebuild the console when a source file is newer than the bundle.
needs_build=0
if [ ! -d web/dist ]; then
  needs_build=1
elif [ -n "$(find web/src web/index.html -newer web/dist -type f 2>/dev/null | head -1)" ]; then
  needs_build=1
fi

if [ "$needs_build" = "1" ]; then
  if command -v npm >/dev/null 2>&1; then
    echo "Building the console..."
    [ -d web/node_modules ] || npm --prefix web install --silent
    npm --prefix web run build --silent
  else
    echo "npm not found — the API will run, but the console will not be served."
    echo "Install Node.js from https://nodejs.org to use the browser interface."
  fi
fi

echo
echo "  County Content Console  ->  http://localhost:${PORT}"
echo "  API docs                ->  http://localhost:${PORT}/docs"
echo "  Stop with Ctrl-C"
echo

exec ./.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port "${PORT}"
