import os
import time

import audio as au
import cfg
import ck
import db
import http_core as hc
import log
import ver
import yt_search as ys

UI_ROOT = ""
WEB_DIR = ""
DOC_DIR = ""
BOOT_TS = 0

DOC_EXTRA = ["SETUP.md", "TEST.md", "SECURITY.md",
             "README.md", "VERSION"]
DOC_EXT_OK = [".md", ""]


def ui_init(root):
    global UI_ROOT, WEB_DIR, DOC_DIR, BOOT_TS
    UI_ROOT = root
    WEB_DIR = os.path.join(root, "src", "web")
    DOC_DIR = os.path.join(root, "docs")
    BOOT_TS = int(time.time())


def ui_guard(req):
    c = cfg.cfg_load()
    if hc.tok_check(req, c["admin_token"]) != 0:
        return None
    return c


def safe_join(base, name):
    if name == "":
        return None
    if name.find("\x00") >= 0:
        return None
    p = os.path.normpath(os.path.join(base, name))
    b = os.path.normpath(base)
    if p != b and not p.startswith(b + os.sep):
        return None
    return p


def r_health(req):
    return hc.rsp_json(200, {"ok": 1, "ver": ver.VER_STR})


def r_root(req):
    return hc.rsp_redir(302, "/ui/")


def r_static(req):
    name = req["path"][len("/ui/"):]
    if name == "":
        name = "index.html"
    p = safe_join(WEB_DIR, name)
    if p == None:
        return hc.rsp_err(400, "bad path")
    if not os.path.isfile(p):
        return hc.rsp_err(404, "no file")
    return hc.rsp_file(p, None)


def dir_mb(path):
    if not os.path.isdir(path):
        return 0
    tot = 0
    names = os.listdir(path)
    i = 0
    while i < len(names):
        f = os.path.join(path, names[i])
        i = i + 1
        try:
            if os.path.isfile(f):
                tot = tot + os.path.getsize(f)
        except OSError:
            continue
    return tot // (1024 * 1024)


