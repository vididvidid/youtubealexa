import hmac
import json
import os
import socket
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs
from urllib.parse import unquote
from urllib.parse import urlparse

import log

BODY_MAX = 1 << 20
SEND_CHUNK = 1 << 16
TOK_HDR = "X-Admin-Token"

RT_TAB = []

MIME_TAB = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
    ".md": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg"
}


def mime_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in MIME_TAB:
        return MIME_TAB[ext]
    return "application/octet-stream"


def rt_add(meth, path, fn, pfx):
    r = {}
    r["meth"] = meth
    r["path"] = path
    r["fn"] = fn
    r["pfx"] = pfx
    RT_TAB.append(r)


def rt_clear():
    while len(RT_TAB) > 0:
        RT_TAB.pop()


def rt_find(meth, path):
    i = 0
    hit = None
    while i < len(RT_TAB):
        r = RT_TAB[i]
        i = i + 1
        if r["meth"] != meth:
            continue
        if r["pfx"] == 0:
            if r["path"] == path:
                return r
            continue
        if not path.startswith(r["path"]):
            continue
        if hit == None or len(r["path"]) > len(hit["path"]):
            hit = r
    return hit


def rsp_new(code, ctype):
    r = {}
    r["code"] = code
    r["type"] = ctype
    r["hdrs"] = {}
    r["body"] = None
    r["file"] = None
    r["pump"] = None
    r["size"] = -1
    r["loc"] = None
    return r


def rsp_bytes(code, ctype, data):
    r = rsp_new(code, ctype)
    r["body"] = data
    return r


def rsp_text(code, txt):
    return rsp_bytes(code, "text/plain; charset=utf-8",
                     txt.encode("utf-8"))


def rsp_html(code, txt):
    return rsp_bytes(code, "text/html; charset=utf-8",
                     txt.encode("utf-8"))


