import json
import os

CFG_NAME = "config.json"
CFG_MODE = 0o600
HOME_MODE = 0o700

CFG_DEF = {
    "host": "127.0.0.1",
    "port": 8080,
    "public_hosts": [],
    "admin_token": "",
    "hmac_secret": "",
    "skill_id": "",
    "verify_sig": 1,
    "locale": "hi-IN",
    "cache_max_mb": 1024,
    "log_keep": 2000,
    "audio_mode": "local",
    "audio_origin": "",
    "queue_len": 25,
    "prefetch": 1,
    "url_ttl": 21600,
    "search_region": "IN",
    "search_lang": "hi",
    "search_want": 20,
    "min_dur": 20,
    "max_dur": 3600,
    "ytdlp_bin": "yt-dlp",
    "transcode": 0,
    "fetch_tmo": 90,
    "sig_ca": "",
    "say_title": 1,
    "launch_play": 1,
    "default_query": ""
}

CFG_SECRETS = ["admin_token", "hmac_secret"]

CFG_ENV = "YTA_"


def cfg_home():
    d = os.environ.get("YTA_HOME")
    if d != None and d != "":
        return d
    return os.path.join(os.path.expanduser("~"), ".ytalexa")


def cfg_path():
    return os.path.join(cfg_home(), CFG_NAME)


def cfg_mkhome():
    d = cfg_home()
    if os.path.isdir(d):
        return 0
    try:
        os.makedirs(d, HOME_MODE)
    except OSError:
        return -1
    return 0


def cfg_dup_def():
    c = {}
    for k in CFG_DEF:
        v = CFG_DEF[k]
        if type(v) == list:
            v = list(v)
        c[k] = v
    return c


def cfg_read_raw():
    p = cfg_path()
    if not os.path.isfile(p):
        return None
    try:
        f = open(p, "r")
        raw = f.read()
        f.close()
    except OSError:
        return None
    try:
        got = json.loads(raw)
    except ValueError:
        return None
    if type(got) != dict:
        return None
    return got


def cfg_cast(k, raw):
    want = type(CFG_DEF[k])
    if want == int:
        try:
            return int(raw), 0
        except ValueError:
            return None, -1
    if want == list:
        out = []
        parts = raw.replace(",", " ").split()
        i = 0
        while i < len(parts):
            v = parts[i].strip()
            i = i + 1
            if v != "":
                out.append(v)
        return out, 0
    return raw, 0


def cfg_env(c):
    n = 0
    for k in CFG_DEF:
        name = CFG_ENV + k.upper()
        raw = os.environ.get(name)
        if raw == None or raw == "":
            continue
        v, rc = cfg_cast(k, raw)
        if rc != 0:
            continue
        c[k] = v
        n = n + 1
    return n


def cfg_load():
    c = cfg_dup_def()
    got = cfg_read_raw()
    if got != None:
        for k in got:
            if k not in CFG_DEF:
                continue
            if type(got[k]) != type(CFG_DEF[k]):
                continue
            c[k] = got[k]
    cfg_env(c)
    return c


def cfg_save(c):
    if cfg_mkhome() != 0:
        return -1
    out = {}
    for k in CFG_DEF:
        if k in c:
            out[k] = c[k]
    p = cfg_path()
    tmp = p + ".tmp"
    try:
        f = open(tmp, "w")
        f.write(json.dumps(out, indent=2, sort_keys=True))
        f.write("\n")
        f.close()
        os.chmod(tmp, CFG_MODE)
        os.replace(tmp, p)
    except OSError:
        return -1
    return 0


def cfg_gen_secret(n):
    return os.urandom(n).hex()


def cfg_init():
    c = cfg_load()
    dirty = 0
    if cfg_read_raw() == None and os.environ.get(
            CFG_ENV + "ADMIN_TOKEN") != None:
        return c, 0
    i = 0
    while i < len(CFG_SECRETS):
        k = CFG_SECRETS[i]
        if c[k] == "":
            c[k] = cfg_gen_secret(24)
            dirty = 1
        i = i + 1
    if dirty == 1:
        if cfg_save(c) != 0:
            return c, -1
    return c, 0


def cfg_patch(c, patch):
    bad = []
    for k in patch:
        if k not in CFG_DEF:
            bad.append(k)
            continue
        if k in CFG_SECRETS:
            bad.append(k)
            continue
        v = patch[k]
        if type(v) != type(CFG_DEF[k]):
            bad.append(k)
            continue
        c[k] = v
    if cfg_save(c) != 0:
        return bad, -1
    return bad, 0


def cfg_public(c):
    out = {}
    for k in c:
        if k in CFG_SECRETS:
            continue
        out[k] = c[k]
    return out
