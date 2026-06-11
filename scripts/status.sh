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
  if command -v lsof >/dev/null 2>&1; then
    PORT_PIDS="$(lsof -tiTCP:8765 -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -n "$PORT_PIDS" ]]; then
      echo "Port 8765 is still occupied by PID(s): $PORT_PIDS"
    fi
  fi
  exit 1
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" 2>/dev/null; then
  echo "SteamSearch is not running, but a stale PID file exists."
  echo "PID file: $PID_FILE"
  echo "Run ./scripts/stop.sh to clean stale runtime files."
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
    SOURCE_STATUS="$(curl -fsS "$URL/api/source-status" 2>/dev/null || true)"
    if [[ -n "$SOURCE_STATUS" ]]; then
      echo "Source status: $SOURCE_STATUS"
    fi
  else
    echo "Health: failed"
  fi
fi

echo "Log: $SERVER_LOG"
