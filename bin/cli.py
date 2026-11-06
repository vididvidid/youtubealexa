import os
import signal
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import audio as au
import cfg
import ck
import log
import ver
import wizard as wz

USAGE = """ytalexa %s

usage: ytalexa <command> [args]

  setup              interactive setup wizard
  start              start the server in the background
  stop               stop the server
  restart            stop then start
  serve              run in the foreground, ctrl-c to stop
  status             show everything at a glance
  selftest           check the pipeline end to end
  token              print the console admin token
  console            print the console url and token
  cookies <file>     load a cookies.txt
  tunnel [mode]      bring up the tunnel, default tailscale
  update             upgrade yt-dlp and ytmusicapi
  logs [n]           print the last n log lines, default 40
  version            print the version

run with no command for the wizard.
"""


def pidfile():
    return os.path.join(cfg.cfg_home(), "server.pid")


def pid_read():
    p = pidfile()
    if not os.path.isfile(p):
        return 0
    try:
        f = open(p, "r")
        v = f.read().strip()
        f.close()
    except OSError:
        return 0
    if not v.isdigit():
        return 0
    n = int(v)
    try:
        os.kill(n, 0)
    except OSError:
        return 0
    return n


def c_setup(argv):
    wz.wz_main()
    return 0


def c_start(argv):
    return wz.do_start()


def c_stop(argv):
    n = pid_read()
    c0 = cfg.cfg_load()
    if n == 0 and wz.port_up(c0["port"]) == 0:
        sys.stdout.write("not running\n")
        return 0
    if n == 0:
        sys.stdout.write("running but no pid file, kill by hand\n")
        return 1
    try:
        os.kill(n, signal.SIGTERM)
    except OSError as e:
        sys.stdout.write("kill failed: %r\n" % e)
        return 1
    sys.stdout.write("stopped pid %d\n" % n)
    return 0


def c_restart(argv):
    c_stop(argv)
    import time
    time.sleep(1.0)
    return wz.do_start()


def c_serve(argv):
    f = os.path.join(ROOT, "bin", "serve.py")
    os.execv(sys.executable, [sys.executable, f])
    return 1


def c_status(argv):
    return wz.do_status()


def c_selftest(argv):
    return wz.do_selftest()


def c_token(argv):
    sys.stdout.write("%s\n" % cfg.cfg_load()["admin_token"])
    return 0


def c_console(argv):
    c0 = cfg.cfg_load()
    sys.stdout.write("http://127.0.0.1:%d/ui/\n" % c0["port"])
    sys.stdout.write("%s\n" % c0["admin_token"])
    return 0


def c_cookies(argv):
    if len(argv) < 1:
        s = ck.ck_stat()
        if s["present"] == 0:
            sys.stdout.write("no cookies loaded\n")
            return 1
        sys.stdout.write("rows    %d\n" % s["rows"])
        sys.stdout.write("youtube %d\n" % s["yt"])
        sys.stdout.write("ok      %d\n" % s["ok"])
        sys.stdout.write("days    %d\n" % s["days"])
        return 0
    p = os.path.expanduser(argv[0])
    if not os.path.isfile(p):
        sys.stderr.write("no such file: %s\n" % p)
        return 1
    try:
        f = open(p, "r")
        txt = f.read()
        f.close()
    except OSError as e:
        sys.stderr.write("read failed: %r\n" % e)
        return 1
    log.LOG_ECHO = 0
    rc, err = ck.ck_write(txt)
    if rc != 0:
        sys.stderr.write("rejected: %s\n" % err)
        return 1
    s = ck.ck_stat()
    sys.stdout.write("stored %s\n" % ck.ck_path())
    sys.stdout.write("%d youtube rows, %d days left\n"
                     % (s["yt"], s["days"]))
    if len(s["missing"]) > 0:
        sys.stderr.write("WARNING missing: %s\n"
                         % ", ".join(s["missing"]))
        sys.stderr.write("export again from a private window\n")
        return 1
    sys.stdout.write("login cookies look complete\n")
    sys.stdout.write("now delete %s\n" % p)
    return 0


def c_tunnel(argv):
    mode = "tailscale"
    if len(argv) > 0:
        mode = argv[0]
    sh = os.path.join(ROOT, "bin", "tunnel.sh")
    port = str(cfg.cfg_load()["port"])
    try:
        r = subprocess.run(["bash", sh, mode, port])
    except OSError as e:
        sys.stderr.write("spawn failed: %r\n" % e)
        return 1
    return r.returncode


def c_update(argv):
    sys.stdout.write("upgrading yt-dlp and ytmusicapi\n")
    args = [sys.executable, "-m", "pip", "install",
            "--upgrade", "yt-dlp", "ytmusicapi"]
    try:
        r = subprocess.run(args)
    except OSError as e:
        sys.stderr.write("spawn failed: %r\n" % e)
        return 1
    if r.returncode != 0:
        return r.returncode
    rc, txt = wz.run(["yt-dlp", "--version"], 30)
    sys.stdout.write("yt-dlp now %s\n" % txt)
    if wz.port_up(cfg.cfg_load()["port"]) == 1:
        sys.stdout.write("restart the server to pick it up:\n")
        sys.stdout.write("  ytalexa restart\n")
    return 0


def c_logs(argv):
    n = 40
    if len(argv) > 0 and argv[0].isdigit():
        n = int(argv[0])
    rows = log.log_tail(n, "dbg")
    i = len(rows) - 1
    while i >= 0:
        r = rows[i]
        i = i - 1
        sys.stdout.write("%s %s %-8s %s\n"
                         % (r["at"], r["lvl"], r["tag"],
                            r["msg"]))
    return 0


def c_version(argv):
    sys.stdout.write("%s %s\n" % (ver.VER_NAME, ver.VER_STR))
    return 0


def c_help(argv):
    sys.stdout.write(USAGE % ver.VER_STR)
    return 0


CMDS = {
    "setup": c_setup,
    "start": c_start,
    "stop": c_stop,
    "restart": c_restart,
    "serve": c_serve,
    "status": c_status,
    "selftest": c_selftest,
    "token": c_token,
    "console": c_console,
    "cookies": c_cookies,
    "tunnel": c_tunnel,
    "update": c_update,
    "logs": c_logs,
    "version": c_version,
    "help": c_help,
    "-h": c_help,
    "--help": c_help,
    "-v": c_version,
    "--version": c_version
}


def main(argv):
    cfg.cfg_init()
    au.au_init(ROOT)
    wz.wz_init(ROOT)
    log.LOG_ECHO = 0
    if len(argv) < 2:
        return c_setup([])
    name = argv[1]
    if name not in CMDS:
        sys.stderr.write("unknown command: %s\n\n" % name[:24])
        sys.stderr.write(USAGE % ver.VER_STR)
        return 2
    try:
        return CMDS[name](argv[2:])
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        return 130
    except BrokenPipeError:
        try:
            fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(fd, sys.stdout.fileno())
        except OSError:
            pass
        return 0


def flush_safe(rc):
    try:
        sys.stdout.flush()
    except (BrokenPipeError, OSError):
        try:
            fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(fd, sys.stdout.fileno())
        except OSError:
            pass
        return 0
    return rc


if __name__ == "__main__":
    sys.exit(flush_safe(main(sys.argv)))
