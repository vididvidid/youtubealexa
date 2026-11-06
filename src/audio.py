import hashlib
import hmac
import os
import re
import subprocess
import threading
import time

import cfg
import ck
import log

AU_DIR = "cache"
AU_EXT = ".m4a"
AU_FMT = "140/bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]"
AU_FMT_ANY = "bestaudio/best"
AU_VID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
AU_ROOT = ""

AU_LK = threading.Lock()
AU_BUSY = {}


def au_init(root):
    global AU_ROOT
    AU_ROOT = root
    d = au_dir()
    if os.path.isdir(d):
        return 0
    try:
        os.makedirs(d, 0o700)
    except OSError:
        return -1
    return 0


def au_dir():
    if AU_ROOT == "":
        return os.path.join(cfg.cfg_home(), AU_DIR)
    return os.path.join(AU_ROOT, AU_DIR)


def au_vid_ok(vid):
    if type(vid) != str:
        return 0
    if AU_VID_RE.match(vid) == None:
        return 0
    return 1


def au_file(vid):
    return os.path.join(au_dir(), vid + AU_EXT)


def au_have(vid):
    p = au_file(vid)
    if not os.path.isfile(p):
        return 0
    try:
        if os.path.getsize(p) < 4096:
            return 0
    except OSError:
        return 0
    return 1


def au_touch(vid):
    p = au_file(vid)
    try:
        os.utime(p, None)
    except OSError:
        return -1
    return 0


def au_sign(vid, exp, secret):
    msg = ("%s|%d" % (vid, exp)).encode("utf-8")
    key = secret.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:32]


def au_url(vid, ttl, secret):
    exp = int(time.time()) + ttl
    sig = au_sign(vid, exp, secret)
    return "/audio/%s%s?e=%d&s=%s" % (vid, AU_EXT, exp, sig)


def au_verify(vid, exp, sig, secret):
    if au_vid_ok(vid) == 0:
        return -1
    if exp <= 0:
        return -1
    if exp < int(time.time()):
        return -1
    want = au_sign(vid, exp, secret)
    if not hmac.compare_digest(want, sig):
        return -1
    return 0


def au_lock(vid):
    AU_LK.acquire()
    if vid not in AU_BUSY:
        AU_BUSY[vid] = threading.Lock()
    lk = AU_BUSY[vid]
    AU_LK.release()
    return lk


def au_cmd(vid, out, c):
    args = [c["ytdlp_bin"]]
    args.append("--no-warnings")
    args.append("--no-progress")
    args.append("--no-playlist")
    args.append("--force-overwrites")
    args.append("--retries")
    args.append("3")
    args.append("--socket-timeout")
    args.append("20")
    args.append("-f")
    if c["transcode"] == 1:
        args.append(AU_FMT_ANY)
        args.append("-x")
        args.append("--audio-format")
        args.append("m4a")
    else:
        args.append(AU_FMT)
    arg = ck.ck_arg(vid)
    if arg != None:
        args.append("--cookies")
        args.append(arg)
    args.append("-o")
    args.append(out)
    args.append("--")
    args.append("https://www.youtube.com/watch?v=" + vid)
    return args


def au_tmp(vid):
    return os.path.join(au_dir(), "tmp-" + vid)


def au_tmp_clean(vid):
    ck.ck_run_clean(vid)
    d = au_dir()
    pre = "tmp-" + vid
    try:
        names = os.listdir(d)
    except OSError:
        return
    i = 0
    while i < len(names):
        n = names[i]
        i = i + 1
        if n.startswith(pre):
            au_rm(os.path.join(d, n))


def au_tmp_find(vid):
    d = au_dir()
    pre = "tmp-" + vid
    try:
        names = os.listdir(d)
    except OSError:
        return None
    best = None
    bsz = 0
    i = 0
    while i < len(names):
        n = names[i]
        i = i + 1
        if not n.startswith(pre):
            continue
        if n.endswith(".part") or n.endswith(".ytdl"):
            continue
        q = os.path.join(d, n)
        try:
            sz = os.path.getsize(q)
        except OSError:
            continue
        if sz > bsz:
            bsz = sz
            best = q
    return best


def au_run(vid, c):
    au_tmp_clean(vid)
    out = au_tmp(vid) + AU_EXT
    args = au_cmd(vid, out, c)
    t0 = time.time()
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,
                           timeout=c["fetch_tmo"])
    except FileNotFoundError:
        au_tmp_clean(vid)
        return -1, "yt-dlp not found: %s" % c["ytdlp_bin"]
    except subprocess.TimeoutExpired:
        au_tmp_clean(vid)
        return -1, "timeout after %ds" % c["fetch_tmo"]
    except OSError as e:
        au_tmp_clean(vid)
        return -1, "spawn failed %r" % e
    dt = time.time() - t0
    if r.returncode != 0:
        tail = r.stdout.decode("utf-8", "replace").strip()
        tail = tail.replace("\n", " ")[-300:]
        au_tmp_clean(vid)
        return -1, "yt-dlp rc=%d %s" % (r.returncode, tail)
    if not os.path.isfile(out):
        alt = au_tmp_find(vid)
        if alt == None:
            au_tmp_clean(vid)
            return -1, "no output file"
        out = alt
    try:
        sz = os.path.getsize(out)
        os.replace(out, au_file(vid))
    except OSError as e:
        au_tmp_clean(vid)
        return -1, "rename failed %r" % e
    au_tmp_clean(vid)
    log.log_add("inf", "audio", "fetched %s %d KiB in %.1fs"
                % (vid, sz // 1024, dt))
    return 0, None


def au_rm(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        return -1
    return 0


def au_get(vid, c):
    if au_vid_ok(vid) == 0:
        return -1, "bad video id"
    if au_have(vid) == 1:
        au_touch(vid)
        return 0, None
    lk = au_lock(vid)
    lk.acquire()
    try:
        if au_have(vid) == 1:
            au_touch(vid)
            return 0, None
        rc, err = au_run(vid, c)
    finally:
        lk.release()
    if rc != 0:
        log.log_add("err", "audio", "fetch %s: %s" % (vid, err))
        return -1, err
    return 0, None


def au_list():
    d = au_dir()
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    i = 0
    while i < len(names):
        n = names[i]
        i = i + 1
        if not n.endswith(AU_EXT):
            continue
        p = os.path.join(d, n)
        try:
            st = os.stat(p)
        except OSError:
            continue
        e = {}
        e["vid"] = n[:len(n) - len(AU_EXT)]
        e["path"] = p
        e["size"] = st.st_size
        e["at"] = int(st.st_mtime)
        out.append(e)
    return out


def au_bytes():
    rows = au_list()
    tot = 0
    i = 0
    while i < len(rows):
        tot = tot + rows[i]["size"]
        i = i + 1
    return tot


def au_evict(max_mb):
    if max_mb < 16:
        max_mb = 16
    cap = max_mb * 1024 * 1024
    rows = au_list()
    tot = 0
    i = 0
    while i < len(rows):
        tot = tot + rows[i]["size"]
        i = i + 1
    if tot <= cap:
        return 0
    rows = sorted(rows, key=lambda r: r["at"])
    gone = 0
    i = 0
    while i < len(rows) and tot > cap:
        r = rows[i]
        i = i + 1
        if au_rm(r["path"]) != 0:
            continue
        tot = tot - r["size"]
        gone = gone + 1
    log.log_add("inf", "audio", "evicted %d files, now %d MiB"
                % (gone, tot // (1024 * 1024)))
    return gone
