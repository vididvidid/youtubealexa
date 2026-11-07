import threading

import alexa_sig as sg
import audio as au
import cfg
import http_core as hc
import log
import qu
import speak as sp
import yt_radio as yr
import yt_search as ys

AX_SLOT = "query"
AX_INTENT = "PlayIntent"
AX_TRY = 3
AX_SAY_MAX = 48
AX_PATH = "/audio/"
AX_PUNC = ".,!?\u0964 "

AX_FILL = [
    "\u092c\u091c\u093e\u0913", "\u0932\u0917\u093e\u0913",
    "\u0938\u0941\u0928\u093e\u0913", "\u091c\u0930\u093e",
    "\u091a\u0932\u093e\u0913", "\u0915\u0930\u094b",
    "\u0917\u093e\u0928\u093e", "\u0917\u093e\u0928\u0947",
    "\u0935\u093e\u0932\u093e", "\u0935\u093e\u0932\u0940",
    "\u091c\u093c\u0930\u093e", "\u092f\u0939",
    "\u092f\u0947", "\u0926\u094b",
    "play", "song", "the", "this",
]

AX_NEXT = [
    "\u0905\u0917\u0932\u093e", "\u0905\u0917\u0932\u0940",
    "\u092c\u0926\u0932\u094b", "\u0926\u0942\u0938\u0930\u093e",
    "next", "skip",
]

AX_PREV = [
    "\u092a\u093f\u091b\u0932\u093e",
    "\u092a\u093f\u091b\u0932\u0940",
    "\u092a\u0940\u091b\u0947", "\u092a\u0939\u0932\u0947",
    "previous", "back",
]

AX_HALT = [
    "\u0930\u094b\u0915\u094b", "\u0930\u094b\u0915",
    "\u092c\u0902\u0926", "\u0930\u0941\u0915\u094b",
    "\u091a\u0941\u092a", "\u092c\u0938",
    "stop", "pause",
]


def ax_has(tab, w):
    i = 0
    while i < len(tab):
        if tab[i] == w:
            return 1
        i = i + 1
    return 0


def ax_words(q):
    out = []
    raw = q.lower().split()
    i = 0
    while i < len(raw):
        w = raw[i]
        i = i + 1
        while len(w) > 0 and w[len(w) - 1] in AX_PUNC:
            w = w[:len(w) - 1]
        while len(w) > 0 and w[0] in AX_PUNC:
            w = w[1:]
        if w == "":
            continue
        if ax_has(AX_FILL, w) == 1:
            continue
        out.append(w)
    return out


def ax_ctl(q):
    ws = ax_words(q)
    if len(ws) == 0 or len(ws) > 3:
        return 0
    nx = 0
    pv = 0
    ht = 0
    i = 0
    while i < len(ws):
        w = ws[i]
        i = i + 1
        if ax_has(AX_NEXT, w) == 1:
            nx = 1
            continue
        if ax_has(AX_PREV, w) == 1:
            pv = 1
            continue
        if ax_has(AX_HALT, w) == 1:
            ht = 1
            continue
        return 0
    if ht == 1:
        return 3
    if pv == 1:
        return 2
    if nx == 1:
        return 1
    return 0


def ax_dict(node, key):
    v = node.get(key)
    if type(v) != dict:
        return {}
    return v


def ax_user(body):
    s = ax_dict(body, "session")
    u = ax_dict(s, "user")
    v = u.get("userId")
    if type(v) == str and v != "":
        return v
    c = ax_dict(body, "context")
    sy = ax_dict(c, "System")
    u = ax_dict(sy, "user")
    v = u.get("userId")
    if type(v) == str and v != "":
        return v
    return "anon"


def ax_app_ids(body):
    out = []
    s = ax_dict(body, "session")
    a = ax_dict(s, "application")
    if type(a.get("applicationId")) == str:
        out.append(a["applicationId"])
    ctx = ax_dict(body, "context")
    sy = ax_dict(ctx, "System")
    a = ax_dict(sy, "application")
    if type(a.get("applicationId")) == str:
        out.append(a["applicationId"])
    return out


