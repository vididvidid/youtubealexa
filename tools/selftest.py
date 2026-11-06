import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ["YTA_HOME"] = tempfile.mkdtemp(prefix="ytatest")

import alexa_sig as sg
import audio as au
import cfg
import ck
import fold as fd
import http_core as hc
import log
import qu
import speak as sp
import yt_search as ys

log.LOG_ECHO = 0

T_PASS = 0
T_FAIL = 0
T_NAME = ""


def grp(name):
    global T_NAME
    T_NAME = name
    sys.stdout.write("\n%s\n" % name)


def ok(label, got, want):
    global T_PASS, T_FAIL
    if got == want:
        T_PASS = T_PASS + 1
        sys.stdout.write("  pass  %s\n" % label)
        return 0
    T_FAIL = T_FAIL + 1
    sys.stdout.write("  FAIL  %s\n" % label)
    sys.stdout.write("        got  %r\n" % (got,))
    sys.stdout.write("        want %r\n" % (want,))
    return -1


def t_fold():
    grp("fold, cross script matching")
    ok("devanagari tokens", fd.fd_toks("मुझे"
                                       " माम"),
       fd.fd_toks("mujhe maam"))
    q = fd.fd_toks("मुझे माम")
    ok("maaf variants agree",
       fd.fd_word("maaf") == fd.fd_word("maaph"), True)
    qt = fd.fd_toks("लग जा गले")
    ok("deva query vs latin title",
       fd.fd_cover(qt, "Lag Ja Gale 8K Video Song"), 1.0)
    ok("latin query vs deva title",
       fd.fd_cover(fd.fd_toks("lag ja gale"),
                   "लग जा गले"
                   " Full Song"), 1.0)
    ok("wrong song scores zero",
       fd.fd_cover(fd.fd_toks("मुझे "
                              "माम"),
                   "Dil De Diya Hai Lyrical"), 0.0)
    ok("stopwords dropped",
       fd.fd_toks("gaana bajao song full video"), [])
    ok("empty query", fd.fd_cover([], "anything"), 0.0)


def t_score():
    grp("search scoring")
    def mk(title, chan, dur, views):
        return {"vid": "a" * 11, "title": title, "chan": chan,
                "dur": dur, "durtxt": "", "live": 0,
                "views": views, "score": 0.0, "rel": 0.0}
    rows = [mk("Random Upload", "Some Guy", 500, 90000000),
            mk("Lag Ja Gale Full Song", "Saregama Music",
               400, 500000)]
    out = ys.ys_rank(rows, "lag ja gale")
    ok("relevance beats view count",
       out[0]["title"], "Lag Ja Gale Full Song")
    rows = [mk("Lag Ja Gale Cover", "Someone", 300, 900000),
            mk("Lag Ja Gale", "Lata - Topic", 300, 900000)]
    out = ys.ys_rank(rows, "lag ja gale")
    ok("original beats cover", out[0]["chan"], "Lata - Topic")
    rows = [mk("Lag Ja Gale status", "X", 40, 900000),
            mk("Lag Ja Gale", "Y", 300, 900000)]
    out = ys.ys_rank(rows, "lag ja gale")
    ok("short status clip loses", out[0]["dur"], 300)
    ok("live filtered", len(ys.ys_filter(
       [{"live": 1, "dur": 300}], 20, 3600, 5)), 0)
    ok("too long filtered", len(ys.ys_filter(
       [{"live": 0, "dur": 99999}], 20, 3600, 5)), 0)


def t_views():
    grp("view count parsing")
    ok("comma", ys.ys_num("1,234,567 views"), 1234567)
    ok("lakh", ys.ys_num("12 लाख बार"),
       1200000)
    ok("crore", ys.ys_num("3.4 करोड "
                          "बार"), 34000000)
    ok("M suffix", ys.ys_num("1.2M views"), 1200000)
    ok("K suffix", ys.ys_num("45K views"), 45000)
    ok("plain", ys.ys_num("850 views"), 850)
    ok("empty", ys.ys_num(""), 0)


def t_sign():
    grp("signed audio urls")
    s = "secret-key"
    vid = "dQw4w9WgXcQ"
    exp = int(time.time()) + 600
    sig = au.au_sign(vid, exp, s)
    ok("valid", au.au_verify(vid, exp, sig, s), 0)
    ok("expired", au.au_verify(vid, 1, sig, s), -1)
    ok("bad sig", au.au_verify(vid, exp, "deadbeef", s), -1)
    ok("wrong key", au.au_verify(vid, exp, sig, "other"), -1)
    ok("other video", au.au_verify("aaaaaaaaaaa", exp, sig, s),
       -1)
    ok("shell injection", au.au_vid_ok("a; rm -rf /"), 0)
    ok("traversal", au.au_vid_ok("../../etc/passwd"), 0)
    ok("too short", au.au_vid_ok("short"), 0)
    ok("good id", au.au_vid_ok("dQw4w9WgXcQ"), 1)


def t_range():
    grp("http range parsing")
    ok("none", hc.range_parse(None, 100), None)
    ok("open ended", hc.range_parse("bytes=0-", 100), (0, 99))
    ok("closed", hc.range_parse("bytes=10-20", 100), (10, 20))
    ok("suffix", hc.range_parse("bytes=-10", 100), (90, 99))
    ok("clamped", hc.range_parse("bytes=90-999", 100), (90, 99))
    ok("past end", hc.range_parse("bytes=500-", 100), (-1, -1))
    ok("junk", hc.range_parse("junk", 100), None)
    ok("reversed", hc.range_parse("bytes=20-10", 100), None)


