import os
import time

import cfg
import log

CK_NAME = "cookies.txt"
CK_MODE = 0o600
CK_MAX = 1 << 19

CK_WANT = [
    "SID", "HSID", "SSID", "APISID", "SAPISID",
    "__Secure-1PSID", "__Secure-3PSID", "LOGIN_INFO"
]

CK_CORE = ["SID", "HSID", "SSID", "APISID", "SAPISID"]


def ck_path():
    return os.path.join(cfg.cfg_home(), CK_NAME)


def ck_have():
    if os.path.isfile(ck_path()):
        return 1
    return 0


def ck_arg():
    if ck_have() == 0:
        return None
    return ck_path()


def ck_parse(text):
    rows = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        i = i + 1
        if ln == "":
            continue
        if ln.startswith("#") and not ln.startswith("#HttpOnly_"):
            continue
        if ln.startswith("#HttpOnly_"):
            ln = ln[len("#HttpOnly_"):]
        cols = ln.split("\t")
        if len(cols) < 7:
            continue
        e = {}
        e["domain"] = cols[0]
        e["path"] = cols[2]
        e["secure"] = cols[3]
        try:
            e["exp"] = int(cols[4])
        except ValueError:
            e["exp"] = 0
        e["name"] = cols[5]
        e["val"] = cols[6]
        rows.append(e)
    return rows


def ck_check(rows):
    st = {}
    st["rows"] = len(rows)
    st["yt"] = 0
    st["names"] = []
    st["missing"] = []
    st["exp_min"] = 0
    now = int(time.time())
    soonest = 0
    i = 0
    while i < len(rows):
        e = rows[i]
        i = i + 1
        if e["domain"].find("youtube.com") < 0:
            continue
        st["yt"] = st["yt"] + 1
        if e["name"] not in st["names"]:
            st["names"].append(e["name"])
        if e["name"] not in CK_WANT:
            continue
        if e["exp"] <= now:
            continue
        if soonest == 0 or e["exp"] < soonest:
            soonest = e["exp"]
    i = 0
    while i < len(CK_CORE):
        if CK_CORE[i] not in st["names"]:
            st["missing"].append(CK_CORE[i])
        i = i + 1
    st["exp_min"] = soonest
    if soonest == 0:
        st["days"] = 0
    else:
        st["days"] = (soonest - now) // 86400
    if len(st["missing"]) == 0 and st["yt"] > 0:
        st["ok"] = 1
    else:
        st["ok"] = 0
    return st


def ck_write(text):
    if len(text) > CK_MAX:
        return -1, "too big"
    rows = ck_parse(text)
    if len(rows) == 0:
        return -1, "no netscape cookie lines found"
    st = ck_check(rows)
    if st["yt"] == 0:
        return -1, "no youtube.com cookies"
    if cfg.cfg_mkhome() != 0:
        return -1, "cannot create home"
    p = ck_path()
    tmp = p + ".tmp"
    body = text
    if not body.startswith("# Netscape"):
        body = "# Netscape HTTP Cookie File\n" + body
    if not body.endswith("\n"):
        body = body + "\n"
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                     CK_MODE)
        f = os.fdopen(fd, "w")
        f.write(body)
        f.close()
        os.replace(tmp, p)
    except OSError as e:
        return -1, "write failed %r" % e
    log.log_add("inf", "cookie",
                "stored %d rows, %d youtube, core=%s, %d days"
                % (st["rows"], st["yt"],
                   len(st["missing"]) == 0, st["days"]))
    return 0, None


def ck_read():
    p = ck_path()
    if not os.path.isfile(p):
        return None
    try:
        f = open(p, "r")
        t = f.read()
        f.close()
    except OSError:
        return None
    return t


def ck_stat():
    t = ck_read()
    if t == None:
        return {"present": 0, "ok": 0, "rows": 0, "yt": 0,
                "missing": CK_CORE, "days": 0, "names": []}
    st = ck_check(ck_parse(t))
    st["present"] = 1
    try:
        st["mtime"] = int(os.path.getmtime(ck_path()))
    except OSError:
        st["mtime"] = 0
    return st


def ck_clear():
    p = ck_path()
    if not os.path.isfile(p):
        return 0
    try:
        os.remove(p)
    except OSError:
        return -1
    log.log_add("wrn", "cookie", "cookie file removed")
    return 0