def r_status(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    st = {}
    st["ok"] = 1
    st["ver"] = ver.VER_STR
    st["name"] = ver.VER_NAME
    st["now"] = int(time.time())
    st["boot"] = BOOT_TS
    st["uptime"] = int(time.time()) - BOOT_TS
    st["host"] = c["host"]
    st["port"] = c["port"]
    st["locale"] = c["locale"]
    st["audio_mode"] = c["audio_mode"]
    st["public_hosts"] = c["public_hosts"]
    st["logs"] = log.log_count()
    st["home"] = cfg.cfg_home()
    st["cache_mb"] = au.au_bytes() // (1024 * 1024)
    st["cache_n"] = len(au.au_list())
    st["cookie"] = ck.ck_stat()
    st["cache_max_mb"] = c["cache_max_mb"]
    st["skill_id"] = c["skill_id"] != ""
    st["feat"] = feat_list()
    return hc.rsp_json(200, st)


def feat_list():
    f = []
    f.append({"id": "F01", "name": "config store log", "on": 1})
    f.append({"id": "F02", "name": "http core", "on": 1})
    f.append({"id": "F03", "name": "web ui", "on": 1})
    f.append({"id": "F04", "name": "youtube search", "on": 1})
    f.append({"id": "F05", "name": "cookie store", "on": 1})
    f.append({"id": "F06", "name": "audio cache", "on": 1})
    f.append({"id": "F07", "name": "alexa endpoint", "on": 1})
    f.append({"id": "F08", "name": "radio queue", "on": 1})
    f.append({"id": "F09", "name": "prefetch evict", "on": 1})
    f.append({"id": "F10", "name": "vercel adapter", "on": 0})
    return f


def r_logs(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    n = hc.q_int(req, "n", 200)
    lvl = hc.q_str(req, "lvl", "dbg")
    rows = log.log_tail(n, lvl)
    return hc.rsp_json(200, {"ok": 1, "rows": rows})


def r_logs_clear(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    if log.log_clear() != 0:
        return hc.rsp_err(500, "clear failed")
    log.log_add("inf", "ui", "log cleared")
    return hc.rsp_json(200, {"ok": 1})


def r_cfg_get(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    out = {}
    out["ok"] = 1
    out["cfg"] = cfg.cfg_public(c)
    out["locked"] = cfg.CFG_SECRETS
    return hc.rsp_json(200, out)


def r_cfg_put(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    patch = hc.req_json(req)
    if patch == None:
        return hc.rsp_err(400, "need json object")
    if type(patch) != dict:
        return hc.rsp_err(400, "need json object")
    bad, rc = cfg.cfg_patch(c, patch)
    if rc != 0:
        return hc.rsp_err(500, "save failed")
    log.log_add("inf", "ui", "config saved, %d rejected"
                % len(bad))
    out = {}
    out["ok"] = 1
    out["bad"] = bad
    out["cfg"] = cfg.cfg_public(cfg.cfg_load())
    return hc.rsp_json(200, out)


def doc_names():
    out = []
    i = 0
    while i < len(DOC_EXTRA):
        p = os.path.join(UI_ROOT, DOC_EXTRA[i])
        if os.path.isfile(p):
            out.append(DOC_EXTRA[i])
        i = i + 1
    if not os.path.isdir(DOC_DIR):
        return out
    names = sorted(os.listdir(DOC_DIR))
    i = 0
    while i < len(names):
        n = names[i]
        i = i + 1
        if not n.endswith(".md"):
            continue
        out.append("docs/" + n)
    return out


def r_docs(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    return hc.rsp_json(200, {"ok": 1, "files": doc_names()})


def r_doc(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    name = hc.q_str(req, "f", "")
    if name not in doc_names():
        return hc.rsp_err(404, "not a doc")
    p = safe_join(UI_ROOT, name)
    if p == None:
        return hc.rsp_err(400, "bad path")
    if not os.path.isfile(p):
        return hc.rsp_err(404, "no file")
    try:
        f = open(p, "r")
        txt = f.read()
        f.close()
    except OSError:
        return hc.rsp_err(500, "read failed")
    return hc.rsp_json(200, {"ok": 1, "name": name, "text": txt})


def r_ck_get(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    return hc.rsp_json(200, {"ok": 1, "cookie": ck.ck_stat()})


def r_ck_put(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    j = hc.req_json(req)
    if type(j) != dict:
        return hc.rsp_err(400, "need json object")
    txt = j.get("text")
    if type(txt) != str or txt.strip() == "":
        return hc.rsp_err(400, "need text field")
    rc, err = ck.ck_write(txt)
    if rc != 0:
        return hc.rsp_err(400, err)
    return hc.rsp_json(200, {"ok": 1, "cookie": ck.ck_stat()})


def r_ck_del(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    if ck.ck_clear() != 0:
        return hc.rsp_err(500, "remove failed")
    return hc.rsp_json(200, {"ok": 1, "cookie": ck.ck_stat()})


def r_cache_get(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    rows = au.au_list()
    rows = sorted(rows, key=lambda r: r["at"], reverse=True)
    out = []
    i = 0
    while i < len(rows) and i < 200:
        r = rows[i]
        i = i + 1
        e = {}
        e["vid"] = r["vid"]
        e["kib"] = r["size"] // 1024
        e["at"] = log.log_stamp(r["at"])
        out.append(e)
    tot = au.au_bytes()
    return hc.rsp_json(200, {"ok": 1, "files": out,
                             "mb": tot // (1024 * 1024),
                             "max_mb": c["cache_max_mb"]})


def r_cache_evict(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    n = au.au_evict(c["cache_max_mb"])
    return hc.rsp_json(200, {"ok": 1, "gone": n})


def r_cache_clear(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    rows = au.au_list()
    n = 0
    i = 0
    while i < len(rows):
        if au.au_rm(rows[i]["path"]) == 0:
            n = n + 1
        i = i + 1
    log.log_add("wrn", "audio", "cache cleared, %d files" % n)
    return hc.rsp_json(200, {"ok": 1, "gone": n})


def r_search(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    j = hc.req_json(req)
    if type(j) != dict:
        return hc.rsp_err(400, "need json object")
    q = j.get("q")
    if type(q) != str or q.strip() == "":
        return hc.rsp_err(400, "need q field")
    rows, err = ys.ys_search(q, c["search_lang"],
                             c["search_region"],
                             c["search_want"], c["min_dur"],
                             c["max_dur"])
    if err != None:
        return hc.rsp_err(502, err)
    if rows == None:
        rows = []
    out = []
    i = 0
    while i < len(rows) and i < 12:
        e = rows[i]
        i = i + 1
        r = {}
        r["vid"] = e["vid"]
        r["title"] = e["title"]
        r["chan"] = e["chan"]
        r["dur"] = e["durtxt"]
        r["views"] = e["views"]
        r["score"] = round(e["score"], 1)
        r["rel"] = round(e["rel"], 2)
        r["cached"] = au.au_have(e["vid"])
        out.append(r)
    return hc.rsp_json(200, {"ok": 1, "rows": out})


def r_fetch(req):
    c = ui_guard(req)
    if c == None:
        return hc.rsp_err(401, "bad token")
    j = hc.req_json(req)
    if type(j) != dict:
        return hc.rsp_err(400, "need json object")
    vid = j.get("vid")
    if type(vid) != str:
        return hc.rsp_err(400, "need vid field")
    rc, err = au.au_get(vid, c)
    if rc != 0:
        return hc.rsp_err(502, err)
    return hc.rsp_json(200, {"ok": 1, "vid": vid,
                             "kib": os.path.getsize(
                                 au.au_file(vid)) // 1024})


def ui_routes():
    hc.rt_add("GET", "/health", r_health, 0)
    hc.rt_add("GET", "/", r_root, 0)
    hc.rt_add("GET", "/ui/", r_static, 1)
    hc.rt_add("GET", "/api/status", r_status, 0)
    hc.rt_add("GET", "/api/logs", r_logs, 0)
    hc.rt_add("POST", "/api/logs/clear", r_logs_clear, 0)
    hc.rt_add("GET", "/api/config", r_cfg_get, 0)
    hc.rt_add("POST", "/api/config", r_cfg_put, 0)
    hc.rt_add("GET", "/api/docs", r_docs, 0)
    hc.rt_add("GET", "/api/doc", r_doc, 0)
    hc.rt_add("GET", "/api/cookies", r_ck_get, 0)
    hc.rt_add("POST", "/api/cookies", r_ck_put, 0)
    hc.rt_add("POST", "/api/cookies/clear", r_ck_del, 0)
    hc.rt_add("GET", "/api/cache", r_cache_get, 0)
    hc.rt_add("POST", "/api/cache/evict", r_cache_evict, 0)
    hc.rt_add("POST", "/api/cache/clear", r_cache_clear, 0)
    hc.rt_add("POST", "/api/search", r_search, 0)
    hc.rt_add("POST", "/api/fetch", r_fetch, 0)
