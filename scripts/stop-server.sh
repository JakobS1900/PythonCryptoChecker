#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"
MODE="${2:-}"
echo "Stopping server on port ${PORT}... ${MODE}"

if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti :"${PORT}" || true)
else
  # Fallback using netstat/grep/awk
  if command -v netstat >/dev/null 2>&1; then
    PIDS=$(netstat -nlp 2>/dev/null | awk -v p=":${PORT}" '$4 ~ p {print $7}' | cut -d'/' -f1 | tr '\n' ' ')
  else
    echo "Neither lsof nor netstat found to detect processes." >&2
    exit 1
  fi
fi

if [ -z "${PIDS:-}" ]; then
  echo "No process is listening on port ${PORT}." >&2
  if [ "$MODE" = "--aggressive" ]; then
    echo "Aggressive mode: killing uvicorn/run processes by pattern" >&2
    pkill -f "uvicorn|web.main:app|run.py" || true
  fi
  exit 0
fi

for pid in ${PIDS}; do
  if [ -n "$pid" ]; then
    echo "Killing PID $pid"
    kill -9 "$pid" || true
  fi
done

echo "Done."
