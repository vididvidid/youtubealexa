MANUAL TEST SHEET
=================

Everything in here needs a real phone, a real Echo, a real
Amazon account or your mother. I could not test any of it from
my side. Work top to bottom, each phase depends on the one
before it.

Mark boxes as you go. Where something fails, the log line to
look at is named.

Legend
  [ ]  not done
  [x]  works
  [!]  failed, see notes at the bottom of each phase


WHAT I ALREADY TESTED, SO YOU CAN SKIP IT
-----------------------------------------

Do not spend time on these, they pass:

  * search for Hindi lyric fragments, Devanagari and romanized
  * Devanagari to romanized title matching
  * result ranking, originals beating covers and status clips
  * audio download, AAC 128k in m4a, correct duration
  * cache hit, eviction, no leftover temp files
  * signed audio URLs, tampering and expiry rejected
  * video id injection attempts rejected
  * Alexa signature verification against a forged CA, tampered
    body, bad cert URL, missing SAN, stale timestamp
  * skill id mismatch rejected
  * Host allowlist, right host passes and wrong host is 403
  * full simulated conversation: launch, play, audio fetch,
    range request, PlaybackStarted, NearlyFinished enqueue with
    expectedPreviousToken, next, pause
  * radio queue, 50 era matched tracks from a Lata seed
  * admin API token enforcement, path traversal, oversize body


PHASE 1  PHONE
--------------

  [ ] Termux installed from F-Droid or GitHub, NOT Play Store
  [ ] Termux:API installed
  [ ] Termux:Boot installed
  [ ] bash bin/termux_setup.sh finished with no MISSING line
  [ ] battery optimisation set to Unrestricted for Termux
  [ ] autostart enabled, Xiaomi / Oppo / Vivo / OnePlus only

  [ ] bash bin/run.sh starts and prints an admin token
  [ ] http://127.0.0.1:8080/ui/ opens in the phone browser
  [ ] token unlocks the console
  [ ] Status tab shows F01 to F10 all green
  [ ] Logs tab shows a "listening on" line

  This is the first thing I could not test at all. The code is
  pure stdlib plus two pip packages, so I expect it to work,
  but Termux is its own world.

  If python3 bin/serve.py fails to bind, something else has
  port 8080. Change port in the Config tab.

  notes:


PHASE 2  TUNNEL   <-- GO / NO-GO GATE
-------------------------------------

Nothing past this point works until the Echo can reach the
phone over HTTPS. Do not move on until this passes.

  [ ] tailscale installed in Termux, ARM64 build
  [ ] tailscale ... up completed, device shows in your tailnet
  [ ] bash bin/tunnel.sh tailscale 8080 succeeded
  [ ] tailscale funnel status shows /alexa and /audio

  From a DIFFERENT network, phone data with wifi off:

  [ ] curl https://<name>.<tailnet>.ts.net/alexa
      expected: HTTP 400 with {"ok":0,...}
      400 means reachable. That is a pass.

  [ ] curl https://<name>.<tailnet>.ts.net/ui/
      expected: 404 from Tailscale, NOT the console
  [ ] curl https://<name>.<tailnet>.ts.net/api/status
      expected: 404

  Those last two matter. If the console answers from the
  internet, stop and fix the funnel paths before continuing.
  Anyone could read your config.

  THIS IS THE STEP MOST LIKELY TO FAIL. Tailscale Funnel inside
  Termux without root is the one thing in this project I could
  not verify, and there are conflicting reports about whether
  cert provisioning needs root in userspace mode. If it refuses
  to issue a cert, go to docs/SETUP-DOMAIN.md option B, the
  Oracle relay. Tell me which way you went.

  notes:


