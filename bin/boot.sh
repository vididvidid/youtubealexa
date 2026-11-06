#!/data/data/com.termux/files/usr/bin/bash
set -u

export PATH="/data/data/com.termux/files/usr/bin:$PATH"
HERE="$HOME/youtubealexa"

termux-wake-lock 2>/dev/null || true

if [ -x "$HOME/.ytalexa/tunnel.sh" ]; then
  nohup "$HOME/.ytalexa/tunnel.sh" >/dev/null 2>&1 &
fi

cd "$HERE" || exit 1
nohup bash bin/run.sh >/dev/null 2>&1 &