def ax_app_ok(body, c):
    want = c["skill_id"]
    if want == "":
        return 0
    got = ax_app_ids(body)
    i = 0
    while i < len(got):
        if got[i] == want:
            return 0
        i = i + 1
    seen = "none"
    if len(got) > 0:
        seen = got[0]
    log.log_add("err", "alexa", "skill id mismatch %r"
                % seen[:48])
    return -1


def ax_host_ok(req, c):
    hosts = c["public_hosts"]
    if len(hosts) == 0:
        return 0
    got = req["hdrs"].get("host", "")
    got = got.split(":")[0].lower()
    i = 0
    while i < len(hosts):
        if hosts[i].strip().lower() == got:
            return 0
        i = i + 1
    log.log_add("wrn", "alexa", "host not allowed: %r" % got[:64])
    return -1


def ax_base(req, c):
    if c["audio_origin"] != "":
        b = c["audio_origin"]
        while b.endswith("/"):
            b = b[:len(b) - 1]
        return b
    h = req["hdrs"].get("host", "")
    if h == "":
        return ""
    return "https://" + h


def ax_rsp(speech, reprompt, end, dirs):
    r = {}
    b = {}
    if speech != None:
        b["outputSpeech"] = {"type": "PlainText",
                             "text": speech}
    if reprompt != None:
        b["reprompt"] = {"outputSpeech":
                         {"type": "PlainText",
                          "text": reprompt}}
    if end != None:
        b["shouldEndSession"] = end
    if dirs != None:
        b["directives"] = dirs
    r["version"] = "1.0"
    r["response"] = b
    return hc.rsp_json(200, r)


def ax_play_dir(url, token, off, behav, prev, title, sub):
    st = {}
    st["url"] = url
    st["token"] = token
    st["offsetInMilliseconds"] = off
    if behav == "ENQUEUE":
        st["expectedPreviousToken"] = prev
    item = {}
    item["stream"] = st
    item["metadata"] = {"title": title[:140],
                        "subtitle": sub[:140]}
    d = {}
    d["type"] = "AudioPlayer.Play"
    d["playBehavior"] = behav
    d["audioItem"] = item
    return d


def ax_elicit_dir():
    sl = {}
    sl[AX_SLOT] = {"name": AX_SLOT,
                   "confirmationStatus": "NONE"}
    it = {}
    it["name"] = AX_INTENT
    it["confirmationStatus"] = "NONE"
    it["slots"] = sl
    d = {}
    d["type"] = "Dialog.ElicitSlot"
    d["slotToElicit"] = AX_SLOT
    d["updatedIntent"] = it
    return d


def ax_ask(loc, key):
    return ax_rsp(sp.sp_get(loc, key),
                  sp.sp_get(loc, "reprompt"), None,
                  [ax_elicit_dir()])


def ax_stop_dir():
    return {"type": "AudioPlayer.Stop"}


def ax_clear_dir():
    return {"type": "AudioPlayer.ClearQueue",
            "clearBehavior": "CLEAR_ALL"}


def ax_pick_at(st, idx):
    e = qu.qu_at(st, idx)
    if e == None:
        return None, idx
    return e, idx


def ax_bg(fn):
    t = threading.Thread(target=fn)
    t.daemon = True
    t.start()


def ax_warm(user, idx, c, force):
    def run():
        st = qu.qu_load(user)
        n = 0
        while n < 2:
            e = qu.qu_at(st, idx + n)
            n = n + 1
            if e == None:
                break
            au.au_get(e["vid"], c)
        au.au_evict(c["cache_max_mb"])
    if c["prefetch"] != 1 and force == 0:
        return
    ax_bg(run)


def ax_prefetch(user, idx, c):
    ax_warm(user, idx, c, 0)


def ax_fill(user, vid, rows, c):
    def run():
        radio, rerr = yr.yr_radio(vid, c["queue_len"])
        if rerr != None or radio == None or len(radio) == 0:
            log.log_add("wrn", "alexa", "no radio for %s"
                        % vid)
            return
        items = yr.yr_merge(rows, radio, c["queue_len"])
        add, st = qu.qu_extend(user, items)
        log.log_add("inf", "alexa", "radio added %d, queue %d"
                    % (add, len(st["items"])))
    ax_bg(run)


