import os
import socket
import subprocess
import sys
import time

import audio as au
import cfg
import ck
import ver

WZ_COLOR = 1
WZ_ROOT = ""

WZ_C = {
    "r": "\033[0m",
    "b": "\033[1m",
    "d": "\033[2m",
    "g": "\033[32m",
    "y": "\033[33m",
    "e": "\033[31m",
    "c": "\033[36m"
}

WZ_PY_MIN = (3, 11)

WZ_DEPS = [
    ["openssl", ["openssl", "version"]],
    ["yt-dlp", ["yt-dlp", "--version"]],
    ["ffmpeg", ["ffmpeg", "-version"]]
]


def wz_init(root):
    global WZ_ROOT, WZ_COLOR
    WZ_ROOT = root
    if not sys.stdout.isatty():
        WZ_COLOR = 0
    if os.environ.get("NO_COLOR") not in [None, ""]:
        WZ_COLOR = 0


def c(key, txt):
    if WZ_COLOR == 0:
        return txt
    return WZ_C[key] + txt + WZ_C["r"]


def out(txt):
    try:
        sys.stdout.write(txt + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, OSError):
        return


def ask(prompt):
    sys.stdout.write(c("c", prompt))
    sys.stdout.flush()
    try:
        return sys.stdin.readline().strip()
    except (KeyboardInterrupt, EOFError):
        return ""


def mark(state):
    if state == 1:
        return c("g", "[ ok ]")
    if state == 0:
        return c("e", "[ no ]")
    return c("d", "[ ?? ]")


def rule():
    out(c("d", "-" * 62))


def run(args, tmo):
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=tmo)
    except FileNotFoundError:
        return -1, "not installed"
    except subprocess.TimeoutExpired:
        return -1, "timed out"
    except OSError as e:
        return -1, str(e)
    txt = r.stdout.decode("utf-8", "replace").strip()
    return r.returncode, txt


def is_termux():
    if os.environ.get("PREFIX", "").find("com.termux") >= 0:
        return 1
    if os.path.isdir("/data/data/com.termux/files/usr"):
        return 1
    return 0


def port_up(port):
    s = socket.socket()
    s.settimeout(1.0)
    rc = s.connect_ex(("127.0.0.1", port))
    s.close()
    if rc == 0:
        return 1
    return 0


def py_ok():
    if sys.version_info >= WZ_PY_MIN:
        return 1
    return 0


def py_str():
    return "%d.%d.%d" % (sys.version_info[0],
                         sys.version_info[1],
                         sys.version_info[2])


def st_deps():
    if py_ok() == 0:
        return 0
    i = 0
    while i < len(WZ_DEPS):
        rc, txt = run(WZ_DEPS[i][1], 20)
        i = i + 1
        if rc != 0:
            return 0
    try:
        import ytmusicapi
    except ImportError:
        return 0
    return 1


def st_cookies():
    s = ck.ck_stat()
    if s["present"] == 0:
        return 0
    if s["ok"] == 0:
        return 0
    return 1


def st_skill():
    c0 = cfg.cfg_load()
    if c0["skill_id"] == "":
        return 0
    return 1


def st_boot():
    p = os.path.join(os.path.expanduser("~"), ".termux",
                     "boot", "ytalexa.sh")
    if os.path.isfile(p):
        return 1
    return 0


def st_server():
    return port_up(cfg.cfg_load()["port"])


def st_tunnel():
    rc, txt = run(["tailscale", "funnel", "status"], 10)
    if rc != 0:
        return -1
    if txt.find("/alexa") >= 0:
        return 1
    return 0


def menu():
    out("")
    out(c("b", "  ytalexa setup  " + ver.VER_STR))
    rule()
    rows = [
        ["1", "check dependencies", st_deps()],
        ["2", "battery and autostart", -1],
        ["3", "load Premium cookies", st_cookies()],
        ["4", "set up the tunnel", st_tunnel()],
        ["5", "set the Alexa skill id", st_skill()],
        ["6", "install boot autostart", st_boot()],
        ["7", "start the server", st_server()],
        ["8", "run self test", -1],
        ["9", "show status", -1]
    ]
    i = 0
    while i < len(rows):
        r = rows[i]
        i = i + 1
        out("  %s  %s  %s" % (c("b", r[0]), mark(r[2]), r[1]))
    rule()
    out("  %s  quit" % c("b", "q"))
    out("")


