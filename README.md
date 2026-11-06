ytalexa
=======

Hindi voice search for YouTube audio on an Amazon Echo, served
from an always-on Android phone running Termux.

  "अलेक्सा, गाना"  ->  "क्या सुनना है?"  ->  "मुझे माफ करना"

The Echo then plays the matching track and keeps going with a
YouTube Music radio queue built from it.

No YouTube Data API. Search goes through YouTube's own InnerTube
endpoints, audio comes from yt-dlp using the owner's YouTube
Premium cookies, which exempts the account from GVS PO tokens.


why a phone and not a cloud function
------------------------------------

googlevideo stream URLs are bound to the IP that requested them,
and this is strictest on music. The machine that extracts the URL
must also be the machine that fetches the bytes. A phone on your
home wifi does both from one residential IP, which also keeps the
Premium account away from datacenter abuse heuristics.

Serverless also cannot help: Vercel caps a function at 300s
including streamed output, and Cloudflare's CDN terms disallow
proxying large media that is not hosted on Cloudflare.


install
-------

In Termux, one line:

  curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/\
install.sh | bash

Then:

  ytalexa setup

That opens a numbered terminal menu. Work down it. Full steps
are in SETUP.md, and the same docs are published as a website
by the pages workflow, which is easier to read on a phone.


layout
------

  VERSION            feature plan and per release change log
  README.md          this file
  SETUP.md           one linear setup path, phone then amazon
  TEST.md            manual checks that need real hardware
  install.sh         curl installer for termux
  bin/cli.py         the ytalexa command
  bin/serve.py       entry point for the phone
  src/cfg.py         json config, secrets, atomic save
  src/db.py          sqlite handle, kv table
  src/log.py         levelled logging into sqlite
  src/http_core.py   stdlib http server, routes, range, pump
  src/routes_ui.py   console and json api
  src/web/           single page console
  src/ver.py         version string
  src/wizard.py      terminal setup wizard
  docs/              setup guides and the alexa skill model
  tools/             site generator, checks, tests, deb builder
  api/               vercel entry point
  cache/             extracted audio, created at runtime


run it
------

  ytalexa setup      guided, recommended
  ytalexa start      background
  ytalexa serve      foreground
  ytalexa status     what is and is not set up
  ytalexa selftest   check the pipeline end to end

Or without installing:

  python3 bin/serve.py

Needs python3, openssl, yt-dlp and ytmusicapi. The console
itself is stdlib only.

The admin token is generated on first start and printed to the
terminal every time the server starts. Open the console at
http://127.0.0.1:8080/ui/ and paste it.

Config and database live in $YTA_HOME, or ~/.ytalexa when that
is unset.


security
--------

  * server binds 127.0.0.1 only
  * every /api route needs the admin token
  * /health is the one open route, for tunnel checks
  * config file is mode 0600, it holds live Premium cookies
    once F05 lands, so keep it off /sdcard
  * the tunnel must mount only /alexa and /audio, never /ui
    or /api