def ax_start(req, user, st, idx, off, c, loc, behav, lead):
    e, idx = ax_pick_at(st, idx)
    if e == None:
        return ax_rsp(sp.sp_get(loc, "failed"), None, True, None)
    qu.qu_mark(user, st, idx, off, 0, 0)
    base = ax_base(req, c)
    url = base + au.au_url(e["vid"], c["url_ttl"],
                           c["hmac_secret"])
    tok = qu.qu_tok(idx, e["vid"])
    d = ax_play_dir(url, tok, off, behav, "", e["title"],
                    e["chan"])
    ax_warm(user, idx, c, 1)
    say = sp.sp_get(loc, "playing")
    if c["say_title"] == 1 and e["title"] != "":
        nm = sp.sp_title(e["title"], AX_SAY_MAX)
        if nm != "":
            say = nm + ". " + say
    if lead != "":
        say = lead + " " + say
    log.log_add("inf", "alexa", "play idx=%d %s %r"
                % (idx, e["vid"], e["title"][:52]))
    return ax_rsp(say, None, True, [d])


def ax_halt(req, user, c, loc):
    st = qu.qu_load(user)
    if qu.qu_cur(st) != None:
        qu.qu_flag(user, st, "own", 1)
    return ax_rsp(None, None, True, [ax_stop_dir()])


def ax_launch(req, user, c, loc):
    st = qu.qu_load(user)
    if st["cut"] == 1 and qu.qu_cur(st) != None:
        log.log_add("inf", "alexa", "resuming after cut at %d"
                    % st["off"])
        return ax_start(req, user, st, st["idx"], st["off"], c,
                        loc, "REPLACE_ALL",
                        sp.sp_get(loc, "cut"))
    return ax_ask(loc, "welcome")


def ax_slot(rq):
    it = ax_dict(rq, "intent")
    slots = ax_dict(it, "slots")
    s = ax_dict(slots, AX_SLOT)
    v = s.get("value")
    if type(v) != str:
        return ""
    return v.strip()


def ax_do_play(req, user, rq, c, loc):
    q = ax_slot(rq)
    if q == "":
        return ax_ask(loc, "huh")
    k = ax_ctl(q)
    if k != 0:
        log.log_add("inf", "alexa", "control %r -> %d"
                    % (q[:32], k))
    if k == 1:
        return ax_do_step(req, user, c, loc, 1)
    if k == 2:
        return ax_do_step(req, user, c, loc, -1)
    if k == 3:
        return ax_halt(req, user, c, loc)
    rows, err = ys.ys_search(q, c["search_lang"],
                             c["search_region"],
                             c["search_want"], c["min_dur"],
                             c["max_dur"])
    if err != None:
        return ax_rsp(sp.sp_get(loc, "failed"), None, True, None)
    if rows == None or len(rows) == 0:
        return ax_ask(loc, "notfound")
    seed = rows[0]
    st = qu.qu_set(user, rows)
    log.log_add("inf", "alexa", "query %r -> seed %d"
                % (q[:52], len(rows)))
    ax_fill(user, seed["vid"], rows, c)
    return ax_start(req, user, st, 0, 0, c, loc, "REPLACE_ALL",
                    "")


def ax_do_step(req, user, c, loc, delta):
    st = qu.qu_load(user)
    if len(st["items"]) == 0:
        return ax_ask(loc, "welcome")
    idx = st["idx"] + delta
    if idx < 0:
        idx = 0
    if idx >= len(st["items"]):
        qu.qu_flag(user, st, "own", 1)
        return ax_rsp(sp.sp_get(loc, "nomore"), None, True,
                      [ax_stop_dir()])
    return ax_start(req, user, st, idx, 0, c, loc,
                    "REPLACE_ALL", "")


def ax_do_resume(req, user, c, loc):
    st = qu.qu_load(user)
    if qu.qu_cur(st) == None:
        return ax_ask(loc, "welcome")
    return ax_start(req, user, st, st["idx"], st["off"], c,
                    loc, "REPLACE_ALL", "")


