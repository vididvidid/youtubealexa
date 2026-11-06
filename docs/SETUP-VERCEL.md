Setup on Vercel
===============

READ THIS FIRST
---------------

Vercel cannot serve the audio. Not a configuration problem, a
hard one:

  * googlevideo URLs are bound to the IP that requested them.
    Serverless gives you a different IP per invocation, so a
    URL extracted in one call gets 403 when fetched in another.
  * Hobby functions are capped at 300s including streamed
    output, so a long bhajan would be cut off mid song.
  * the filesystem is ephemeral, so the audio cache and the
    rotated cookie jar do not survive.

So Vercel is useful for exactly two things:

  1. a stable HTTPS front door for the Alexa endpoint, if
     Tailscale Funnel will not work for you
  2. testing search and the interaction model without the
     phone running

In mode 1 the phone still serves audio. Vercel handles the
Alexa POST, and the Play directive it returns points the Echo
straight at the phone.


Deploy
------

  npm i -g vercel
  vercel

The repo already has vercel.json and requirements.txt. Every
path is rewritten to api/index.py, which reuses the same route
table as the phone, so there is no second implementation to
keep in sync.


Environment variables
---------------------

The filesystem is read only apart from /tmp, so config comes
from the environment. Every config key can be set as
YTA_<KEY_IN_CAPITALS>. Set these in the Vercel dashboard:

  YTA_ADMIN_TOKEN     long random string, protects the console
  YTA_HMAC_SECRET     long random string, signs audio urls
  YTA_SKILL_ID        amzn1.ask.skill....
  YTA_AUDIO_MODE      proxy
  YTA_AUDIO_ORIGIN    https://<your-phone-host>
  YTA_PUBLIC_HOSTS    your-project.vercel.app
  YTA_LOCALE          hi-IN

YTA_HMAC_SECRET must be IDENTICAL on Vercel and on the phone.
Vercel signs the audio URL and the phone verifies it. If they
differ every audio request gets 403.

Generate both secrets with:

  python3 -c "import os;print(os.urandom(24).hex())"


What works and what does not
----------------------------

  works     /alexa, search, radio queue, the console, logs
  works     /audio redirects to YTA_AUDIO_ORIGIN
  broken    serving audio bytes from Vercel itself
  degraded  logs reset on every cold start, they live in
            /tmp/ytalexa/state.db
  degraded  no cookies unless you bake them in, so search is
            anonymous and extraction has no Premium exemption


Account risk
------------

If you ever put Premium cookies on Vercel, understand the
tradeoff: a logged in Google session used from constantly
changing AWS datacenter IPs is itself a pattern Google can
flag. The phone path exists to avoid exactly this. Do not put
your main account cookies on Vercel unless you accept that.