def do_deps():
    out("")
    out(c("b", "checking dependencies"))
    bad = 0
    out("  %s %-12s %s" % (mark(py_ok()), "python",
                           py_str()))
    if py_ok() == 0:
        bad = bad + 1
        out(c("y", "       yt-dlp needs 3.11 or newer"))
        out(c("y", "       try: pkg upgrade python"))
    i = 0
    while i < len(WZ_DEPS):
        name = WZ_DEPS[i][0]
        rc, txt = run(WZ_DEPS[i][1], 20)
        i = i + 1
        if rc != 0:
            out("  %s %-12s %s" % (mark(0), name, txt))
            bad = bad + 1
            continue
        out("  %s %-12s %s" % (mark(1), name,
                               txt.split("\n")[0][:40]))
    try:
        import ytmusicapi
        out("  %s %-12s present" % (mark(1), "ytmusicapi"))
    except ImportError:
        out("  %s %-12s not installed" % (mark(0), "ytmusicapi"))
        bad = bad + 1
    if bad == 0:
        out(c("g", "\n  all dependencies present"))
        return 0
    out(c("y", "\n  %d missing. install with:" % bad))
    if is_termux() == 1:
        out("    pkg install -y python openssl-tool ffmpeg")
        out("    pip install --upgrade yt-dlp ytmusicapi")
    else:
        out("    pip install --upgrade yt-dlp ytmusicapi")
    return -1


def do_battery():
    out("")
    out(c("b", "battery and autostart"))
    out("")
    out("  Android will kill Termux within hours unless you")
    out("  change these. This cannot be done from a script.")
    out("")
    out(c("y", "  1. Settings, Apps, Termux, Battery"))
    out("     choose Unrestricted")
    out("")
    out(c("y", "  2. Xiaomi, Oppo, Vivo, OnePlus only:"))
    out("     also enable Autostart for Termux")
    out("")
    out("  These skins are aggressive. Step 2 is not optional")
    out("  on them.")
    out("")
    ask("  press enter when done ")
    return 0


def do_cookies():
    out("")
    out(c("b", "load Premium cookies"))
    out("")
    s = ck.ck_stat()
    if s["present"] == 1:
        out("  current: %d youtube rows, logged in = %s,"
            % (s["yt"], s["ok"] == 1))
        out("           expires in %d days" % s["days"])
        out("")
    out("  Export on a DESKTOP browser, not this phone:")
    out("")
    out("    1. open a PRIVATE or INCOGNITO window")
    out("    2. log in to youtube.com")
    out("    3. export cookies.txt, Netscape format")
    out(c("y", "    4. CLOSE it WITHOUT logging out"))
    out("")
    out("  Step 4 matters. Exporting from a session you keep")
    out("  using lets YouTube rotate it, and playback dies")
    out("  about a week later.")
    out("")
    p = ask("  path to cookies.txt (blank to cancel): ")
    if p == "":
        return -1
    p = os.path.expanduser(p)
    if not os.path.isfile(p):
        out(c("e", "  no such file: %s" % p))
        return -1
    try:
        f = open(p, "r")
        txt = f.read()
        f.close()
    except OSError as e:
        out(c("e", "  cannot read: %r" % e))
        return -1
    rc, err = ck.ck_write(txt)
    if rc != 0:
        out(c("e", "  rejected: %s" % err))
        return -1
    s = ck.ck_stat()
    out("")
    out(c("g", "  stored %s" % ck.ck_path()))
    out("  %d youtube rows, expires in %d days"
        % (s["yt"], s["days"]))
    if len(s["missing"]) > 0:
        out(c("e", "  WARNING missing: %s"
              % ", ".join(s["missing"])))
        out("  you were not logged in. export again.")
        return -1
    out(c("g", "  login cookies look complete"))
    out("")
    out(c("y", "  now delete the copy you imported:"))
    out("    rm %s" % p)
    return 0


def do_tunnel():
    out("")
    out(c("b", "set up the tunnel"))
    out("")
    sh = os.path.join(WZ_ROOT, "bin", "tunnel.sh")
    if not os.path.isfile(sh):
        out(c("e", "  missing %s" % sh))
        return -1
    rc, txt = run(["tailscale", "--version"], 10)
    if rc != 0:
        out(c("y", "  tailscale is not installed."))
        out("")
        out("  Install the Linux arm64 build into Termux, then")
        out("  log in once with:")
        out("")
        out("    tailscale --socket=%s up"
            % os.path.join(cfg.cfg_home(), "tailscaled.sock"))
        out("")
        out("  Full steps: docs/SETUP-MOBILE.md step 5")
        return -1
    port = cfg.cfg_load()["port"]
    out("  running: bash %s tailscale %d" % (sh, port))
    out("")
    rc, txt = run(["bash", sh, "tailscale", str(port)], 120)
    out(txt[-1200:])
    if rc != 0:
        out("")
        out(c("e", "  tunnel setup failed"))
        out(c("y", "  this is the known weak point of the"))
        out(c("y", "  project. see docs/SETUP-DOMAIN.md"))
        out(c("y", "  option B for the Oracle relay instead."))
        return -1
    out("")
    out(c("g", "  tunnel up, only /alexa and /audio exposed"))
    out("  write down the hostname above, part B needs it")
    return 0