def rsp_json(code, obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    return rsp_bytes(code, "application/json", data)


def rsp_err(code, why):
    return rsp_json(code, {"ok": 0, "err": why})


def rsp_file(path, ctype):
    if ctype == None:
        ctype = mime_of(path)
    r = rsp_new(200, ctype)
    r["file"] = path
    return r


def rsp_pump(ctype, size, fn):
    r = rsp_new(200, ctype)
    r["pump"] = fn
    r["size"] = size
    return r


def rsp_redir(code, loc):
    r = rsp_new(code, "text/plain; charset=utf-8")
    r["loc"] = loc
    r["body"] = b""
    return r


def tok_check(req, want):
    if want == "":
        return 0
    got = req["hdrs"].get(TOK_HDR.lower())
    if got == None:
        got = q_str(req, "t", "")
    if got == "":
        return -1
    if hmac.compare_digest(got, want):
        return 0
    return -1


def q_str(req, name, dflt):
    v = req["query"].get(name)
    if v == None:
        return dflt
    if len(v) == 0:
        return dflt
    return v[0]


def q_int(req, name, dflt):
    v = q_str(req, name, None)
    if v == None:
        return dflt
    try:
        return int(v)
    except ValueError:
        return dflt


def req_json(req):
    if req["body"] == None:
        return None
    if len(req["body"]) == 0:
        return None
    try:
        return json.loads(req["body"].decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def range_parse(hdr, total):
    if hdr == None:
        return None
    if not hdr.startswith("bytes="):
        return None
    spec = hdr[6:].split(",")[0].strip()
    if spec == "":
        return None
    dash = spec.find("-")
    if dash < 0:
        return None
    lo_s = spec[:dash].strip()
    hi_s = spec[dash + 1:].strip()
    if lo_s == "":
        if hi_s == "":
            return None
        try:
            n = int(hi_s)
        except ValueError:
            return None
        if n <= 0:
            return None
        if n > total:
            n = total
        return total - n, total - 1
    try:
        lo = int(lo_s)
    except ValueError:
        return None
    if lo >= total:
        return -1, -1
    if hi_s == "":
        return lo, total - 1
    try:
        hi = int(hi_s)
    except ValueError:
        return None
    if hi >= total:
        hi = total - 1
    if hi < lo:
        return None
    return lo, hi


class HttpH(BaseHTTPRequestHandler):
    server_version = "ytalexa"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        self.go("GET", 1)

    def do_POST(self):
        self.go("POST", 1)

    def do_HEAD(self):
        self.go("GET", 0)

    def hdr_map(self):
        m = {}
        for k in self.headers:
            m[k.lower()] = self.headers[k]
        return m

    def body_read(self):
        n = 0
        raw = self.headers.get("Content-Length")
        if raw != None:
            try:
                n = int(raw)
            except ValueError:
                return b"", -1
        if n < 0:
            return b"", -1
        if n > BODY_MAX:
            return b"", -1
        if n == 0:
            return b"", 0
        try:
            return self.rfile.read(n), 0
        except OSError:
            return b"", -1

    def mkreq(self, meth):
        u = urlparse(self.path)
        req = {}
        req["meth"] = meth
        req["path"] = unquote(u.path)
        req["query"] = parse_qs(u.query)
        req["hdrs"] = self.hdr_map()
        req["peer"] = self.client_address[0]
        body, rc = self.body_read()
        if rc != 0:
            return None
        req["body"] = body
        return req

    def go(self, meth, send):
        req = self.mkreq(meth)
        if req == None:
            self.emit(rsp_err(413, "body too large"), send)
            return
        rt = rt_find(meth, req["path"])
        if rt == None:
            self.emit(rsp_err(404, "no route"), send)
            return
        try:
            rsp = rt["fn"](req)
        except Exception as e:
            log.log_add("err", "http", "%s %s: %r"
                        % (meth, req["path"], e))
            self.emit(rsp_err(500, "handler failed"), send)
            return
        if rsp == None:
            rsp = rsp_err(500, "empty reply")
        self.emit(rsp, send)

    def put_hdrs(self, rsp, clen):
        self.send_header("Content-Type", rsp["type"])
        if clen >= 0:
            self.send_header("Content-Length", str(clen))
        if rsp["loc"] != None:
            self.send_header("Location", rsp["loc"])
        for k in rsp["hdrs"]:
            self.send_header(k, rsp["hdrs"][k])
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def emit(self, rsp, send):
        if rsp["file"] != None:
            self.emit_file(rsp, send)
            return
        if rsp["pump"] != None:
            self.emit_pump(rsp, send)
            return
        data = rsp["body"]
        if data == None:
            data = b""
        self.send_response(rsp["code"])
        self.put_hdrs(rsp, len(data))
        if send == 1 and len(data) > 0:
            self.wsafe(data)

    def emit_file(self, rsp, send):
        path = rsp["file"]
        try:
            total = os.path.getsize(path)
            f = open(path, "rb")
        except OSError:
            self.emit(rsp_err(404, "gone"), send)
            return
        rng = range_parse(self.headers.get("Range"), total)
        lo = 0
        hi = total - 1
        code = 200
        if rng != None:
            if rng[0] < 0:
                f.close()
                self.send_response(416)
                self.send_header("Content-Range",
                                 "bytes */%d" % total)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            lo = rng[0]
            hi = rng[1]
            code = 206
        n = hi - lo + 1
        self.send_response(code)
        if code == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d"
                             % (lo, hi, total))
        self.send_header("Accept-Ranges", "bytes")
        self.put_hdrs(rsp, n)
        if send == 0:
            f.close()
            return
        f.seek(lo)
        left = n
        while left > 0:
            want = SEND_CHUNK
            if left < want:
                want = left
            buf = f.read(want)
            if len(buf) == 0:
                break
            if self.wsafe(buf) != 0:
                break
            left = left - len(buf)
        f.close()

    def emit_pump(self, rsp, send):
        self.send_response(rsp["code"])
        self.send_header("Accept-Ranges", "none")
        self.put_hdrs(rsp, rsp["size"])
        if send == 0:
            return
        try:
            rsp["pump"](self.wsafe)
        except Exception as e:
            log.log_add("wrn", "http", "pump broke: %r" % e)

    def wsafe(self, buf):
        try:
            self.wfile.write(buf)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return -1
        return 0


def srv_make(host, port):
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer.daemon_threads = True
    try:
        return ThreadingHTTPServer((host, port), HttpH)
    except OSError as e:
        log.log_add("err", "http", "bind %s:%d failed: %r"
                    % (host, port, e))
        return None


def srv_run(srv):
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    srv.server_close()
