#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/dist}"
VER="$(sed -n 's/^VER_STR = "\(.*\)"/\1/p' "$ROOT/src/ver.py")"
[ -n "$VER" ] || { echo "cannot read version" >&2; exit 1; }

TPREFIX="data/data/com.termux/files/usr"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

APP="$BUILD/$TPREFIX/opt/ytalexa"
mkdir -p "$APP" "$BUILD/$TPREFIX/bin" "$BUILD/DEBIAN"

cp -R "$ROOT/src" "$ROOT/bin" "$ROOT/docs" "$APP/"
cp "$ROOT/VERSION" "$ROOT/README.md" "$ROOT/SETUP.md" \
   "$ROOT/TEST.md" "$ROOT/SECURITY.md" \
   "$ROOT/requirements.txt" "$APP/"
mkdir -p "$APP/cache"
find "$APP" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
chmod +x "$APP"/bin/*.sh "$APP"/bin/*.py

cat > "$BUILD/$TPREFIX/bin/ytalexa" <<'WRAP'
#!/data/data/com.termux/files/usr/bin/bash
exec python3 /data/data/com.termux/files/usr/opt/ytalexa/bin/cli.py "$@"
WRAP
chmod 755 "$BUILD/$TPREFIX/bin/ytalexa"

cat > "$BUILD/DEBIAN/control" <<CTRL
Package: ytalexa
Version: $VER
Architecture: all
Maintainer: ytalexa
Depends: python, openssl-tool, ffmpeg
Recommends: termux-api
Section: sound
Priority: optional
Homepage: https://github.com/vididvidid/youtubealexa
Description: Hindi voice search for YouTube audio on an Echo
 Serves YouTube audio to an Amazon Echo from a phone running
 Termux, driven by a custom Alexa skill in Hindi. Search goes
 through YouTube's own endpoints and audio comes from yt-dlp,
 so there is no YouTube Data API key and no quota.
CTRL

cat > "$BUILD/DEBIAN/postinst" <<'POST'
#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "installing yt-dlp and ytmusicapi"
python3 -m pip install --upgrade --disable-pip-version-check \
  yt-dlp ytmusicapi || {
  echo "pip install failed, run it by hand:"
  echo "  pip install --upgrade yt-dlp ytmusicapi"
}
mkdir -p "$HOME/.ytalexa" 2>/dev/null || true
chmod 700 "$HOME/.ytalexa" 2>/dev/null || true
echo ""
echo "installed. next:"
echo "  ytalexa setup"
echo ""
POST
chmod 755 "$BUILD/DEBIAN/postinst"

cat > "$BUILD/DEBIAN/prerm" <<'PRE'
#!/data/data/com.termux/files/usr/bin/bash
set -e
if command -v ytalexa >/dev/null 2>&1; then
  ytalexa stop 2>/dev/null || true
fi
PRE
chmod 755 "$BUILD/DEBIAN/prerm"

mkdir -p "$OUT"
DEB="$OUT/ytalexa.deb"
dpkg-deb --build --root-owner-group "$BUILD" "$DEB" >/dev/null
echo "built $DEB"
dpkg-deb --info "$DEB" | sed 's/^/  /'
echo "  contents:"
dpkg-deb --contents "$DEB" | awk '{print $NF}' | head -14 \
  | sed 's/^/    /'
echo "    ... $(dpkg-deb --contents "$DEB" | wc -l) entries"