def t_queue():
    grp("queue state")
    items = []
    i = 0
    while i < 5:
        items.append({"vid": "v" * 10 + str(i),
                      "title": "song %d" % i, "chan": "c",
                      "dur": 200})
        i = i + 1
    u = "amzn1.user.TEST"
    st = qu.qu_set(u, items)
    ok("stored", len(st["items"]), 5)
    st = qu.qu_load(u)
    ok("reloaded", len(st["items"]), 5)
    ok("current", qu.qu_cur(st)["title"], "song 0")
    e, st = qu.qu_step(u, st, 1)
    ok("stepped", e["title"], "song 1")
    ok("persisted idx", qu.qu_load(u)["idx"], 1)
    tok = qu.qu_tok(3, "vvvvvvvvvv3")
    ok("token round trip", qu.qu_untok(tok), (3, "vvvvvvvvvv3"))
    ok("bad token", qu.qu_untok("nope"), (-1, ""))
    ok("none token", qu.qu_untok(None), (-1, ""))
    ok("other user empty",
       len(qu.qu_load("amzn1.user.OTHER")["items"]), 0)
    st = qu.qu_load(u)
    e, st = qu.qu_step(u, st, 99)
    ok("past end", e, None)


def t_cookies():
    grp("cookie parsing")
    good = ("# Netscape HTTP Cookie File\n"
            ".youtube.com\tTRUE\t/\tTRUE\t9999999999\tSID\tv1\n"
            ".youtube.com\tTRUE\t/\tTRUE\t9999999999\tHSID\tv2\n"
            ".youtube.com\tTRUE\t/\tTRUE\t9999999999\tSSID\tv3\n"
            ".youtube.com\tTRUE\t/\tTRUE\t9999999999\tAPISID\tv4\n"
            "#HttpOnly_.youtube.com\tTRUE\t/\tTRUE\t9999999999"
            "\tSAPISID\tv5\n")
    rows = ck.ck_parse(good)
    ok("rows parsed", len(rows), 5)
    ok("httponly row kept", rows[4]["name"], "SAPISID")
    st = ck.ck_check(rows)
    ok("complete login", st["ok"], 1)
    ok("nothing missing", st["missing"], [])
    st2 = ck.ck_check(ck.ck_parse(
        ".youtube.com\tTRUE\t/\tTRUE\t9999999999\tPREF\tx\n"))
    ok("incomplete flagged", st2["ok"], 0)
    rc, err = ck.ck_write("not a cookie file")
    ok("garbage rejected", rc, -1)
    rc, err = ck.ck_write(good)
    ok("good accepted", rc, 0)
    ok("file mode 0600",
       oct(os.stat(ck.ck_path()).st_mode & 0o777), "0o600")
    ok("stat ok", ck.ck_stat()["ok"], 1)
    ck.ck_clear()
    ok("cleared", ck.ck_stat()["present"], 0)


def t_sig():
    grp("alexa signature guards")
    base = "https://s3.amazonaws.com/echo.api/cert"
    ok("good url", sg.sg_url_ok(base), 0)
    ok("http rejected",
       sg.sg_url_ok("http://s3.amazonaws.com/echo.api/c"), -1)
    ok("wrong host",
       sg.sg_url_ok("https://evil.com/echo.api/c"), -1)
    ok("wrong path",
       sg.sg_url_ok("https://s3.amazonaws.com/other/c"), -1)
    ok("wrong port",
       sg.sg_url_ok("https://s3.amazonaws.com:8443/echo.api/c"),
       -1)
    ok("traversal",
       sg.sg_url_ok("https://s3.amazonaws.com/echo.api/../x/c"),
       -1)
    ok("not a string", sg.sg_url_ok(None), -1)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    old = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(time.time() - 600))
    ok("fresh stamp", sg.sg_ts_ok(now), 0)
    ok("stale stamp", sg.sg_ts_ok(old), -1)
    ok("junk stamp", sg.sg_ts_ok("not-a-time"), -1)


def t_cfg():
    grp("config")
    c = cfg.cfg_load()
    ok("defaults present", c["locale"], "hi-IN")
    bad, rc = cfg.cfg_patch(c, {"port": 9090, "nope": 1,
                                "admin_token": "hack",
                                "locale": 5})
    ok("patch saved", rc, 0)
    ok("rejected keys", sorted(bad),
       ["admin_token", "locale", "nope"])
    ok("accepted key", cfg.cfg_load()["port"], 9090)
    ok("secret not leaked",
       "admin_token" in cfg.cfg_public(c), False)
    os.environ["YTA_PORT"] = "7777"
    os.environ["YTA_PUBLIC_HOSTS"] = "a.example, b.example"
    c2 = cfg.cfg_load()
    ok("env int", c2["port"], 7777)
    ok("env list", c2["public_hosts"],
       ["a.example", "b.example"])
    del os.environ["YTA_PORT"]
    del os.environ["YTA_PUBLIC_HOSTS"]


def t_speak():
    grp("locale strings")
    ok("hindi", sp.sp_loc("hi-IN"), "hi-IN")
    ok("prefix match", sp.sp_loc("hi"), "hi-IN")
    ok("unknown falls back", sp.sp_loc("de-DE"), "en-IN")
    ok("none falls back", sp.sp_loc(None), "en-IN")
    ok("key exists", len(sp.sp_get("hi-IN", "welcome")) > 0,
       True)
    ok("missing key", sp.sp_get("hi-IN", "nosuchkey"), "")


def main():
    t_fold()
    t_score()
    t_views()
    t_sign()
    t_range()
    t_queue()
    t_cookies()
    t_sig()
    t_cfg()
    t_speak()
    sys.stdout.write("\n%s\n" % ("-" * 46))
    sys.stdout.write("  %d passed, %d failed\n"
                     % (T_PASS, T_FAIL))
    if T_FAIL > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
