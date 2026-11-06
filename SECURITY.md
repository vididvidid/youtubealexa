Security
========

This is a personal, self hosted hobby project. It runs on one
phone on a home network and serves one household. There is no
multi user model and no server anyone else logs into.

What follows is the honest threat model rather than a policy
template, because the thing worth protecting here is a live
Google session.


Supported versions
------------------

The latest release only. There are no backports. If something
breaks, update:

  ytalexa update

which upgrades yt-dlp and ytmusicapi, the two parts that break
when YouTube changes something.


What is actually sensitive
--------------------------

  cookies.txt     your YouTube Premium session. These are live
                  credentials for your Google account. Anyone
                  holding them is logged in as you.
  admin_token     unlocks the web console, which can read logs
                  and change config.
  hmac_secret     signs the audio URLs handed to the Echo.

All three live in $YTA_HOME, which defaults to ~/.ytalexa. The
directory is mode 0700 and the files are written 0600.

yt-dlp rewrites whatever cookie jar it is given, so it is
never handed the master file. Each download gets a 0600 copy
at $YTA_HOME/ckrun-<videoid>.txt, which is deleted when the
download ends, on both the success and the failure path. A
yt-dlp that corrupts or truncates its jar damages the copy
and nothing else.

Never put cookies on /sdcard or in any shared storage. Any
Android app holding the storage permission can read that, and
these are credentials, not preferences. The loader prints a
reminder to delete the copy you imported.

Nothing sensitive is ever sent to the browser. The config API
strips admin_token and hmac_secret from every response, and
refuses to set them.


How the server is exposed
-------------------------

The server binds 127.0.0.1 only. It is reachable from the
internet solely through whatever tunnel you run.

The tunnel must mount exactly two paths:

  /alexa        the Alexa skill endpoint
  /audio/...    signed, expiring audio URLs

It must NOT mount /ui or /api. bin/tunnel.sh sets up Tailscale
Funnel with only those two paths, and the Cloudflare example in
docs/SETUP-DOMAIN.md ends with a catch all 404 rule for the
same reason. If you write your own ingress, keep that rule.

Verify it after any tunnel change:

  curl -i https://YOUR-HOST/ui/
  curl -i https://YOUR-HOST/api/status

Both must fail. If the console answers from the internet,
anyone can read your logs and configuration.


Request authentication
----------------------

Alexa requests are verified properly, not just trusted:

  * the certificate URL must be https, on s3.amazonaws.com,
    port 443, under /echo.api/, checked after path
    normalisation so traversal cannot slip through
  * the certificate chain is validated against the system CA
    store
  * the certificate must carry the echo-api.amazon.com SAN
  * the RSA-SHA1 signature is checked over the raw request
    body, not a re-serialised copy
  * the timestamp must be within 150 seconds, which blocks
    replay
  * the applicationId must match skill_id once you set it

verify_sig defaults to 1. Setting it to 0 is for local curl
testing only. With it off, anyone who learns your endpoint URL
can play audio on the speaker.

Audio URLs are HMAC-SHA256 signed over the video id and an
expiry, so a leaked URL stops working and cannot be edited to
fetch something else. Video ids are matched against a strict
11 character pattern before they reach yt-dlp, and yt-dlp is
always invoked with an argument list, never a shell string.

Every /api route requires the admin token, compared in constant
time. Static console files are served without it because they
contain no secrets, and the console will not load without one.


Not a vulnerability
-------------------

GitHub secret scanning flags the InnerTube API key as a leaked
Google API key. It is not a secret. It is the public web client
key that youtube.com serves to every anonymous visitor:

  curl -s https://www.youtube.com/ | grep -o \
    '"INNERTUBE_API_KEY":"[^"]*"'

returns the same value. It is nobody's private credential and
carries no quota billed to anyone. Since version 0.3.3 the code
reads it from that page at runtime instead of hardcoding it,
which also keeps the client version current, so the literal no
longer appears in the tree at all.


Known limitations
-----------------

These are accepted, not oversights:

  * the whole design depends on holding a Google session on a
    phone. If that phone is compromised, the account is.
  * audio is extracted with yt-dlp, which violates YouTube's
    terms of service. That is a terms problem, not a security
    one, but it is why a secondary account is worth considering
    even though it costs you the Premium PO token exemption.
  * the admin token is printed to the terminal on every start.
    Anyone who can see that terminal can reach the console.
  * Tailscale Funnel inside Termux without root is unverified.
    See TEST.md phase 2.


Reporting something
-------------------

Open an issue, or use GitHub's private vulnerability reporting
if it is sensitive enough that a public issue would be a
problem. Include the version from

  ytalexa version

and the relevant lines from the console Logs tab, filtered to
errors only. Please redact anything from a cookies file.