def do_skill():
    out("")
    out(c("b", "set the Alexa skill id"))
    out("")
    c0 = cfg.cfg_load()
    if c0["skill_id"] != "":
        out("  current: %s" % c0["skill_id"])
        out("")
    out("  Copy it from the top of your skill page at")
    out("  developer.amazon.com/alexa/console/ask")
    out("")
    v = ask("  skill id (blank to cancel): ")
    if v == "":
        return -1
    if not v.startswith("amzn1.ask.skill."):
        out(c("e", "  that does not look like a skill id"))
        out("  expected amzn1.ask.skill.xxxxxxxx-...")
        return -1
    bad, rc = cfg.cfg_patch(c0, {"skill_id": v})
    if rc != 0:
        out(c("e", "  could not save config"))
        return -1
    out(c("g", "  saved. only this skill is accepted now."))
    return 0


def do_boot():
    out("")
    out(c("b", "install boot autostart"))
    out("")
    if is_termux() == 0:
        out(c("y", "  not running on Termux, skipping"))
        return -1
    d = os.path.join(os.path.expanduser("~"), ".termux", "boot")
    src = os.path.join(WZ_ROOT, "bin", "boot.sh")
    dst = os.path.join(d, "ytalexa.sh")
    if not os.path.isfile(src):
        out(c("e", "  missing %s" % src))
        return -1
    try:
        os.makedirs(d, 0o700)
    except OSError:
        pass
    try:
        f = open(src, "r")
        txt = f.read()
        f.close()
        txt = txt.replace('HERE="$HOME/youtubealexa"',
                          'HERE="%s"' % WZ_ROOT)
        f = open(dst, "w")
        f.write(txt)
        f.close()
        os.chmod(dst, 0o700)
    except OSError as e:
        out(c("e", "  install failed: %r" % e))
        return -1
    out(c("g", "  installed %s" % dst))
    out("")
    out("  Termux:Boot must be installed from F-Droid for")
    out("  this to fire. Reboot the phone to confirm it")
    out("  comes back by itself.")
    return 0


def do_start():
    out("")
    out(c("b", "start the server"))
    out("")
    c0 = cfg.cfg_load()
    if port_up(c0["port"]) == 1:
        out(c("g", "  already running on port %d" % c0["port"]))
        out("  console http://127.0.0.1:%d/ui/" % c0["port"])
        out("  token   %s" % c0["admin_token"])
        return 0
    sh = os.path.join(WZ_ROOT, "bin", "run.sh")
    if not os.path.isfile(sh):
        out(c("e", "  missing %s" % sh))
        return -1
    try:
        f = open(os.devnull, "w")
        subprocess.Popen(["bash", sh], stdout=f, stderr=f,
                         start_new_session=True)
    except OSError as e:
        out(c("e", "  spawn failed: %r" % e))
        return -1
    i = 0
    while i < 20:
        time.sleep(0.5)
        if port_up(c0["port"]) == 1:
            break
        i = i + 1
    if port_up(c0["port"]) == 0:
        out(c("e", "  did not come up"))
        out("  check %s/server.log" % cfg.cfg_home())
        return -1
    out(c("g", "  running on port %d" % c0["port"]))
    out("  console http://127.0.0.1:%d/ui/" % c0["port"])
    out("  token   %s" % c0["admin_token"])
    return 0


