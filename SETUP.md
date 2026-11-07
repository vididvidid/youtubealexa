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

Needs Python 3.11 or newer, because yt-dlp requires it. A
current Termux gives you that. If yours is old:

  pkg upgrade python

  https://f-droid.org/packages/com.termux/

Install these two from the same place as well:

  Termux:API     for the wake lock
  Termux:Boot    to restart after a reboot


A2. One command
---------------

Open Termux and paste:

  R=https://github.com/vididvidid/youtubealexa/releases
  curl -fsSL $R/latest/download/install.sh | bash

The path in that URL is the repository being installed from,
so use your own if you forked this. That script does:

  * checks it is really running on Termux
  * installs python, openssl, ffmpeg, termux-api, git
  * installs yt-dlp and ytmusicapi
  * downloads the latest release into ~/ytalexa
  * creates ~/.ytalexa at mode 0700
  * puts a "ytalexa" command on your PATH
  * starts the setup wizard

If you prefer the Termux package:

  pkg install -y python openssl-tool ffmpeg termux-api
  curl -fsSLO $R/latest/download/ytalexa.deb
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

The invocation name is "अंश का बाजा". Pick a replacement with
care if you change it. Amazon rejects single word names, and a
name that reads like an ordinary music request never reaches
your skill at all: Alexa's own music domain answers first. The
earlier name "मेरा गाना" means "my song", so "अलेक्सा, मेरा गाना
खोलो" was parsed as "open my song" and got an Amazon Music
Unlimited advert instead. The giveaway is the Test tab showing
empty JSON Input and JSON Output panels, which means your
endpoint was never called.

The current name is a personal one, "Ansh's music box". That
is deliberate: a name built from a person's name shares no
word with anything Alexa already listens for, so the music
domain never claims it.

If even that is a mouthful, a Routine gives you a shorter
phrase. Alexa app, More, Routines, plus sign; When This
Happens, Voice, type the phrase she will actually say, for
example "गाना बजाओ"; Add Action, Custom, type "अंश का बाजा खोलो".
Save. She then says "अलेक्सा, गाना बजाओ" and the routine speaks
the real invocation for her. One caveat worth testing on the
device: a routine that opens a skill may or may not leave the
microphone open for her to answer "कौन सा गाना सुनना है?". If it
does not, the one shot form is the one to teach her instead.

For the full list of what she can say once it is playing, and
for how to add your own phrases, see docs/ALEXA-SKILL.md.


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

  अंश का बाजा खोलो

Expected reply: नमस्ते, क्या सुनना है?

Then type:

  लग जा गले

Expected: a JSON reply containing an AudioPlayer.Play
directive. The developer console cannot play audio itself, so
check the phone console Logs tab for a line like

  inf alexa  play idx=0 ...

If you see that, the hard part is done.

Read the JSON Input and JSON Output panels on the right, not
just the chat bubbles. A reply that looks sensible but leaves
both panels empty did not come from this skill at all. Alexa
answered it herself, and what you are reading is her own music
domain. In that case the problem is the invocation name or the
skill not being enabled for testing, never your server.


B6a. Prove the endpoint separately
----------------------------------

If you want to test the server without depending on the
invocation name at all, use the Manual JSON tab next to Alexa
Simulator. It sends a request you paste straight to your
endpoint, correctly signed, skipping speech recognition
entirely. Pick LaunchRequest from its template list and send
it.

A reply with outputSpeech in it means the whole chain works:
tunnel, certificate, signature check, and handler. Anything
else is a real server problem, and the phone console Logs tab
will say which:

  signature: ...    the request did not verify
  host not allowed  add the hostname to public_hosts
  wrong skill       skill_id in config does not match


B7. Getting it onto the Echo
----------------------------

There is nothing to install. Do not look for it in the Alexa
app's skill store and do not try to enable it. A skill in
development is never listed there; the store only carries
skills that passed certification, and this one never will,
because it reads YouTube. Searching for "ytalexa" will always
come up empty and that is correct.

What actually happens is that Amazon puts a skill that is in
the Development stage onto every Echo signed in to the same
account as the developer console. No install step, no enable
step. If the three things below are true it is already there.

  1  The Echo is signed in to the same Amazon account as the
     developer console.

     Alexa app, More, Settings, Your Profile. The email there
     has to be the one you log in to developer.amazon.com
     with. This is the usual reason a development skill never
     appears: a household where the Echo was set up on a
     different family account.

  2  Skill testing is set to Development, not Off.

     Developer console, Test tab, the dropdown at the top
     left. You have already done this if you tested in the
     simulator.

  3  The Echo's language is Hindi.

     Alexa app, Devices, Echo and Alexa, pick the device,
     Language. Choose हिन्दी.

     This one matters more than it looks. The skill has a
     hi-IN interaction model and nothing else. An Echo set to
     English (India) cannot invoke it at all, and it will not
     tell you why; the invocation name simply does nothing or
     falls through to Alexa's own music. Set the device to
     Hindi first and get a song playing. Try the bilingual
     Hindi and English setting afterwards if you want it, as
     a separate change, so you know which one broke it if it
     stops working.

If you want to see it listed, it is in the Alexa app under
More, Skills and Games, Your Skills, then the Dev tab along
the top. It carries a DEV badge. Seeing it there is a useful
confirmation, but it is not where you turn it on, and the
skill works whether or not you ever look at this screen.

After changing the device language, give it a minute and say
something simple to the Echo first, so you know the device
came back up in Hindi before you blame the skill.


B8. The real thing
------------------

Say to the Echo:

  "अलेक्सा, अंश का बाजा"
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
