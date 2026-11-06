import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MD_PAGES = [
    ["SETUP.md", "setup.html", "Setup", "Start here"],
    ["README.md", "readme.html", "Overview", "What this is"],
    ["TEST.md", "test.html", "Test sheet", "Manual checks"],
    ["docs/SETUP-MOBILE.md", "mobile.html", "Phone detail",
     "Full Termux steps"],
    ["docs/ALEXA-SKILL.md", "skill.html", "Alexa detail",
     "Full skill steps"],
    ["docs/SETUP-DOMAIN.md", "domain.html", "Custom domain",
     "Hostnames and tunnels"],
    ["docs/SETUP-VERCEL.md", "vercel.html", "Vercel",
     "Serverless front door"],
    ["SECURITY.md", "security.html", "Security",
     "Threat model"],
    ["VERSION", "version.html", "Changelog",
     "Features and fixes"]
]

MD_RAW = [
    ["docs/interaction-hi-IN.json", "interaction.html",
     "Skill model", "Paste into Amazon"]
]

MD_SLUG = "vididvidid/youtubealexa"
MD_INSTALL_URL = ("https://github.com/" + MD_SLUG
                  + "/releases/latest/download/install.sh")

URL_RE = re.compile(r"(https?://[^\s<>\"')\]\\]+?)([.,;:)\]\\]*)(?=\s|$)")
SLUG_RE = re.compile(r"[^a-z0-9]+")


def esc(t):
    t = t.replace("&", "&amp;")
    t = t.replace("<", "&lt;")
    t = t.replace(">", "&gt;")
    t = t.replace('"', "&quot;")
    return t


def linkify(t):
    return URL_RE.sub(r'<a href="\1">\1</a>\2', t)


def slug(t):
    s = SLUG_RE.sub("-", t.lower()).strip("-")
    if s == "":
        return "x"
    return s


def is_bar(ln, ch):
    s = ln.strip()
    if len(s) < 3:
        return 0
    i = 0
    while i < len(s):
        if s[i] != ch:
            return 0
        i = i + 1
    return 1


def indented(ln):
    if ln.strip() == "":
        return 0
    if ln.startswith("  "):
        return 1
    if ln.startswith("\t"):
        return 1
    return 0


def md_parse(text):
    lines = text.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        if ln.strip() == "":
            i = i + 1
            continue
        if i + 1 < n and indented(ln) == 0:
            if is_bar(lines[i + 1], "="):
                out.append(["h1", ln.strip()])
                i = i + 2
                continue
            if is_bar(lines[i + 1], "-"):
                out.append(["h2", ln.strip()])
                i = i + 2
                continue
        if ln.startswith("## "):
            out.append(["h2", ln[3:].strip()])
            i = i + 1
            continue
        if ln.startswith("# "):
            out.append(["h1", ln[2:].strip()])
            i = i + 1
            continue
        if indented(ln) == 1:
            buf = []
            while i < n:
                if indented(lines[i]) == 1:
                    buf.append(lines[i])
                    i = i + 1
                    continue
                if lines[i].strip() == "":
                    j = i
                    while j < n and lines[j].strip() == "":
                        j = j + 1
                    if j < n and indented(lines[j]) == 1:
                        while i < j:
                            buf.append("")
                            i = i + 1
                        continue
                break
            while len(buf) > 0 and buf[len(buf) - 1].strip() == "":
                buf.pop()
            out.append(["pre", "\n".join(buf)])
            continue
        buf = []
        while i < n:
            if lines[i].strip() == "":
                break
            if indented(lines[i]) == 1:
                break
            if i + 1 < n and (is_bar(lines[i + 1], "=") or
                              is_bar(lines[i + 1], "-")):
                break
            buf.append(lines[i].strip())
            i = i + 1
        out.append(["p", " ".join(buf)])
    return out


def box(t):
    t = t.replace("[ ]", '<span class="box">&#9744;</span>')
    t = t.replace("[x]", '<span class="boxd">&#9745;</span>')
    t = t.replace("[!]", '<span class="boxf">&#9888;</span>')
    return t


def render(blocks):
    html = []
    toc = []
    i = 0
    while i < len(blocks):
        kind = blocks[i][0]
        txt = blocks[i][1]
        i = i + 1
        if kind == "h1":
            html.append("<h1>%s</h1>" % esc(txt))
            continue
        if kind == "h2":
            s = slug(txt)
            toc.append([s, txt])
            html.append('<h2 id="%s"><a href="#%s">%s</a></h2>'
                        % (s, s, esc(txt)))
            continue
        if kind == "pre":
            html.append("<pre>%s</pre>"
                        % box(linkify(esc(txt))))
            continue
        html.append("<p>%s</p>" % linkify(esc(txt)))
    return "\n".join(html), toc


def nav(cur, pages):
    out = ['<nav class="side">']
    out.append('<a class="brand" href="index.html">ytalexa</a>')
    out.append("<ul>")
    i = 0
    while i < len(pages):
        p = pages[i]
        i = i + 1
        on = ""
        if p[1] == cur:
            on = ' class="on"'
        out.append('<li><a href="%s"%s>%s<span>%s</span></a></li>'
                   % (p[1], on, esc(p[2]), esc(p[3])))
    out.append("</ul></nav>")
    return "\n".join(out)


def toc_html(toc):
    if len(toc) < 3:
        return ""
    out = ['<div class="toc"><b>On this page</b><ul>']
    i = 0
    while i < len(toc):
        out.append('<li><a href="#%s">%s</a></li>'
                   % (toc[i][0], esc(toc[i][1])))
        i = i + 1
    out.append("</ul></div>")
    return "\n".join(out)