def do_selftest():
    out("")
    out(c("b", "self test"))
    out("")
    c0 = cfg.cfg_load()
    port = c0["port"]
    if port_up(port) == 0:
        out(c("e", "  server not running, do step 7 first"))
        return -1
    import json
    import urllib.error
    import urllib.request
    base = "http://127.0.0.1:%d" % port
    fails = 0

    def hit(path, tok, meth, body):
        u = base + path
        data = None
        if body != None:
            data = json.dumps(body).encode("utf-8")
        r = urllib.request.Request(u, data=data, method=meth)
        if tok != None:
            r.add_header("X-Admin-Token", tok)
        if data != None:
            r.add_header("Content-Type", "application/json")
        try:
            h = urllib.request.urlopen(r, timeout=90)
            raw = h.read()
            h.close()
            return h.status, raw
        except urllib.error.HTTPError as e:
            return e.code, b""
        except (urllib.error.URLError, OSError) as e:
            return -1, str(e).encode("utf-8")

    st, raw = hit("/health", None, "GET", None)
    ok = 1
    if st != 200:
        ok = 0
        fails = fails + 1
    out("  %s health endpoint" % mark(ok))

    st, raw = hit("/api/status", None, "GET", None)
    ok = 1
    if st != 401:
        ok = 0
        fails = fails + 1
    out("  %s console refuses no token" % mark(ok))

    st, raw = hit("/api/status", c0["admin_token"], "GET", None)
    ok = 1
    if st != 200:
        ok = 0
        fails = fails + 1
    out("  %s console accepts the token" % mark(ok))

    st, raw = hit("/api/search", c0["admin_token"], "POST",
                  {"q": "lag ja gale"})
    vid = ""
    ok = 1
    if st != 200:
        ok = 0
        fails = fails + 1
    else:
        try:
            j = json.loads(raw.decode("utf-8"))
            rows = j.get("rows", [])
            if len(rows) == 0:
                ok = 0
                fails = fails + 1
            else:
                vid = rows[0]["vid"]
        except ValueError:
            ok = 0
            fails = fails + 1
    out("  %s youtube search works" % mark(ok))

    ok = 1
    if vid == "":
        ok = 0
    else:
        st, raw = hit("/api/fetch", c0["admin_token"], "POST",
                      {"vid": vid})
        if st != 200:
            ok = 0
            fails = fails + 1
    out("  %s audio download works" % mark(ok))

    s = ck.ck_stat()
    out("  %s premium cookies loaded" % mark(s["ok"]))
    if s["ok"] == 0:
        out(c("y", "       without these, extraction is more"))
        out(c("y", "       likely to break. see step 3."))

    out("  %s alexa skill id set" % mark(st_skill()))
    t = st_tunnel()
    out("  %s tunnel exposing /alexa" % mark(t))
    if t != 1:
        out(c("y", "       the Echo cannot reach this phone"))
        out(c("y", "       until the tunnel is up. step 4."))

    out("")
    if fails == 0:
        out(c("g", "  core pipeline works"))
        return 0
    out(c("e", "  %d core checks failed" % fails))
    return -1


def do_status():
    out("")
    out(c("b", "status"))
    rule()
    c0 = cfg.cfg_load()
    s = ck.ck_stat()
    out("  version      %s" % ver.VER_STR)
    out("  home         %s" % cfg.cfg_home())
    out("  install      %s" % WZ_ROOT)
    out("  termux       %s" % (is_termux() == 1))
    out("  server       %s on port %d"
        % (port_up(c0["port"]) == 1, c0["port"]))
    out("  console      http://127.0.0.1:%d/ui/" % c0["port"])
    out("  token        %s" % c0["admin_token"])
    out("  locale       %s" % c0["locale"])
    out("  skill id     %s" % (c0["skill_id"] or "not set"))
    hosts = "any"
    if len(c0["public_hosts"]) > 0:
        hosts = ", ".join(c0["public_hosts"])
    out("  public hosts %s" % hosts)
    out("  verify sig   %d" % c0["verify_sig"])
    if s["present"] == 1:
        out("  cookies      %d rows, logged in %s, %d days"
            % (s["yt"], s["ok"] == 1, s["days"]))
    else:
        out("  cookies      none")
    out("  cache        %d files, %d MiB of %d"
        % (len(au.au_list()), au.au_bytes() // (1024 * 1024),
           c0["cache_max_mb"]))
    rule()
    return 0


WZ_STEPS = {
    "1": do_deps,
    "2": do_battery,
    "3": do_cookies,
    "4": do_tunnel,
    "5": do_skill,
    "6": do_boot,
    "7": do_start,
    "8": do_selftest,
    "9": do_status
}


def wz_main():
    if is_termux() == 0:
        out(c("y", "\n  note: not running on Termux. steps 2"))
        out(c("y", "  and 6 do not apply here.\n"))
    while 1:
        menu()
        v = ask("  choose: ")
        if v in ["q", "Q", "quit", "exit"]:
            out("")
            return 0
        if v == "":
            continue
        if v not in WZ_STEPS:
            out(c("e", "  no such step: %s" % v[:8]))
            continue
        try:
            WZ_STEPS[v]()
        except KeyboardInterrupt:
            out(c("y", "\n  cancelled"))
        out("")
        ask("  press enter for the menu ")
