import log

YR_LIMIT = 25


def yr_dur(ms, txt):
    if type(ms) == int and ms > 0:
        return ms // 1000
    if type(txt) != str:
        return 0
    parts = txt.split(":")
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


def yr_artist(t):
    a = t.get("artists")
    if type(a) != list:
        return ""
    out = []
    i = 0
    while i < len(a):
        n = a[i]
        i = i + 1
        if type(n) != dict:
            continue
        v = n.get("name")
        if type(v) == str:
            out.append(v)
    return ", ".join(out)


def yr_row(t):
    if type(t) != dict:
        return None
    vid = t.get("videoId")
    if type(vid) != str:
        return None
    if len(vid) != 11:
        return None
    e = {}
    e["vid"] = vid
    ttl = t.get("title")
    if type(ttl) != str:
        ttl = ""
    e["title"] = ttl
    e["chan"] = yr_artist(t)
    e["dur"] = yr_dur(t.get("lengthSeconds"), t.get("length"))
    return e


def yr_radio(vid, limit):
    if limit < 2:
        limit = YR_LIMIT
    try:
        import ytmusicapi
    except ImportError:
        log.log_add("wrn", "radio", "ytmusicapi not installed")
        return [], "ytmusicapi missing"
    try:
        yt = ytmusicapi.YTMusic()
    except Exception as e:
        log.log_add("wrn", "radio", "init failed %r" % e)
        return [], "init failed"
    try:
        res = yt.get_watch_playlist(videoId=vid, radio=True,
                                    limit=limit)
    except Exception as e:
        log.log_add("wrn", "radio", "watch playlist %r" % e)
        return [], "lookup failed"
    if type(res) != dict:
        return [], "bad reply"
    tracks = res.get("tracks")
    if type(tracks) != list:
        return [], "no tracks"
    out = []
    i = 0
    while i < len(tracks):
        e = yr_row(tracks[i])
        i = i + 1
        if e == None:
            continue
        out.append(e)
    log.log_add("inf", "radio", "radio for %s -> %d tracks"
                % (vid, len(out)))
    return out, None


def yr_merge(seed, radio, want):
    out = []
    seen = {}
    i = 0
    while i < len(seed):
        e = seed[i]
        i = i + 1
        if e["vid"] in seen:
            continue
        seen[e["vid"]] = 1
        out.append(e)
        break
    i = 0
    while i < len(radio) and len(out) < want:
        e = radio[i]
        i = i + 1
        if e["vid"] in seen:
            continue
        seen[e["vid"]] = 1
        out.append(e)
    i = 1
    while i < len(seed) and len(out) < want:
        e = seed[i]
        i = i + 1
        if e["vid"] in seen:
            continue
        seen[e["vid"]] = 1
        out.append(e)
    return out