PHASE 3  COOKIES
----------------

  On a DESKTOP browser:

  [ ] opened a private / incognito window
  [ ] logged into youtube.com in that window
  [ ] exported cookies.txt, Netscape format
  [ ] CLOSED the window WITHOUT logging out

  That last step is the one people get wrong. If you export
  from a session you keep using, YouTube rotates it and
  playback dies a week later with 403 errors.

  On the phone:

  [ ] python3 bin/cookies_load.py <path to cookies.txt>
      expected: "login cookies look complete"
  [ ] deleted the copy from /sdcard afterwards
  [ ] console Media tab shows present=yes, logged in=yes
  [ ] expires in: ____ days   (write it down, diary it)

  [ ] Media tab, Search tester, type: लग जा गले
      expected: Lata Mangeshkar full song near the top
  [ ] press fetch on the top row
      expected: button turns to "cached" within ~10s

  If fetch fails here, playback will fail later. Check the Logs
  tab for an "audio" error line. Nine times out of ten the fix
  is: pip install --upgrade yt-dlp

  notes:


PHASE 4  ALEXA SKILL
--------------------

  [ ] Echo device language set to Hindi, or Hindi/English
  [ ] skill created, Hindi (IN), Custom, own hosting
  [ ] Interfaces: Audio Player ENABLED
  [ ] docs/interaction-hi-IN.json pasted into JSON Editor
  [ ] Build Model succeeded
      if it rejects the invocation name, see ALEXA-SKILL.md
  [ ] endpoint set to https://<your-host>/alexa
  [ ] cert option: wildcard certificate from a CA
  [ ] skill id copied into console Config, skill_id field
  [ ] verify_sig is 1

  Developer console Test tab, language Hindi:

  [ ] type "अंश का बाजा खोलो"
      expected reply: नमस्ते, क्या सुनना है?
  [ ] JSON Input and JSON Output panels are NOT empty
      this is the one that matters. Empty panels mean the
      skill was never called and you are reading Alexa's own
      answer, however convincing it looks. Do not debug the
      server in that case; fix the invocation name or enable
      the skill for testing first.
  [ ] JSON Output contains a Dialog.ElicitSlot directive
  [ ] type "लग जा गले"
      expected: JSON reply containing AudioPlayer.Play
      if instead you get an Amazon Music answer, ElicitSlot
      did not take. Fall back to the one shot form and tell
      me, because that decides the whole two turn design.
  [ ] console Logs tab shows "play idx=0 ..."

  If you get a signature error, your clock may be off. The
  server allows 150 seconds of skew. Check: date

  notes:


PHASE 5  THE ECHO
-----------------

Now the real thing. This is where unknowns show up, because
the Echo fetches the audio itself.

First, three things that have nothing to do with the code.
There is no install step; a development skill is on every
Echo signed in to the developer account already. Do not look
for it in the skill store, it is not there and never will be.

  [ ] Alexa app, More, Settings, Your Profile: the email
      matches the developer console login
  [ ] developer console, Test tab: Development, not Off
  [ ] Alexa app, Devices, the Echo, Language: हिन्दी
      an English (India) device cannot invoke a hi-IN only
      skill and gives you no error saying so
  [ ] optional sanity check: Alexa app, More, Skills and
      Games, Your Skills, Dev tab, it is listed with a DEV
      badge

  [ ] "अलेक्सा, अंश का बाजा"            -> she asks what to play
  [ ] "लग जा गले"                     -> audio actually starts
  [ ] time from speaking to first sound: ____ seconds
      under 8 is good, over 12 means the fetch is slow
  [ ] song plays to the end without cutting out
  [ ] NEXT SONG STARTS BY ITSELF        <-- the key one
  [ ] second song is a sensible follow-on, same era
  [ ] let it run 5 songs without touching anything

  [ ] "अलेक्सा, अगला गाना"            -> skips
  [ ] skip twice in a row, then "पिछला गाना"
      -> lands on the song before, not the one playing. If it
      replays the current song the index is not tracking
      playback; look for a "play idx=" line whose number did
      not move
  [ ] let the queue advance by itself once, THEN "अगला गाना"
      -> must move forward from the song you can hear, not
      from the one you asked for by name
  [ ] "अलेक्सा, रोको"                 -> stops
  [ ] "अलेक्सा, बंद करो"             -> stops
  [ ] "अलेक्सा, अंश का बाजा" then "चालू करो" -> resumes

  [ ] one shot form: "अलेक्सा, अंश का बाजा से लग जा गले बजाओ"

  Sharing the speaker with Amazon Music:

  [ ] while a song is playing, say "अलेक्सा, मौसम कैसा है"
      -> she answers, and the music comes back by itself
  [ ] while a song is playing, deliberately ask Amazon Music
      for something: "अलेक्सा, कुछ बजाओ"
      -> our music stops, theirs starts. Expected, and not
      fixable from the skill
  [ ] then "अलेक्सा, अंश का बाजा"
      -> says "गाना बीच में रुक गया था। वहीं से आगे।" and picks
      up the same song where it was cut. Check the log for a
      "playback cut off at" line and a "resuming after cut"
      line
  [ ] after a normal "बंद करो", opening the skill again does
      NOT claim it was interrupted, it just asks what to play

  If audio never starts but the logs show "play idx=0", the
  Echo could not fetch the URL. Check: is the tunnel still up,
  and does the URL in the log begin with https and your tunnel
  hostname rather than 127.0.0.1?

  If the next song does not start by itself, look for an
  "enqueue idx=" line in the logs. No line means Alexa never
  sent PlaybackNearlyFinished, which usually means Audio Player
  is not enabled on the skill.

  notes:


