#!/data/data/com.termux/files/usr/bin/bash
set -u

HERE="$(cd "$(dirname "$0")/.." && pwd)"
LOGDIR="$HOME/.ytalexa"
LOGFILE="$LOGDIR/server.log"
PIDFILE="$LOGDIR/server.pid"

mkdir -p "$LOGDIR"
chmod 700 "$LOGDIR"

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock
  echo "wake lock held"
fi

if [ -f "$PIDFILE" ]; then
  OLD="$(cat "$PIDFILE" 2>/dev/null || echo)"
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    echo "already running as pid $OLD"
    exit 0
  fi
fi

echo $$ > "$PIDFILE"
echo "logging to $LOGFILE"

while true; do
  echo "--- start $(date -Iseconds)" >> "$LOGFILE"
  python3 "$HERE/bin/serve.py" >> "$LOGFILE" 2>&1
  RC=$?
  echo "--- exit rc=$RC $(date -Iseconds)" >> "$LOGFILE"
  if [ "$RC" = "0" ]; then
    break
  fi
  if [ "$RC" = "2" ]; then
    break
  fi
  sleep 5
done

rm -f "$PIDFILE"
if command -v termux-wake-unlock >/dev/null 2>&1; then
  termux-wake-unlock
fi
