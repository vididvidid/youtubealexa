#!/usr/bin/env bash
set -u

REPO="${YTA_REPO:-OWNER/REPO}"
BRANCH="${YTA_BRANCH:-main}"
DEST="${YTA_DEST:-$HOME/ytalexa}"

say() { printf '%s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

say ""
say "  ytalexa installer"
say "  ================="
say ""

if [ "$REPO" = "OWNER/REPO" ]; then
  die "set YTA_REPO, for example:
    curl -fsSL <url>/install.sh | YTA_REPO=you/ytalexa bash"
fi

IS_TERMUX=0
if [ -n "${PREFIX:-}" ] && [ -d "$PREFIX/bin" ] \
   && printf '%s' "$PREFIX" | grep -q com.termux; then
  IS_TERMUX=1
fi
if [ -d /data/data/com.termux/files/usr ]; then
  IS_TERMUX=1
fi

if [ "$IS_TERMUX" = "1" ]; then
  say "  target   Termux on Android"
  BINDIR="$PREFIX/bin"
else
  say "  target   generic linux (not Termux)"
  say "  note     steps 2 and 6 of the wizard will not apply"
  BINDIR="$HOME/.local/bin"
  mkdir -p "$BINDIR"
fi
say "  repo     $REPO"
say "  install  $DEST"
say ""

say "[1/6] installing system packages"
if [ "$IS_TERMUX" = "1" ]; then
  pkg install -y python openssl-tool ffmpeg termux-api curl tar \
    >/dev/null 2>&1 || die "pkg install failed"
else
  if ! command -v python3 >/dev/null 2>&1; then
    die "install python3 first"
  fi
fi
say "      ok"

say "[2/6] installing yt-dlp and ytmusicapi"
PIPQ="--disable-pip-version-check -q"
python3 -m pip install $PIPQ --upgrade pip >/dev/null 2>&1 || true
if ! python3 -m pip install $PIPQ --upgrade yt-dlp ytmusicapi \
     >/dev/null 2>&1; then
  python3 -m pip install $PIPQ --upgrade --break-system-packages \
    yt-dlp ytmusicapi >/dev/null 2>&1 \
    || die "pip install failed"
fi
say "      yt-dlp $(yt-dlp --version 2>/dev/null || echo '?')"

say "[3/6] downloading ytalexa"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
URL="https://github.com/$REPO/releases/latest/download/ytalexa.tar.gz"
if ! curl -fsSL "$URL" -o "$TMP/a.tgz" 2>/dev/null; then
  say "      no release yet, taking branch $BRANCH"
  URL="https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz"
  curl -fsSL "$URL" -o "$TMP/a.tgz" || die "download failed"
fi
mkdir -p "$TMP/x"
tar -xzf "$TMP/a.tgz" -C "$TMP/x" || die "extract failed"

SRC="$TMP/x"
if [ ! -f "$SRC/bin/cli.py" ]; then
  SRC="$(find "$TMP/x" -maxdepth 2 -name cli.py -path '*/bin/*' \
        -printf '%h\n' 2>/dev/null | head -1)"
  SRC="$(dirname "$SRC")"
fi
[ -f "$SRC/bin/cli.py" ] || die "archive layout not recognised"

if [ -d "$DEST" ]; then
  say "      keeping your old copy at $DEST.old"
  rm -rf "$DEST.old"
  mv "$DEST" "$DEST.old"
fi
mkdir -p "$DEST"
cp -R "$SRC/." "$DEST/" || die "copy failed"
chmod +x "$DEST"/bin/*.sh "$DEST"/bin/*.py 2>/dev/null || true
say "      ok"

say "[4/6] creating state directory"
mkdir -p "$HOME/.ytalexa"
chmod 700 "$HOME/.ytalexa"
say "      $HOME/.ytalexa"

say "[5/6] installing the ytalexa command"
cat > "$BINDIR/ytalexa" <<WRAP
#!/usr/bin/env bash
exec python3 "$DEST/bin/cli.py" "\$@"
WRAP
chmod +x "$BINDIR/ytalexa"
say "      $BINDIR/ytalexa"
if ! printf '%s' ":$PATH:" | grep -q ":$BINDIR:"; then
  say "      WARNING $BINDIR is not on your PATH"
  say "      add this to ~/.bashrc:"
  say "        export PATH=\"$BINDIR:\$PATH\""
fi

say "[6/6] checking it runs"
python3 "$DEST/bin/cli.py" version || die "cli failed to run"

say ""
say "  done. next:"
say ""
say "    ytalexa setup"
say ""
say "  that opens a numbered menu. work down it."
say "  full steps: $DEST/SETUP.md"
say ""