def ax_intent(req, user, rq, c, loc):
    it = ax_dict(rq, "intent")
    name = it.get("name")
    if type(name) != str:
        name = ""
    if name == AX_INTENT:
        return ax_do_play(req, user, rq, c, loc)
    if name == "AMAZON.NextIntent":
        return ax_do_step(req, user, c, loc, 1)
    if name == "AMAZON.PreviousIntent":
        return ax_do_step(req, user, c, loc, -1)
    if name == "AMAZON.StartOverIntent":
        return ax_do_step(req, user, c, loc, 0)
    if name == "AMAZON.ResumeIntent":
        return ax_do_resume(req, user, c, loc)
    if name == "AMAZON.PauseIntent":
        return ax_halt(req, user, c, loc)
    if name == "AMAZON.StopIntent":
        return ax_halt(req, user, c, loc)
    if name == "AMAZON.CancelIntent":
        return ax_halt(req, user, c, loc)
    if name == "AMAZON.HelpIntent":
        return ax_ask(loc, "help")
    if name == "AMAZON.FallbackIntent":
        return ax_ask(loc, "huh")
    if name.startswith("AMAZON.Loop"):
        return ax_rsp(sp.sp_get(loc, "bye"), None, True, None)
    if name.startswith("AMAZON.Shuffle"):
        return ax_rsp(sp.sp_get(loc, "bye"), None, True, None)
    if name.startswith("AMAZON.Repeat"):
        return ax_do_step(req, user, c, loc, 0)
    log.log_add("wrn", "alexa", "unknown intent %r" % name[:48])
    return ax_ask(loc, "huh")


def ax_evt_near(req, user, rq, c, loc):
    idx, vid = qu.qu_untok(rq.get("token"))
    if idx < 0:
        return ax_rsp(None, None, True, None)
    st = qu.qu_load(user)
    nxt = idx + 1
    e, nxt = ax_pick_at(st, nxt)
    if e == None:
        return ax_rsp(None, None, True, None)
    base = ax_base(req, c)
    url = base + au.au_url(e["vid"], c["url_ttl"],
                           c["hmac_secret"])
    tok = qu.qu_tok(nxt, e["vid"])
    prev = qu.qu_tok(idx, vid)
    d = ax_play_dir(url, tok, 0, "ENQUEUE", prev, e["title"],
                    e["chan"])
    ax_warm(user, nxt, c, 1)
    log.log_add("inf", "alexa", "enqueue idx=%d %s"
                % (nxt, e["vid"]))
    return ax_rsp(None, None, True, [d])


def ax_evt_skip(req, user, rq, c, loc):
    idx, vid = qu.qu_untok(rq.get("token"))
    if idx < 0:
        return ax_rsp(None, None, True, None)
    st = qu.qu_load(user)
    nxt = idx + 1
    if nxt - idx > AX_TRY:
        return ax_rsp(None, None, True, None)
    e, nxt = ax_pick_at(st, nxt)
    if e == None:
        return ax_rsp(None, None, True, None)
    qu.qu_seek(user, st, nxt, 0)
    base = ax_base(req, c)
    url = base + au.au_url(e["vid"], c["url_ttl"],
                           c["hmac_secret"])
    tok = qu.qu_tok(nxt, e["vid"])
    d = ax_play_dir(url, tok, 0, "REPLACE_ALL", "", e["title"],
                    e["chan"])
    ax_warm(user, nxt, c, 1)
    log.log_add("inf", "alexa", "skipping to idx=%d %s"
                % (nxt, e["vid"]))
    return ax_rsp(None, None, True, [d])


def ax_evt(req, user, rq, c, loc):
    typ = rq.get("type")
    off = rq.get("offsetInMilliseconds")
    if type(off) != int:
        off = 0
    if typ == "AudioPlayer.PlaybackNearlyFinished":
        return ax_evt_near(req, user, rq, c, loc)
    if typ == "AudioPlayer.PlaybackStarted":
        idx, vid = qu.qu_untok(rq.get("token"))
        if idx >= 0:
            st = qu.qu_load(user)
            qu.qu_mark(user, st, idx, 0, 0, 0)
            ax_prefetch(user, idx + 1, c)
        return ax_rsp(None, None, True, None)
    if typ == "AudioPlayer.PlaybackFinished":
        idx, vid = qu.qu_untok(rq.get("token"))
        if idx >= 0:
            st = qu.qu_load(user)
            qu.qu_mark(user, st, idx, 0, 0, 0)
        return ax_rsp(None, None, True, None)
    if typ == "AudioPlayer.PlaybackStopped":
        idx, vid = qu.qu_untok(rq.get("token"))
        if idx >= 0:
            st = qu.qu_load(user)
            cut = 1
            if st["own"] == 1:
                cut = 0
            qu.qu_mark(user, st, idx, off, cut, 0)
            if cut == 1:
                log.log_add("wrn", "alexa",
                            "playback cut off at %d ms" % off)
        return ax_rsp(None, None, True, None)
    if typ == "AudioPlayer.PlaybackFailed":
        er = ax_dict(rq, "error")
        log.log_add("err", "alexa", "playback failed: %s %s"
                    % (er.get("type"),
                       str(er.get("message"))[:90]))
        return ax_evt_skip(req, user, rq, c, loc)
    return ax_rsp(None, None, True, None)


