import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import ck
import cfg
import log

USAGE = "usage: cookies_load.py <cookies.txt>\n"


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(USAGE)
        return 2
    src = argv[1]
    if not os.path.isfile(src):
        sys.stderr.write("no such file: %s\n" % src)
        return 1
    try:
        f = open(src, "r")
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
    st = ck.ck_stat()
    sys.stdout.write("stored  %s\n" % ck.ck_path())
    sys.stdout.write("rows    %d\n" % st["rows"])
    sys.stdout.write("youtube %d\n" % st["yt"])
    sys.stdout.write("expires in %d days\n" % st["days"])
    if len(st["missing"]) > 0:
        sys.stdout.write("WARNING missing core cookies: %s\n"
                         % ", ".join(st["missing"]))
        sys.stdout.write("you are probably not logged in.\n")
        sys.stdout.write("export again from a private window.\n")
        return 1
    sys.stdout.write("login cookies look complete\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
