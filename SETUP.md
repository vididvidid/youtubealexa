SETUP
=====

Two halves. The phone half is almost all automatic now. The
Amazon half has to be clicked through by hand, because Amazon
has no API for creating a skill.

Budget about 10 minutes for the phone and 15 for Amazon.

  phone   install, run the wizard, answer its questions
  amazon  create a skill, paste one JSON file, paste one URL

Detailed references, for when something goes wrong:

  docs/SETUP-MOBILE.md   every phone step in full
  docs/ALEXA-SKILL.md    every Amazon step in full
  docs/SETUP-DOMAIN.md   using your own hostname
  docs/SETUP-VERCEL.md   running the skill endpoint on Vercel
  TEST.md                what to check once it runs


PART A, THE PHONE
=================

A1. Install Termux
------------------

From F-Droid or the GitHub releases page. NOT the Play Store,
that build is deprecated and will fail.

  https://f-droid.org/packages/com.termux/

Install these two from the same place as well:

  Termux:API     for the wake lock
  Termux:Boot    to restart after a reboot


A2. One command
---------------

Open Termux and paste:

  curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/main/install.sh | bash

Replace OWNER/REPO with your GitHub path. That script does:

  * checks it is really running on Termux
  * installs python, openssl, ffmpeg, termux-api, git
  * installs yt-dlp and ytmusicapi
  * downloads the latest release into ~/ytalexa
  * creates ~/.ytalexa at mode 0700
  * puts a "ytalexa" command on your PATH
  * starts the setup wizard

If you prefer the Termux package:

  pkg install -y python openssl-tool ffmpeg termux-api
  curl -fsSLO https://github.com/OWNER/REPO/releases/latest/download/ytalexa.deb
  dpkg -i ytalexa.deb
  ytalexa setup


A3. The wizard
--------------

  ytalexa setup

A numbered menu. Nothing is hidden, every step prints the
command it runs and whether it worked.

   1  check dependencies
   2  battery and autostart reminder
   3  load Premium cookies
   4  set up the tunnel
   5  set the skill id
   6  install boot autostart
   7  start the server
   8  run self test
   9  show status

Work down the list. Step 4 is the one that can genuinely fail,
see A5.

The wizard can be re-run any time. It is safe to repeat a step.


A4. Cookies, the one manual bit
-------------------------------

Your Premium cookies are what exempt this from YouTube's PO
token requirement, which is the usual reason these setups
break. Do this on a DESKTOP, mobile Chrome has no extensions.

  1. open a PRIVATE or INCOGNITO window
  2. log in to youtube.com
  3. export cookies.txt with any Netscape format extension
  4. CLOSE that window WITHOUT logging out

Step 4 is the one people get wrong. Exporting from a session
you keep using lets YouTube rotate it, and playback dies about
a week later with 403 errors.

Get the file onto the phone, then either:

  ytalexa cookies /sdcard/Download/cookies.txt

or paste the text into the console, Media tab, which is easier
for refreshes later.

Then delete the copy from /sdcard. Any app with storage
permission can read that folder, and those are live
credentials.


A5. The tunnel
--------------

Alexa needs to reach the phone on HTTPS port 443 with a cert
from a real CA. Wizard step 4 sets up Tailscale Funnel, which
gives you that on a *.ts.net name with no domain and no port
forwarding. It mounts ONLY /alexa and /audio, so the console
stays off the internet.

Write down the hostname it prints. You need it in part B.

If Funnel will not issue a cert, that is the known weak point:
Funnel inside Termux without root is the one thing in this
project that could not be verified. Go to
docs/SETUP-DOMAIN.md, option B, the Oracle relay. It is free
and keeps Cloudflare out of the path.


PART B, AMAZON
==============

B1. Device language
-------------------

Alexa app, your Echo, Settings, Language. Choose Hindi, or the
Hindi and English bilingual mode. This affects all Alexa use on
that device, not only this skill.


B2. Create the skill
--------------------

  https://developer.amazon.com/alexa/console/ask

  Create Skill
    skill name       ytalexa
    primary locale   Hindi (IN)
    model            Custom
    hosting          Provision your own

Then, in the left sidebar, Interfaces:

  turn ON  Audio Player

Nothing works without that, and the playback intents will not
validate either. Save.


B3. Interaction model
---------------------

Left sidebar, Interaction Model, JSON Editor. Delete what is
there and paste the whole of:

  docs/interaction-hi-IN.json

It is also on the docs website if that is easier to copy from
a phone. Then Save Model, then Build Model, and wait for the
build to finish.

The invocation name is "मेरा गाना". If the build rejects it,
try a different two word name; Amazon tends to reject single
word invocation names.


B4. Endpoint
------------

Left sidebar, Endpoint.

  Service Endpoint Type   HTTPS
  Default Region          https://YOUR-HOST/alexa

Use the hostname from A5. Keep the /alexa path.

For the certificate dropdown choose:

  "My development endpoint is a sub-domain of a domain that
   has a wildcard certificate from a certificate authority"

Tailscale and Cloudflare both present a real CA certificate,
so that is the right option for either. Do not choose the self
signed option. Save.


B5. Skill id
------------

Copy the skill id from the top of the skill page. It looks
like:

  amzn1.ask.skill.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

On the phone:

  ytalexa setup

Choose step 5 and paste it. Until this is set, any correctly
signed Alexa request is accepted. With it set, only your skill
is.


B6. Test in the console
-----------------------

Developer console, Test tab. Switch it from Off to Development.
Set the language selector to Hindi. Type:

  मेरा गाना खोलो

Expected reply: नमस्ते, क्या सुनना है?

Then type:

  लग जा गले

Expected: a JSON reply containing an AudioPlayer.Play
directive. The developer console cannot play audio itself, so
check the phone console Logs tab for a line like

  inf alexa  play idx=0 ...

If you see that, the hard part is done.


B7. The real thing
------------------

Say to the Echo:

  "अलेक्सा, मेरा गाना"
  "क्या सुनना है?"
  "लग जा गले"

Music should start within a few seconds and keep going by
itself into a radio queue afterwards.

Now go through TEST.md, which is the checklist for everything
that can only be verified on real hardware.


THE DAY IT STOPS WORKING
========================

In order of likelihood:

  1  yt-dlp is out of date, YouTube changed something

       ytalexa update

  2  cookies expired or were rotated

       redo A4

  3  the server is not running

       ytalexa start
       ytalexa status

  4  the tunnel dropped

       ytalexa tunnel

Always look at the console Logs tab first, filtered to errors
only. It names the cause nearly every time.