def ax_route(req):
    c = cfg.cfg_load()
    if ax_host_ok(req, c) != 0:
        return hc.rsp_err(403, "host not allowed")
    body = hc.req_json(req)
    if body == None:
        return hc.rsp_err(400, "bad json")
    if type(body) != dict:
        return hc.rsp_err(400, "bad json")
    rc, err = sg.sg_check(req, body, c)
    if rc != 0:
        return hc.rsp_err(400, "signature: %s" % err)
    if ax_app_ok(body, c) != 0:
        return hc.rsp_err(403, "wrong skill")
    rq = ax_dict(body, "request")
    typ = rq.get("type")
    if type(typ) != str:
        return hc.rsp_err(400, "no request type")
    user = ax_user(body)
    loc = rq.get("locale")
    if type(loc) != str:
        loc = c["locale"]
    if typ == "LaunchRequest":
        return ax_launch(req, user, c, loc)
    if typ == "IntentRequest":
        return ax_intent(req, user, rq, c, loc)
    if typ.startswith("AudioPlayer."):
        return ax_evt(req, user, rq, c, loc)
    if typ == "PlaybackController.NextCommandIssued":
        return ax_do_step(req, user, c, loc, 1)
    if typ == "PlaybackController.PreviousCommandIssued":
        return ax_do_step(req, user, c, loc, -1)
    if typ == "PlaybackController.PlayCommandIssued":
        return ax_do_resume(req, user, c, loc)
    if typ == "PlaybackController.PauseCommandIssued":
        return ax_halt(req, user, c, loc)
    if typ == "SessionEndedRequest":
        rsn = rq.get("reason")
        if rsn == "ERROR":
            log.log_add("err", "alexa", "session error: %s"
                        % str(rq.get("error"))[:140])
        return hc.rsp_bytes(200, "application/json", b"")
    if typ == "System.ExceptionEncountered":
        log.log_add("err", "alexa", "device exception: %s"
                    % str(rq.get("error"))[:140])
        return ax_rsp(None, None, True, None)
    log.log_add("wrn", "alexa", "unhandled type %r" % typ[:48])
    return ax_rsp(None, None, True, None)


def ax_audio_route(req):
    c = cfg.cfg_load()
    if c["audio_mode"] == "proxy" and c["audio_origin"] != "":
        b = c["audio_origin"]
        while b.endswith("/"):
            b = b[:len(b) - 1]
        q = ""
        if "e" in req["query"] and "s" in req["query"]:
            q = "?e=%d&s=%s" % (hc.q_int(req, "e", 0),
                                hc.q_str(req, "s", ""))
        return hc.rsp_redir(302, b + req["path"] + q)
    name = req["path"][len(AX_PATH):]
    if not name.endswith(au.AU_EXT):
        return hc.rsp_err(404, "not audio")
    vid = name[:len(name) - len(au.AU_EXT)]
    exp = hc.q_int(req, "e", 0)
    sig = hc.q_str(req, "s", "")
    if au.au_verify(vid, exp, sig, c["hmac_secret"]) != 0:
        log.log_add("wrn", "audio", "bad signed url for %r"
                    % vid[:16])
        return hc.rsp_err(403, "bad or expired link")
    rc, err = au.au_get(vid, c)
    if rc != 0:
        return hc.rsp_err(502, "fetch failed")
    au.au_touch(vid)
    return hc.rsp_file(au.au_file(vid), "audio/mp4")


def ax_routes():
    hc.rt_add("POST", "/alexa", ax_route, 0)
    hc.rt_add("GET", AX_PATH, ax_audio_route, 1)
