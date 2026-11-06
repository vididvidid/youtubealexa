import json
import re
import urllib.error
import urllib.parse
import urllib.request

import fold as fd
import log

YS_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
YS_CVER = "2.20261001.00.00"
YS_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
         "AppleWebKit/537.36 (KHTML, like Gecko) "
         "Chrome/131.0.0.0 Safari/537.36")
YS_API = "https://www.youtube.com/youtubei/v1/search"
YS_WEB = "https://www.youtube.com/results"
YS_VIDONLY = "EgIQAQ%3D%3D"
YS_TMO = 12
YS_WANT = 20
YS_MIN_DUR = 20
YS_MAX_DUR = 3600

YS_INIT_RE = re.compile(r"ytInitialData\s*=\s*(\{.*?\});")


def ys_http(url, body, hdrs):
    req = urllib.request.Request(url, data=body)
    for k in hdrs:
        req.add_header(k, hdrs[k])
    try:
        r = urllib.request.urlopen(req, timeout=YS_TMO)
        raw = r.read()
        r.close()
    except urllib.error.HTTPError as e:
        return None, "http %d" % e.code
    except urllib.error.URLError as e:
        return None, "net %r" % e.reason
    except OSError as e:
        return None, "io %r" % e
    return raw, None


def ys_hdrs(lang, region):
    h = {}
    h["User-Agent"] = YS_UA
    h["Accept-Language"] = "%s-%s,%s;q=0.9" % (lang, region, lang)
    h["Origin"] = "https://www.youtube.com"
    h["Referer"] = "https://www.youtube.com/"
    return h


def ys_ctx(lang, region):
    cl = {}
    cl["clientName"] = "WEB"
    cl["clientVersion"] = YS_CVER
    cl["hl"] = lang
    cl["gl"] = region
    return {"client": cl}


def ys_innertube(q, lang, region):
    url = YS_API + "?key=" + YS_KEY + "&prettyPrint=false"
    pay = {}
    pay["context"] = ys_ctx(lang, region)
    pay["query"] = q
    pay["params"] = urllib.parse.unquote(YS_VIDONLY)
    body = json.dumps(pay).encode("utf-8")
    h = ys_hdrs(lang, region)
    h["Content-Type"] = "application/json"
    raw, err = ys_http(url, body, h)
    if err != None:
        return None, err
    try:
        return json.loads(raw.decode("utf-8")), None
    except (ValueError, UnicodeDecodeError) as e:
        return None, "parse %r" % e


def ys_html(q, lang, region):
    qs = urllib.parse.urlencode({"search_query": q,
                                 "hl": lang, "gl": region,
                                 "sp": "EgIQAQ=="})
    raw, err = ys_http(YS_WEB + "?" + qs, None,
                       ys_hdrs(lang, region))
    if err != None:
        return None, err
    try:
        txt = raw.decode("utf-8", "replace")
    except UnicodeDecodeError as e:
        return None, "decode %r" % e
    m = YS_INIT_RE.search(txt)
    if m == None:
        return None, "no ytInitialData"
    try:
        return json.loads(m.group(1)), None
    except ValueError as e:
        return None, "parse %r" % e


def ys_text(node):
    if node == None:
        return ""
    if type(node) != dict:
        return ""
    if "simpleText" in node:
        v = node["simpleText"]
        if type(v) == str:
            return v
        return ""
    runs = node.get("runs")
    if type(runs) != list:
        return ""
    out = ""
    i = 0
    while i < len(runs):
        r = runs[i]
        i = i + 1
        if type(r) != dict:
            continue
        t = r.get("text")
        if type(t) == str:
            out = out + t
    return out


def ys_dur(txt):
    if txt == "":
        return 0
    parts = txt.strip().split(":")
    if len(parts) < 2 or len(parts) > 3:
        return 0
    tot = 0
    i = 0
    while i < len(parts):
        p = parts[i].strip()
        i = i + 1
        if not p.isdigit():
            return 0
        tot = tot * 60 + int(p)
    return tot


