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
AX_PATH = "/audio/"


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


def ax_app_ok(body, c):
    want = c["skill_id"]
    if want == "":
        return 0
    got = ""
    s = ax_dict(body, "session")
    a = ax_dict(s, "application")
    if type(a.get("applicationId")) == str:
        got = a["applicationId"]
    if got == "":
        ctx = ax_dict(body, "context")
        sy = ax_dict(ctx, "System")
        a = ax_dict(sy, "application")
        if type(a.get("applicationId")) == str:
            got = a["applicationId"]
    if got == want:
        return 0
    log.log_add("err", "alexa", "skill id mismatch %r" % got[:48])
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


def ax_stop_dir():
    return {"type": "AudioPlayer.Stop"}


def ax_clear_dir():
    return {"type": "AudioPlayer.ClearQueue",
            "clearBehavior": "CLEAR_ALL"}


def ax_fetch_at(user, st, idx, c):
    tries = 0
    while tries < AX_TRY:
        e = qu.qu_at(st, idx)
        if e == None:
            return None, idx
        rc, err = au.au_get(e["vid"], c)
        if rc == 0:
            return e, idx
        log.log_add("wrn", "alexa", "skip %s: %s"
                    % (e["vid"], err))
        idx = idx + 1
        tries = tries + 1
    return None, idx


def ax_prefetch(user, idx, c):
    def run():
        st = qu.qu_load(user)
        e = qu.qu_at(st, idx)
        if e != None:
            au.au_get(e["vid"], c)
        au.au_evict(c["cache_max_mb"])
    if c["prefetch"] != 1:
        return
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()


def ax_start(req, user, st, idx, off, c, loc, behav):
    e, idx = ax_fetch_at(user, st, idx, c)
    if e == None:
        return ax_rsp(sp.sp_get(loc, "failed"), None, True, None)
    qu.qu_seek(user, st, idx, off)
    base = ax_base(req, c)
    url = base + au.au_url(e["vid"], c["url_ttl"],
                           c["hmac_secret"])
    tok = qu.qu_tok(idx, e["vid"])
    d = ax_play_dir(url, tok, off, behav, "", e["title"],
                    e["chan"])
    ax_prefetch(user, idx + 1, c)
    say = sp.sp_get(loc, "playing")
    if c["say_title"] == 1 and e["title"] != "":
        say = e["title"][:90] + ". " + say
    log.log_add("inf", "alexa", "play idx=%d %s %r"
                % (idx, e["vid"], e["title"][:52]))
    return ax_rsp(say, None, True, [d])


def ax_launch(req, user, c, loc):
    return ax_rsp(sp.sp_get(loc, "welcome"),
                  sp.sp_get(loc, "reprompt"), False, None)


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
        return ax_rsp(sp.sp_get(loc, "huh"),
                      sp.sp_get(loc, "reprompt"), False, None)
    rows, err = ys.ys_search(q, c["search_lang"],
                             c["search_region"],
                             c["search_want"], c["min_dur"],
                             c["max_dur"])
    if err != None:
        return ax_rsp(sp.sp_get(loc, "failed"), None, True, None)
    if rows == None or len(rows) == 0:
        return ax_rsp(sp.sp_get(loc, "notfound"),
                      sp.sp_get(loc, "reprompt"), False, None)
    seed = rows[0]
    radio, rerr = yr.yr_radio(seed["vid"], c["queue_len"])
    items = yr.yr_merge(rows, radio, c["queue_len"])
    st = qu.qu_set(user, items)
    log.log_add("inf", "alexa", "query %r -> queue %d"
                % (q[:52], len(items)))
    return ax_start(req, user, st, 0, 0, c, loc, "REPLACE_ALL")


def ax_do_step(req, user, c, loc, delta):
    st = qu.qu_load(user)
    if len(st["items"]) == 0:
        return ax_rsp(sp.sp_get(loc, "welcome"),
                      sp.sp_get(loc, "reprompt"), False, None)
    idx = st["idx"] + delta
    if idx < 0:
        idx = 0
    if idx >= len(st["items"]):
        return ax_rsp(sp.sp_get(loc, "nomore"), None, True,
                      [ax_stop_dir()])
    return ax_start(req, user, st, idx, 0, c, loc,
                    "REPLACE_ALL")


def ax_do_resume(req, user, c, loc):
    st = qu.qu_load(user)
    if qu.qu_cur(st) == None:
        return ax_rsp(sp.sp_get(loc, "welcome"),
                      sp.sp_get(loc, "reprompt"), False, None)
    return ax_start(req, user, st, st["idx"], st["off"], c,
                    loc, "REPLACE_ALL")


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
        return ax_rsp(None, None, True, [ax_stop_dir()])
    if name == "AMAZON.StopIntent":
        return ax_rsp(None, None, True, [ax_stop_dir()])
    if name == "AMAZON.CancelIntent":
        return ax_rsp(None, None, True, [ax_stop_dir()])
    if name == "AMAZON.HelpIntent":
        return ax_rsp(sp.sp_get(loc, "help"),
                      sp.sp_get(loc, "reprompt"), False, None)
    if name == "AMAZON.FallbackIntent":
        return ax_rsp(sp.sp_get(loc, "huh"),
                      sp.sp_get(loc, "reprompt"), False, None)
    if name.startswith("AMAZON.Loop"):
        return ax_rsp(sp.sp_get(loc, "bye"), None, True, None)
    if name.startswith("AMAZON.Shuffle"):
        return ax_rsp(sp.sp_get(loc, "bye"), None, True, None)
    if name.startswith("AMAZON.Repeat"):
        return ax_do_step(req, user, c, loc, 0)
    log.log_add("wrn", "alexa", "unknown intent %r" % name[:48])
    return ax_rsp(sp.sp_get(loc, "huh"),
                  sp.sp_get(loc, "reprompt"), False, None)


def ax_evt_near(req, user, rq, c, loc):
    idx, vid = qu.qu_untok(rq.get("token"))
    if idx < 0:
        return ax_rsp(None, None, True, None)
    st = qu.qu_load(user)
    nxt = idx + 1
    e, nxt = ax_fetch_at(user, st, nxt, c)
    if e == None:
        return ax_rsp(None, None, True, None)
    base = ax_base(req, c)
    url = base + au.au_url(e["vid"], c["url_ttl"],
                           c["hmac_secret"])
    tok = qu.qu_tok(nxt, e["vid"])
    prev = qu.qu_tok(idx, vid)
    d = ax_play_dir(url, tok, 0, "ENQUEUE", prev, e["title"],
                    e["chan"])
    ax_prefetch(user, nxt + 1, c)
    log.log_add("inf", "alexa", "enqueue idx=%d %s"
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
            ax_prefetch(user, idx + 1, c)
        return ax_rsp(None, None, True, None)
    if typ == "AudioPlayer.PlaybackStopped":
        idx, vid = qu.qu_untok(rq.get("token"))
        if idx >= 0:
            st = qu.qu_load(user)
            qu.qu_seek(user, st, idx, off)
        return ax_rsp(None, None, True, None)
    if typ == "AudioPlayer.PlaybackFailed":
        er = ax_dict(rq, "error")
        log.log_add("err", "alexa", "playback failed: %s %s"
                    % (er.get("type"), str(er.get("message"))[:90]))
        return ax_rsp(None, None, True, None)
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
        return ax_rsp(None, None, True, [ax_stop_dir()])
    if typ == "SessionEndedRequest":
        return ax_rsp(None, None, True, None)
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
