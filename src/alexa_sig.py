import base64
import os
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import log

SG_HOST = "s3.amazonaws.com"
SG_PATH = "/echo.api/"
SG_SAN = "echo-api.amazon.com"
SG_TMO = 8
SG_SKEW = 150
SG_MAX = 1 << 17
SG_OSSL = "openssl"

SG_CACHE = {}
SG_CACHE_MAX = 8


def sg_url_ok(url):
    if type(url) != str:
        return -1
    if len(url) > 1024:
        return -1
    try:
        u = urllib.parse.urlparse(url)
    except ValueError:
        return -1
    if u.scheme.lower() != "https":
        return -1
    if u.hostname == None:
        return -1
    if u.hostname.lower() != SG_HOST:
        return -1
    port = u.port
    if port != None and port != 443:
        return -1
    path = os.path.normpath(u.path)
    if not path.startswith(SG_PATH):
        return -1
    return 0


def sg_fetch(url):
    if url in SG_CACHE:
        return SG_CACHE[url], None
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "ytalexa")
    try:
        r = urllib.request.urlopen(req, timeout=SG_TMO)
        raw = r.read(SG_MAX)
        r.close()
    except urllib.error.HTTPError as e:
        return None, "cert http %d" % e.code
    except urllib.error.URLError as e:
        return None, "cert net %r" % e.reason
    except OSError as e:
        return None, "cert io %r" % e
    if len(SG_CACHE) >= SG_CACHE_MAX:
        SG_CACHE.clear()
    SG_CACHE[url] = raw
    return raw, None


def sg_split(pem):
    txt = pem.decode("ascii", "replace")
    head = "-----BEGIN CERTIFICATE-----"
    tail = "-----END CERTIFICATE-----"
    out = []
    i = 0
    while 1:
        a = txt.find(head, i)
        if a < 0:
            break
        b = txt.find(tail, a)
        if b < 0:
            break
        b = b + len(tail)
        out.append(txt[a:b] + "\n")
        i = b
    return out


def sg_ossl(args, stdin):
    try:
        r = subprocess.run([SG_OSSL] + args, input=stdin,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,
                           timeout=SG_TMO)
    except FileNotFoundError:
        return -1, b"openssl not found"
    except subprocess.TimeoutExpired:
        return -1, b"openssl timeout"
    except OSError as e:
        return -1, str(e).encode("utf-8")
    return r.returncode, r.stdout


def sg_chain(certs, ca):
    d = tempfile.mkdtemp(prefix="ytasig")
    leaf = os.path.join(d, "leaf.pem")
    rest = os.path.join(d, "rest.pem")
    f = open(leaf, "w")
    f.write(certs[0])
    f.close()
    f = open(rest, "w")
    i = 1
    while i < len(certs):
        f.write(certs[i])
        i = i + 1
    f.close()
    args = ["verify"]
    if ca != "":
        args.append("-CAfile")
        args.append(ca)
    if len(certs) > 1:
        args.append("-untrusted")
        args.append(rest)
    args.append(leaf)
    rc, out = sg_ossl(args, None)
    return d, leaf, rc, out


def sg_san_ok(leaf):
    rc, out = sg_ossl(["x509", "-in", leaf, "-noout", "-ext",
                       "subjectAltName"], None)
    if rc != 0:
        return -1
    txt = out.decode("utf-8", "replace")
    if txt.find(SG_SAN) < 0:
        return -1
    return 0


def sg_fresh(leaf):
    rc, out = sg_ossl(["x509", "-in", leaf, "-noout",
                       "-checkend", "0"], None)
    if rc != 0:
        return -1
    return 0


def sg_pubkey(leaf, d):
    pub = os.path.join(d, "pub.pem")
    rc, out = sg_ossl(["x509", "-in", leaf, "-pubkey",
                       "-noout"], None)
    if rc != 0:
        return None
    try:
        f = open(pub, "wb")
        f.write(out)
        f.close()
    except OSError:
        return None
    return pub


def sg_dgst(pub, sig, body, d):
    sp = os.path.join(d, "sig.bin")
    bp = os.path.join(d, "body.bin")
    try:
        f = open(sp, "wb")
        f.write(sig)
        f.close()
        f = open(bp, "wb")
        f.write(body)
        f.close()
    except OSError:
        return -1
    rc, out = sg_ossl(["dgst", "-sha1", "-verify", pub,
                       "-signature", sp, bp], None)
    if rc != 0:
        return -1
    return 0


def sg_wipe(d):
    try:
        names = os.listdir(d)
    except OSError:
        return
    i = 0
    while i < len(names):
        try:
            os.remove(os.path.join(d, names[i]))
        except OSError:
            pass
        i = i + 1
    try:
        os.rmdir(d)
    except OSError:
        pass


def sg_verify(body, sig_b64, cert_url, ca):
    if sg_url_ok(cert_url) != 0:
        return -1, "bad cert url"
    if type(sig_b64) != str or sig_b64 == "":
        return -1, "no signature"
    try:
        sig = base64.b64decode(sig_b64, validate=True)
    except Exception:
        return -1, "signature not base64"
    pem, err = sg_fetch(cert_url)
    if err != None:
        return -1, err
    certs = sg_split(pem)
    if len(certs) == 0:
        return -1, "no certs in bundle"
    d, leaf, rc, out = sg_chain(certs, ca)
    try:
        if rc != 0:
            msg = out.decode("utf-8", "replace").strip()
            return -1, "chain: %s" % msg.replace("\n", " ")[:160]
        if sg_fresh(leaf) != 0:
            return -1, "cert expired"
        if sg_san_ok(leaf) != 0:
            return -1, "cert SAN missing %s" % SG_SAN
        pub = sg_pubkey(leaf, d)
        if pub == None:
            return -1, "no public key"
        if sg_dgst(pub, sig, body, d) != 0:
            return -1, "signature mismatch"
    finally:
        sg_wipe(d)
    return 0, None


def sg_ts_ok(stamp):
    if type(stamp) != str:
        return -1
    t = stamp.strip()
    if t.endswith("Z"):
        t = t[:len(t) - 1]
    if t.find(".") > 0:
        t = t[:t.find(".")]
    try:
        tm = time.strptime(t, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return -1
    import calendar
    got = calendar.timegm(tm)
    now = int(time.time())
    d = now - got
    if d < 0:
        d = -d
    if d > SG_SKEW:
        return -1
    return 0


def sg_check(req, body_json, c):
    if c["verify_sig"] != 1:
        return 0, None
    h = req["hdrs"]
    url = h.get("signaturecertchainurl")
    sig = h.get("signature")
    rc, err = sg_verify(req["body"], sig, url, c.get("sig_ca", ""))
    if rc != 0:
        log.log_add("err", "sig", "reject: %s" % err)
        return -1, err
    rq = body_json.get("request")
    if type(rq) != dict:
        return -1, "no request block"
    if sg_ts_ok(rq.get("timestamp")) != 0:
        log.log_add("err", "sig", "stale timestamp")
        return -1, "stale timestamp"
    return 0, None