def ys_collect(data, key):
    out = []
    if data == None:
        return out
    stack = [data]
    while len(stack) > 0:
        node = stack.pop()
        if type(node) == dict:
            for k in node:
                if k == key:
                    v = node[k]
                    if type(v) == dict:
                        out.append(v)
                    continue
                v = node[k]
                if type(v) == dict or type(v) == list:
                    stack.append(v)
            continue
        if type(node) == list:
            i = 0
            while i < len(node):
                v = node[i]
                i = i + 1
                if type(v) == dict or type(v) == list:
                    stack.append(v)
    return out


def ys_is_live(vr):
    bl = vr.get("badges")
    if type(bl) == list:
        i = 0
        while i < len(bl):
            b = bl[i]
            i = i + 1
            if type(b) != dict:
                continue
            mb = b.get("metadataBadgeRenderer")
            if type(mb) != dict:
                continue
            s = str(mb.get("style", ""))
            if s.find("LIVE") >= 0:
                return 1
    if "upcomingEventData" in vr:
        return 1
    return 0


YS_SUF = {
    "k": 1000, "m": 1000000, "b": 1000000000,
    "hazar": 1000, "hajar": 1000,
    "lakh": 100000, "lac": 100000,
    "crore": 10000000, "cr": 10000000
}

YS_SUF_HI = [
    ["\u0939\u091c\u093e\u0930", 1000],
    ["\u0932\u093e\u0916", 100000],
    ["\u0915\u0930\u094b\u0921", 10000000]
]

YS_GOOD_CHAN = [
    "- topic", "t-series", "saregama", "sony music",
    "zee music", "tips official", "tips music", "venus",
    "shemaroo", "ultra bollywood", "speed records",
    "yrf", "eros now music", "times music", "sa re ga ma"
]

YS_GOOD_TITLE = [
    "full song", "full audio", "audio song", "official audio",
    "jukebox", "lyrical"
]

YS_BAD_TITLE = [
    "whatsapp status", "status video", "ringtone", "shorts",
    "reels", "mashup", "dj remix", "slowed", "reverb",
    "instrumental", "karaoke", "tutorial", "how to",
    "dance cover", "trailer", "teaser", "making of",
    "behind the scenes", "review", "reaction",
    "cover", "acoustic", "unplugged", "reprise",
    "recreated", "revisited", "tribute", "medley",
    "\u0915\u0935\u0930", "\u090f\u0915\u0941\u0938\u094d\u091f\u093f\u0915"
]

YS_W_DUR = [
    [150, 600, 30],
    [600, 1200, 12],
    [1200, 1800, -5],
    [90, 150, -8],
    [0, 90, -45],
    [1800, 99999, -28]
]

YS_W_TOPIC = 26
YS_W_CHAN = 14
YS_W_TITLE = 9
YS_W_BAD = -24
YS_W_RANK = -6.0
YS_W_VIEW = 2.5
YS_W_REL = 48.0


def ys_num(txt):
    if txt == "":
        return 0
    t = txt.lower().replace(",", "").replace("\u00a0", " ")
    i = 0
    while i < len(YS_SUF_HI):
        pair = YS_SUF_HI[i]
        i = i + 1
        if t.find(pair[0]) < 0:
            continue
        head = t.split(pair[0])[0].strip()
        v = ys_float(head)
        if v <= 0:
            return 0
        return int(v * pair[1])
    words = t.replace("(", " ").replace(")", " ").split()
    i = 0
    while i < len(words):
        w = words[i]
        i = i + 1
        if w in YS_SUF and i >= 2:
            v = ys_float(words[i - 2])
            if v > 0:
                return int(v * YS_SUF[w])
        v = ys_float(w)
        if v <= 0:
            continue
        tail = ""
        if len(w) > 0:
            tail = w[len(w) - 1:]
        if tail in YS_SUF:
            return int(v * YS_SUF[tail])
        return int(v)
    return 0


def ys_float(w):
    out = ""
    i = 0
    while i < len(w):
        c = w[i]
        i = i + 1
        if c.isdigit() or c == ".":
            out = out + c
            continue
        break
    if out == "" or out == ".":
        return 0.0
    try:
        return float(out)
    except ValueError:
        return 0.0


def ys_views(vr):
    n = ys_num(ys_text(vr.get("viewCountText")))
    if n > 0:
        return n
    return ys_num(ys_text(vr.get("shortViewCountText")))