def shell(title, navhtml, toc, body):
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%s - ytalexa</title>
<meta name="description" content="Hindi voice search for
YouTube audio on an Amazon Echo, served from a phone.">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="top">
<a class="brand" href="index.html">ytalexa</a>
<button id="burger" aria-label="menu">menu</button>
</header>
<div class="wrap">
%s
<main>
%s
<article>
%s
</article>
<footer>ytalexa docs, built from the repo.
<a href="index.html">home</a></footer>
</main>
</div>
<script>
var b=document.getElementById("burger");
var s=document.querySelector(".side");
if(b&&s){b.onclick=function(){s.classList.toggle("open");};}
</script>
</body>
</html>
""" % (esc(title), navhtml, toc, body)


def read(path):
    try:
        f = open(path, "r")
        t = f.read()
        f.close()
    except OSError:
        return None
    return t


def write(path, text):
    try:
        f = open(path, "w")
        f.write(text)
        f.close()
    except OSError as e:
        sys.stderr.write("write failed %s: %r\n" % (path, e))
        return -1
    return 0


def index_page(pages, ver):
    cards = []
    i = 0
    while i < len(pages):
        p = pages[i]
        i = i + 1
        cards.append('<a class="card" href="%s"><b>%s</b>'
                     '<span>%s</span></a>' % (p[1], esc(p[2]),
                                              esc(p[3])))
    body = """<h1>ytalexa</h1>
<p>Hindi voice search for YouTube audio on an Amazon Echo,
served from an old Android phone over Termux. No YouTube Data
API. Your mother says a line from a song and it plays, then
keeps going with a YouTube Music radio queue.</p>
<pre>"अलेक्सा, सुरीली पेटी"
"क्या सुनना है?"
"लग जा गले"</pre>
<h2 id="install">Install</h2>
<p>In Termux, one line:</p>
<pre>curl -fsSL @@I@@ | bash</pre>
<p>Then run the wizard and work down its numbered menu:</p>
<pre>ytalexa setup</pre>
<p>The path in that URL is the repository being installed
from, so use your own if you forked this. Full steps are in
<a href="setup.html">Setup</a>.</p>
<h2 id="docs">Pages</h2>
<div class="cards">%s</div>
<h2 id="why">Why a phone</h2>
<p>googlevideo stream URLs are bound to the IP that requested
them, and this is strictest on music. The machine that extracts
the URL must also fetch the bytes, so a phone on your home wifi
does both from one residential IP. That also keeps the Premium
account away from datacenter abuse heuristics.</p>
<p>Serverless cannot replace it: Vercel caps a function at 300
seconds including streamed output, and Cloudflare's CDN terms
disallow proxying large media that is not hosted on Cloudflare.
See <a href="vercel.html">Vercel</a> and
<a href="domain.html">Custom domain</a>.</p>
<p class="dim">version %s</p>
""" % ("\n".join(cards), esc(ver))
    body = body.replace("@@I@@", MD_INSTALL_URL)
    return shell("Docs", nav("index.html", pages), "", body)


def raw_page(path, title, pages):
    t = read(os.path.join(ROOT, path))
    if t == None:
        return None
    body = ("<h1>%s</h1><p>Copy all of this into the JSON "
            "Editor in the Alexa developer console.</p>"
            "<pre>%s</pre>" % (esc(title), esc(t)))
    return shell(title, nav("interaction.html", pages), "", body)


def main(argv):
    outdir = os.path.join(ROOT, "site")
    if len(argv) > 1:
        outdir = argv[1]
    try:
        os.makedirs(outdir, 0o755)
    except OSError:
        pass
    pages = []
    i = 0
    while i < len(MD_PAGES):
        pages.append(MD_PAGES[i])
        i = i + 1
    i = 0
    while i < len(MD_RAW):
        pages.append(MD_RAW[i])
        i = i + 1

    vtxt = read(os.path.join(ROOT, "src", "ver.py"))
    vstr = "?"
    if vtxt != None:
        m = re.search(r'VER_STR = "([^"]+)"', vtxt)
        if m != None:
            vstr = m.group(1)

    n = 0
    i = 0
    while i < len(MD_PAGES):
        p = MD_PAGES[i]
        i = i + 1
        src = os.path.join(ROOT, p[0])
        t = read(src)
        if t == None:
            sys.stderr.write("skip missing %s\n" % p[0])
            continue
        body, toc = render(md_parse(t))
        html = shell(p[2], nav(p[1], pages), toc_html(toc),
                     body)
        if write(os.path.join(outdir, p[1]), html) == 0:
            n = n + 1

    i = 0
    while i < len(MD_RAW):
        p = MD_RAW[i]
        i = i + 1
        html = raw_page(p[0], p[2], pages)
        if html == None:
            continue
        if write(os.path.join(outdir, p[1]), html) == 0:
            n = n + 1

    if write(os.path.join(outdir, "index.html"),
             index_page(pages, vstr)) == 0:
        n = n + 1
    css = read(os.path.join(ROOT, "tools", "site.css"))
    if css == None:
        sys.stderr.write("missing tools/site.css\n")
        return 1
    if write(os.path.join(outdir, "style.css"), css) == 0:
        n = n + 1
    write(os.path.join(outdir, ".nojekyll"), "")
    sys.stdout.write("wrote %d files to %s\n" % (n, outdir))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
