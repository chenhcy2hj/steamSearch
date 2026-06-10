#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/run"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$RUN_DIR/steamsearch.pid"
URL_FILE="$RUN_DIR/steamsearch.url"
SERVER_LOG="$LOG_DIR/web_server.log"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
HOST="${STEAMSEARCH_HOST:-127.0.0.1}"
PORT="${STEAMSEARCH_PORT:-8765}"

mkdir -p "$RUN_DIR" "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE")"
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "SteamSearch is already running."
    if [[ -f "$URL_FILE" ]]; then
      echo "URL: $(cat "$URL_FILE")"
    fi
    echo "PID: $OLD_PID"
    exit 0
  fi
fi

cd "$ROOT_DIR"
PYTHONUNBUFFERED=1 nohup "$PYTHON_BIN" -m app.main web --host "$HOST" --port "$PORT" > "$SERVER_LOG" 2>&1 &
PID="$!"
echo "$PID" > "$PID_FILE"

URL=""
for _ in $(seq 1 50); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "SteamSearch failed to start. Log:"
    tail -40 "$SERVER_LOG" || true
    rm -f "$PID_FILE" "$URL_FILE"
    exit 1
  fi

  URL="$(sed -n 's/^SteamSearch Browser running at //p' "$SERVER_LOG" | tail -1)"
  if [[ -n "$URL" ]]; then
    if curl -fsS "$URL/health" >/dev/null 2>&1; then
      echo "$URL" > "$URL_FILE"
      echo "SteamSearch started."
      echo "URL: $URL"
      echo "PID: $PID"
      echo "Log: $SERVER_LOG"
      exit 0
    fi
  fi
  sleep 0.2
done

echo "SteamSearch start timed out. Log:"
tail -40 "$SERVER_LOG" || true
exit 1