def ys_hit(hay, tab):
    i = 0
    n = 0
    while i < len(tab):
        if hay.find(tab[i]) >= 0:
            n = n + 1
        i = i + 1
    return n


def ys_score(e, rank, qtok):
    sc = 0.0
    e["rel"] = fd.fd_cover(qtok, e["title"])
    sc = sc + YS_W_REL * e["rel"]
    d = e["dur"]
    i = 0
    while i < len(YS_W_DUR):
        row = YS_W_DUR[i]
        i = i + 1
        if d >= row[0] and d < row[1]:
            sc = sc + row[2]
            break
    t = e["title"].lower()
    c = e["chan"].lower()
    if c.endswith("- topic"):
        sc = sc + YS_W_TOPIC
    sc = sc + YS_W_CHAN * ys_hit(c, YS_GOOD_CHAN)
    sc = sc + YS_W_TITLE * ys_hit(t, YS_GOOD_TITLE)
    sc = sc + YS_W_BAD * ys_hit(t, YS_BAD_TITLE)
    if e["views"] > 0:
        import math
        sc = sc + YS_W_VIEW * math.log10(e["views"])
    sc = sc + YS_W_RANK * rank
    return sc


def ys_rank(rows, q):
    qtok = fd.fd_toks(q)
    i = 0
    while i < len(rows):
        rows[i]["score"] = ys_score(rows[i], i, qtok)
        i = i + 1
    out = sorted(rows, key=lambda r: r["score"], reverse=True)
    return out


def ys_entry(vr):
    vid = vr.get("videoId")
    if type(vid) != str:
        return None
    if len(vid) != 11:
        return None
    e = {}
    e["vid"] = vid
    e["title"] = ys_text(vr.get("title"))
    e["chan"] = ys_text(vr.get("ownerText"))
    e["durtxt"] = ys_text(vr.get("lengthText"))
    e["dur"] = ys_dur(e["durtxt"])
    e["live"] = ys_is_live(vr)
    e["views"] = ys_views(vr)
    e["score"] = 0.0
    e["rel"] = 0.0
    return e


def ys_dedup(rows):
    seen = {}
    out = []
    i = 0
    while i < len(rows):
        e = rows[i]
        i = i + 1
        if e["vid"] in seen:
            continue
        seen[e["vid"]] = 1
        out.append(e)
    return out


def ys_parse(data, want):
    vrs = ys_collect(data, "videoRenderer")
    out = []
    i = 0
    while i < len(vrs):
        e = ys_entry(vrs[i])
        i = i + 1
        if e == None:
            continue
        out.append(e)
        if len(out) >= want * 3:
            break
    return ys_dedup(out)


def ys_ok(e, lo, hi):
    if e["live"] == 1:
        return 0
    if e["dur"] < lo:
        return 0
    if e["dur"] > hi:
        return 0
    return 1


def ys_filter(rows, lo, hi, want):
    out = []
    i = 0
    while i < len(rows):
        e = rows[i]
        i = i + 1
        if ys_ok(e, lo, hi) == 0:
            continue
        out.append(e)
        if len(out) >= want:
            break
    return out


def ys_search(q, lang, region, want, lo, hi):
    q = q.strip()
    if q == "":
        return None, "empty query"
    if want < 1:
        want = YS_WANT
    data, err = ys_innertube(q, lang, region)
    src = "innertube"
    if err != None:
        log.log_add("wrn", "search", "innertube failed: %s" % err)
        data, err = ys_html(q, lang, region)
        src = "html"
        if err != None:
            log.log_add("err", "search", "html failed: %s" % err)
            return None, err
    rows = ys_parse(data, want)
    if len(rows) == 0:
        log.log_add("wrn", "search", "%s gave nothing for %r"
                    % (src, q))
        return [], None
    out = ys_rank(ys_filter(rows, lo, hi, want), q)
    if len(out) == 0:
        log.log_add("wrn", "search",
                    "all %d results filtered for %r"
                    % (len(rows), q))
        return [], None
    log.log_add("inf", "search", "%s %r -> %d of %d, top %s %r"
                % (src, q, len(out), len(rows), out[0]["vid"],
                   out[0]["title"][:48]))
    return out, None


def ys_pick(rows):
    if rows == None:
        return None
    if len(rows) == 0:
        return None
    return rows[0]
