import hashlib
import json
import time

import db
import log

QU_PRE = "q:"
QU_MAX = 60
QU_TTL = 86400 * 3


def qu_key(user):
    if type(user) != str or user == "":
        user = "anon"
    h = hashlib.sha256(user.encode("utf-8")).hexdigest()
    return QU_PRE + h[:20]


def qu_new():
    st = {}
    st["items"] = []
    st["idx"] = 0
    st["off"] = 0
    st["ts"] = int(time.time())
    return st


def qu_trim(items):
    out = []
    i = 0
    while i < len(items) and i < QU_MAX:
        e = items[i]
        i = i + 1
        if type(e) != dict:
            continue
        if type(e.get("vid")) != str:
            continue
        r = {}
        r["vid"] = e["vid"]
        r["title"] = str(e.get("title", ""))[:160]
        r["chan"] = str(e.get("chan", ""))[:80]
        d = e.get("dur", 0)
        if type(d) != int:
            d = 0
        r["dur"] = d
        out.append(r)
    return out


def qu_save(user, st):
    st["ts"] = int(time.time())
    try:
        raw = json.dumps(st)
    except (TypeError, ValueError):
        return -1
    return db.kv_set(qu_key(user), raw, st["ts"])


def qu_load(user):
    raw = db.kv_get(qu_key(user))
    if raw == None:
        return qu_new()
    try:
        st = json.loads(raw)
    except ValueError:
        return qu_new()
    if type(st) != dict:
        return qu_new()
    if type(st.get("items")) != list:
        return qu_new()
    if type(st.get("idx")) != int:
        st["idx"] = 0
    if type(st.get("off")) != int:
        st["off"] = 0
    if type(st.get("ts")) != int:
        st["ts"] = 0
    if int(time.time()) - st["ts"] > QU_TTL:
        return qu_new()
    return st


def qu_set(user, items):
    st = qu_new()
    st["items"] = qu_trim(items)
    st["idx"] = 0
    st["off"] = 0
    if qu_save(user, st) != 0:
        log.log_add("err", "queue", "save failed")
    return st


def qu_at(st, i):
    if i < 0:
        return None
    if i >= len(st["items"]):
        return None
    return st["items"][i]


def qu_cur(st):
    return qu_at(st, st["idx"])


def qu_step(user, st, delta):
    i = st["idx"] + delta
    if i < 0:
        i = 0
    e = qu_at(st, i)
    if e == None:
        return None, st
    st["idx"] = i
    st["off"] = 0
    qu_save(user, st)
    return e, st


def qu_seek(user, st, i, off):
    e = qu_at(st, i)
    if e == None:
        return None
    st["idx"] = i
    st["off"] = off
    qu_save(user, st)
    return e


def qu_tok(idx, vid):
    return "%d:%s" % (idx, vid)


def qu_untok(tok):
    if type(tok) != str:
        return -1, ""
    p = tok.split(":")
    if len(p) != 2:
        return -1, ""
    if not p[0].isdigit():
        return -1, ""
    if len(p[1]) != 11:
        return -1, ""
    return int(p[0]), p[1]
