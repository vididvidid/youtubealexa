import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import alexa
import audio as au
import cfg
import http_core as hc
import log
import routes_ui
import ver

USAGE = "usage: serve.py [--host H] [--port N]\n"


def arg_parse(argv):
    o = {}
    o["host"] = None
    o["port"] = None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--host" and i + 1 < len(argv):
            o["host"] = argv[i + 1]
            i = i + 2
            continue
        if a == "--port" and i + 1 < len(argv):
            try:
                o["port"] = int(argv[i + 1])
            except ValueError:
                return None
            i = i + 2
            continue
        return None
    return o


def banner(c, token):
    sys.stdout.write("\n")
    sys.stdout.write("%s %s\n" % (ver.VER_NAME, ver.VER_STR))
    sys.stdout.write("home    %s\n" % cfg.cfg_home())
    sys.stdout.write("listen  http://%s:%d\n"
                     % (c["host"], c["port"]))
    sys.stdout.write("console http://%s:%d/ui/\n"
                     % (c["host"], c["port"]))
    sys.stdout.write("token   %s\n" % token)
    sys.stdout.write("alexa   POST /alexa\n")
    sys.stdout.write("\n")
    sys.stdout.flush()


def main(argv):
    o = arg_parse(argv)
    if o == None:
        sys.stderr.write(USAGE)
        return 2
    c, rc = cfg.cfg_init()
    if rc != 0:
        sys.stderr.write("cannot write config in %s\n"
                         % cfg.cfg_home())
        return 1
    if o["host"] != None:
        c["host"] = o["host"]
    if o["port"] != None:
        c["port"] = o["port"]
    if au.au_init(ROOT) != 0:
        sys.stderr.write("cannot create cache dir\n")
        return 1
    routes_ui.ui_init(ROOT)
    routes_ui.ui_routes()
    alexa.ax_routes()
    srv = hc.srv_make(c["host"], c["port"])
    if srv == None:
        sys.stderr.write("bind failed\n")
        return 1
    banner(c, c["admin_token"])
    log.log_add("inf", "boot", "listening on %s:%d"
                % (c["host"], c["port"]))
    hc.srv_run(srv)
    log.log_add("inf", "boot", "stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