PHASE 6  YOUR MOTHER      <-- the only test that counts
-------------------------------------------------------

Everything above can pass and this can still fail. Sit with her
and write down what she actually says, word for word.

  [ ] she can start it without help
  [ ] she can ask for 5 songs she likes
  [ ] write each phrase and whether the right song played:

      phrase spoken                      right song?
      1 ________________________________  [ ]
      2 ________________________________  [ ]
      3 ________________________________  [ ]
      4 ________________________________  [ ]
      5 ________________________________  [ ]

  [ ] she can skip a song
  [ ] she can stop it
  [ ] the invocation name is easy for her to say
      if not, tell me and we change it

  Send me the misses. The ranking weights all live in one table
  at the top of src/yt_search.py, YS_W_* and the GOOD / BAD
  title lists, and I can tune them against her real phrases.
  Guessing from my side is worth much less than five of her
  actual sentences.

  notes:


PHASE 7  ENDURANCE
------------------

  [ ] left running overnight, console still reachable next day
  [ ] playback still works after 12 hours idle
  [ ] rebooted the phone, Termux:Boot brought it back by itself
  [ ] playback works after the reboot with no manual step
  [ ] after 20 or so songs, Media tab shows cache under the
      limit, so eviction is working
  [ ] phone is not hot and the back is not bulging
  [ ] after a week, cookies still valid, Media tab still says
      logged in = yes

  notes:


THINGS I COULD NOT TEST, RANKED BY RISK
---------------------------------------

  1  Tailscale Funnel inside Termux without root. Conflicting
     reports. Phase 2.
  2  Whether the Echo accepts our audio replies in practice.
     The format is right, AAC in m4a with byte ranges and a
     real cert, but only a real Echo proves it.
  3  Alexa signature verification against Amazon's REAL cert
     chain. I verified the logic with a forged CA; the system
     CA store on Termux is the untested part.
  4  Hindi ASR quality. Whether Alexa hears your mother's
     phrasing correctly is Amazon's business, not this code's.
  5  Android killing Termux over days. Battery settings vary
     by manufacturer.
  6  Whether YouTube throttles your home IP after heavy use.
  7  Long term cookie survival on a real Premium account.


IF SOMETHING BREAKS LATER
-------------------------

  symptom                        first thing to try
  ----------------------------   --------------------------
  playback stopped working       pip install --upgrade yt-dlp
  403 in audio logs              re-export cookies, Phase 3
  console unreachable            bash bin/run.sh again
  Echo says it cannot reach      check tunnel, Phase 2
  wrong songs picked             send me her phrases, Phase 6
  next song never starts         Audio Player enabled? Phase 4
  all requests 403               skill_id correct? clock right?

  The Logs tab in the console is the first place to look for
  every one of these. Filter to "errors only".
