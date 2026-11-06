#!/data/data/com.termux/files/usr/bin/bash
set -u

echo "ytalexa termux setup"
echo

echo "[1/6] updating package lists"
pkg update -y >/dev/null 2>&1 || true

echo "[2/6] installing python, openssl, ffmpeg, termux-api"
pkg install -y python openssl-tool ffmpeg termux-api \
    termux-services || exit 1

echo "[3/6] installing yt-dlp and ytmusicapi"
pip install --upgrade pip >/dev/null 2>&1 || true
pip install --upgrade yt-dlp ytmusicapi || exit 1

echo "[4/6] checking versions"
python3 --version
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= \
  (3, 11) else 1)' 2>/dev/null; then
  echo "  ERROR python 3.11 or newer is required"
  echo "  yt-dlp needs it. try: pkg upgrade python"
  exit 1
fi
yt-dlp --version
openssl version
python3 -c "import ytmusicapi; print('ytmusicapi ok')"

echo "[5/6] creating state directory"
mkdir -p "$HOME/.ytalexa"
chmod 700 "$HOME/.ytalexa"
echo "  $HOME/.ytalexa"

echo "[6/6] disabling battery optimisation"
echo "  open Android Settings, Apps, Termux, Battery"
echo "  choose Unrestricted, then come back"
echo
echo "setup done. next:"
echo "  bash bin/run.sh"
