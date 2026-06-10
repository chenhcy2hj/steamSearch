#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/run"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$RUN_DIR/steamsearch.pid"
URL_FILE="$RUN_DIR/steamsearch.url"
SERVER_LOG="$LOG_DIR/web_server.log"

if [[ ! -f "$PID_FILE" ]]; then
  echo "SteamSearch is not running."
  exit 1
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" 2>/dev/null; then
  echo "SteamSearch is not running, but a stale PID file exists."
  echo "PID file: $PID_FILE"
  exit 1
fi

echo "SteamSearch is running."
echo "PID: $PID"

if [[ -f "$URL_FILE" ]]; then
  URL="$(cat "$URL_FILE")"
else
  URL="$(sed -n 's/^SteamSearch Browser running at //p' "$SERVER_LOG" 2>/dev/null | tail -1)"
fi

if [[ -n "${URL:-}" ]]; then
  echo "URL: $URL"
  if curl -fsS "$URL/health" >/dev/null 2>&1; then
    echo "Health: ok"
  else
    echo "Health: failed"
  fi
fi

echo "Log: $SERVER_LOG"

