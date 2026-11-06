import sys
import time

import db

LOG_LVLS = ["dbg", "inf", "wrn", "err"]
LOG_RANK = {"dbg": 0, "inf": 1, "wrn": 2, "err": 3}
LOG_TAIL_MAX = 1000
LOG_MSG_MAX = 2000
LOG_TRIM_EVERY = 200

LOG_N = 0
LOG_ECHO = 1


def log_rank(lvl):
    if lvl in LOG_RANK:
        return LOG_RANK[lvl]
    return 1


def log_stamp(ts):
    t = time.localtime(ts)
    return time.strftime("%Y-%m-%d %H:%M:%S", t)


def log_echo(ts, lvl, tag, msg):
    line = "%s %s %-8s %s\n" % (log_stamp(ts), lvl, tag, msg)
    try:
        sys.stderr.write(line)
        sys.stderr.flush()
    except OSError:
        pass


def log_add(lvl, tag, msg):
    global LOG_N
    if lvl not in LOG_RANK:
        lvl = "inf"
    msg = str(msg)
    if len(msg) > LOG_MSG_MAX:
        msg = msg[:LOG_MSG_MAX] + "..."
    ts = int(time.time())
    if LOG_ECHO == 1:
        log_echo(ts, lvl, tag, msg)
    sql = "INSERT INTO log (ts, lvl, tag, msg) VALUES (?, ?, ?, ?)"
    if db.db_exec(sql, (ts, lvl, tag, msg)) != 0:
        return -1
    LOG_N = LOG_N + 1
    if LOG_N % LOG_TRIM_EVERY == 0:
        import cfg
        log_trim(cfg.cfg_load()["log_keep"])
    return 0


def log_tail(n, lvl):
    if n < 1:
        n = 1
    if n > LOG_TAIL_MAX:
        n = LOG_TAIL_MAX
    want = log_rank(lvl)
    keep = []
    i = 0
    while i < len(LOG_LVLS):
        if LOG_RANK[LOG_LVLS[i]] >= want:
            keep.append(LOG_LVLS[i])
        i = i + 1
    marks = ",".join(["?"] * len(keep))
    sql = ("SELECT id, ts, lvl, tag, msg FROM log"
           " WHERE lvl IN (" + marks + ")"
           " ORDER BY id DESC LIMIT ?")
    args = tuple(keep) + (n,)
    rows = db.db_query(sql, args)
    if rows == None:
        return []
    out = []
    i = 0
    while i < len(rows):
        r = rows[i]
        e = {}
        e["id"] = r[0]
        e["ts"] = r[1]
        e["at"] = log_stamp(r[1])
        e["lvl"] = r[2]
        e["tag"] = r[3]
        e["msg"] = r[4]
        out.append(e)
        i = i + 1
    return out


def log_trim(keep):
    if keep < 100:
        keep = 100
    sql = ("DELETE FROM log WHERE id NOT IN"
           " (SELECT id FROM log ORDER BY id DESC LIMIT ?)")
    return db.db_exec(sql, (keep,))


def log_clear():
    return db.db_exec("DELETE FROM log", ())


def log_count():
    return db.db_count("log")
