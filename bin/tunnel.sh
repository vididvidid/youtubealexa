#!/data/data/com.termux/files/usr/bin/bash
set -u

MODE="${1:-tailscale}"
PORT="${2:-8080}"
STATE="$HOME/.ytalexa"

mkdir -p "$STATE"

if [ "$MODE" = "tailscale" ]; then
  if ! command -v tailscaled >/dev/null 2>&1; then
    echo "tailscaled not found"
    echo "see docs/SETUP-MOBILE.md step 5"
    exit 1
  fi
  if ! pgrep -f "tailscaled.*userspace" >/dev/null 2>&1; then
    echo "starting tailscaled in userspace mode"
    nohup tailscaled \
      --tun=userspace-networking \
      --statedir="$STATE/tailscale" \
      --socket="$STATE/tailscaled.sock" \
      >> "$STATE/tailscaled.log" 2>&1 &
    sleep 4
  fi
  export TS_SOCKET="$STATE/tailscaled.sock"
  tailscale --socket="$STATE/tailscaled.sock" status \
    >/dev/null 2>&1 || {
    echo "run this once to log in:"
    echo "  tailscale --socket=$STATE/tailscaled.sock up"
    exit 1
  }
  echo "mounting only /alexa and /audio"
  tailscale --socket="$STATE/tailscaled.sock" funnel \
    --set-path=/alexa "http://127.0.0.1:$PORT/alexa" || exit 1
  tailscale --socket="$STATE/tailscaled.sock" funnel \
    --set-path=/audio "http://127.0.0.1:$PORT/audio" || exit 1
  tailscale --socket="$STATE/tailscaled.sock" funnel status
  exit 0
fi

if [ "$MODE" = "cloudflare" ]; then
  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "cloudflared not found"
    echo "see docs/SETUP-DOMAIN.md"
    exit 1
  fi
  CFG="$STATE/cloudflared.yml"
  if [ ! -f "$CFG" ]; then
    echo "missing $CFG"
    echo "see docs/SETUP-DOMAIN.md step 4"
    exit 1
  fi
  exec cloudflared tunnel --config "$CFG" run
fi

echo "usage: tunnel.sh [tailscale|cloudflare] [port]"
exit 2
