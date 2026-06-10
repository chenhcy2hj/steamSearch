#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/run"
PID_FILE="$RUN_DIR/steamsearch.pid"
URL_FILE="$RUN_DIR/steamsearch.url"

if [[ ! -f "$PID_FILE" ]]; then
  echo "SteamSearch is not running."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" 2>/dev/null; then
  echo "SteamSearch is not running. Removing stale files."
  rm -f "$PID_FILE" "$URL_FILE"
  exit 0
fi

kill "$PID"
for _ in $(seq 1 30); do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE" "$URL_FILE"
    echo "SteamSearch stopped."
    exit 0
  fi
  sleep 0.2
done

echo "SteamSearch did not stop gracefully; forcing stop."
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE" "$URL_FILE"
echo "SteamSearch stopped."

