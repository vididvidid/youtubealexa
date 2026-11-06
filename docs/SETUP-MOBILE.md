Setup on an old Android phone (the main path)
=============================================

This is the recommended deployment. The phone does everything:
search, extraction and serving audio to the Echo. It must stay
on your home wifi and stay plugged in.

Why the phone and not a cloud function: googlevideo stream URLs
are bound to the IP that asked for them, hardest of all on
music. Whatever machine extracts the URL must also fetch the
bytes. The phone does both from one residential IP, which is
also what keeps your Premium account away from datacenter abuse
heuristics.


1. Install Termux
-----------------

Install from F-Droid or from the GitHub releases page. Do NOT
use the Play Store build, it is deprecated and will fail.

  https://f-droid.org/packages/com.termux/

Also install, from the same place:

  Termux:API    needed for the wake lock
  Termux:Boot   needed to restart after a reboot


2. Get the code and run setup
-----------------------------

  pkg install -y git
  git clone <your repo url> ~/youtubealexa
  cd ~/youtubealexa
  bash bin/termux_setup.sh

The script installs python, openssl, ffmpeg, yt-dlp and
ytmusicapi, then prints the versions. If any line says MISSING,
stop and fix it before going on.


3. Turn off battery optimisation
--------------------------------

Android will kill Termux within hours otherwise.

  Settings, Apps, Termux, Battery, choose Unrestricted

On Xiaomi, Oppo, Vivo and OnePlus also enable Autostart for
Termux. These skins are aggressive and this step is not
optional.


4. First run
------------

  bash bin/run.sh

On first start it prints an admin token. Copy it. From the
phone's browser open:

  http://127.0.0.1:8080/ui/

Paste the token. You should see the console with every feature
marked live. The token is printed again on every start, and is
stored in ~/.ytalexa/config.json.


5. Public HTTPS with Tailscale Funnel
-------------------------------------

Alexa needs a reachable HTTPS endpoint on port 443 with a cert
from a trusted CA. Funnel gives you that on a *.ts.net name
with no domain and no port forwarding.

Install the Linux ARM64 build of tailscale into Termux, then:

  tailscale --socket=$HOME/.ytalexa/tailscaled.sock up

Follow the printed URL to log in, then:

  bash bin/tunnel.sh tailscale 8080

That mounts ONLY /alexa and /audio. The console and the whole
/api tree stay unreachable from the internet. Do not mount the
whole server.

Check the result:

  tailscale funnel status

Note the hostname. Then from any other network:

  curl https://<name>.<tailnet>.ts.net/alexa

A 400 reply means it is reachable, which is what you want. The
endpoint only accepts well formed Alexa POSTs.

HONEST WARNING: Funnel inside Termux is the one step in this
whole project I could not verify. Tailscale 1.104.0 and later
reportedly run tailscaled in userspace mode on Android with
Funnel working, but an older report says cert provisioning
needs root in userspace mode. If Funnel refuses to issue a
cert, use docs/SETUP-DOMAIN.md instead.


6. Cookies
----------

Your YouTube Premium cookies are what exempt this from GVS PO
tokens, which is the main reason these setups break.

Export them on a DESKTOP browser, not the phone. Mobile Chrome
has no extensions.

  a. open a PRIVATE or INCOGNITO window
  b. log in to youtube.com
  c. export cookies.txt with a Netscape format extension
  d. CLOSE the window without logging out

Step d matters. If you export from a normal session you keep
using, YouTube rotates the session and silently invalidates
what yt-dlp holds, usually within a week or two.

Copy the file to the phone and load it:

  python3 bin/cookies_load.py /sdcard/Download/cookies.txt

It prints how many youtube cookies it found and how long they
last. If it warns about missing core cookies you were not
logged in, so export again.

Then DELETE the copy from /sdcard. Any app with storage
permission can read that folder. The loaded copy lives in
~/.ytalexa/cookies.txt at mode 0600.

You can also paste cookies later from the console, on the Media
tab, which is easier for refreshes.


7. Start on boot
----------------

  mkdir -p ~/.termux/boot
  cp bin/boot.sh ~/.termux/boot/ytalexa.sh
  chmod +x ~/.termux/boot/ytalexa.sh

Reboot the phone and confirm the console comes back by itself.


8. Set the skill id
-------------------

Once the skill exists, see docs/ALEXA-SKILL.md, put its id into
the console Config tab under skill_id. Until you do, any
correctly signed Alexa request is accepted. With it set, only
your skill is.


Battery safety
--------------

A phone kept at 100 percent for months can swell its battery.
Keep it somewhere ventilated, not under a pillow or on fabric,
and look at it now and then. If the back starts to bulge,
stop using that phone.


Keeping it alive
----------------

  yt-dlp breaks when YouTube changes something. Fix:

    pip install --upgrade yt-dlp

  Do that first whenever playback starts failing. It is the
  cause most of the time.


Running in a Linux container instead of Termux
----------------------------------------------

Termux is not the only way. A proot Linux container on the
same phone works, and so does any always on Linux box. The
only thing this project needs is python 3.11 or newer, a
process that stays alive, and a tunnel.

Three things differ from plain Termux.

  No Termux:Boot. A proot container has no boot hook, so the
  autostart step of the wizard cannot help you. After a
  reboot, or after Android kills the container, run:

    ytalexa up

  That starts tailscaled in userspace mode on the private
  socket, starts the server if the port is down, mounts the
  funnel if it is not mounted, and prints the status block.
  It is safe to run when everything is already up, so it is
  the right thing to put behind a launcher button or a one
  tap shortcut.

  No termux-wake-lock. The container cannot take an Android
  wake lock. Android will suspend it eventually. Exclude the
  container app from battery optimisation in Android settings
  and keep the phone on the charger.

  Running as root. A container often runs everything as root.
  Nothing here needs root, and $YTA_HOME is still 0700, but
  remember that root in the container can read the cookies.
  Do not install anything else you do not trust in it.

Tailscale in a container has no tun device, so tailscaled must
run in userspace mode against a socket inside $YTA_HOME rather
than the system one:

  tailscaled --tun=userspace-networking \
    --statedir=$HOME/.ytalexa/tailscale \
    --socket=$HOME/.ytalexa/tailscaled.sock &

  tailscale --socket=$HOME/.ytalexa/tailscaled.sock up

bin/tunnel.sh already starts it this way, and every tailscale
call in the wizard passes that socket when the file exists, so
you only run the login by hand once.
