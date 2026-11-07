Creating the Alexa skill
========================

The skill stays in Development stage on your own account. No
certification, no fee, nobody else can see it. It never needs
to be published.


What you cannot have
--------------------

"Alexa, youtube <song>" is not possible. Free form text needs
the AMAZON.SearchQuery slot, and Amazon requires a carrier
phrase in the utterance, so the slot cannot be the whole thing.
Name free invocation would avoid this but needs certification
that a YouTube scraping skill will never get.

What you can have, with the invocation name below:

  one shot    "अलेक्सा, अंश का पिटारा से लग जा गले बजाओ"
  two turn    "अलेक्सा, अंश का पिटारा"
              "क्या सुनना है?"
              "लग जा गले"

For someone who does not read English the two turn form is
easier. She says two words, then answers a question, instead of
remembering a sentence shape. And because playback continues
through the radio queue by itself, she only does this once per
listening session, not once per song.


1. Device language
------------------

In the Alexa app, set the Echo to Hindi, or to the Hindi and
English bilingual mode. The skill is built for hi-IN. This
changes all Alexa use on that device, not just this skill.


2. Create the skill
-------------------

  developer.amazon.com/alexa/console/ask

  Create Skill
  name            ytalexa
  language        Hindi (IN)
  model           Custom
  hosting         Provision your own

Then under Interfaces, enable Audio Player. The skill will not
work without it, and the required playback intents below will
not validate either.


3. Interaction model
--------------------

Open the JSON Editor and paste the file next to this one:

  docs/interaction-hi-IN.json

Invocation name is "अंश का पिटारा", Ansh's treasure box.
A personal name plus an ordinary object: no part of it is a
word Alexa already listens for.

The name before it, "अंश का बाजा", failed on a real device
while working perfectly in the simulator, which is worth
understanding. The simulator takes typed text. The Echo has to
hear the name, and "बाजा" is a musical instrument, sitting
inside the vocabulary Alexa's music domain listens to. Spoken,
it was either claimed by that domain or split in the wrong
place: "अंश का बाजा खोलो" was parsed as the invocation
"अंश का" plus the song request "बाजा खोलो", and the skill
dutifully searched for and played a song called "Tu Dhol Baja
Languriya Dil Khol Baja Languriya".

So a name passing in the simulator proves nothing about the
device. check.sh rejects गाना, गाने, संगीत, बाजा, बाजे,
डीजे, धुन, रेडियो, म्यूजिक, music, song, radio, dj,
play and tune inside an invocation name.

It is deliberately not a word for "song" or "music". Amazon
requires at least two words, and separately requires that a
name not collide with Alexa's built in features. A name like
"मेरा गाना" ("my song") satisfies the word count and still
fails, because Alexa's music domain claims the utterance
before the skill is considered. You get a music answer, and
the Test tab shows no skill invocation. If you change the
name, keep it something nobody would say to a speaker by
accident.

Save, then Build Model. Wait for it to finish.


4. Endpoint
-----------

  Endpoint type     HTTPS
  Default region    https://<your-host>/alexa

  certificate       "My development endpoint is a sub-domain of
                     a domain that has a wildcard certificate
                     from a certificate authority"

Tailscale Funnel and Cloudflare both present a real CA cert, so
that option is correct for either. Do not pick the self signed
option.


5. Wire up the skill id
-----------------------

Copy the skill id from the console, it looks like

  amzn1.ask.skill.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

Put it in the ytalexa console, Config tab, skill_id. Until it
is set the server accepts any correctly signed Alexa request.


6. Test
-------

Use the Test tab in the developer console, set it to Hindi, and
type:

  अंश का पिटारा खोलो

You should get "नमस्ते, क्या सुनना है?" back. Then:

  लग जा गले

The reply should carry an AudioPlayer.Play directive. The
developer console cannot play the audio itself, so check the
ytalexa console Logs tab for a "play idx=0" line, then try it
on the real Echo.


Signature verification
----------------------

verify_sig is 1 by default and the server verifies Amazon's
request signature properly: cert URL shape, chain against the
system CA store, the echo-api.amazon.com SAN, expiry, the
RSA-SHA1 signature over the raw body, and a 150 second
timestamp window.

Set verify_sig to 0 only for local curl testing, and put it
back to 1. With it off, anyone who learns your endpoint URL can
play audio on your mother's Echo.


Required playback intents
-------------------------

Amazon requires these once Audio Player is enabled, and they
are all in the supplied model: Pause, Resume, Next, Previous,
StartOver, LoopOn, LoopOff, ShuffleOn, ShuffleOff, Repeat. The
server answers all of them. Loop and shuffle are acknowledged
politely rather than implemented.

Four of them cannot carry custom sample utterances, so the
Hindi phrases live on the four custom intents listed under
"Adding your own command" above. Both spellings reach the same
handler, so it does not matter which one Alexa decides to
send.


What she can say
----------------

The short way in is a Routine, described in SETUP.md: she says
one word, "डीजे", and the routine speaks the invocation name
for her. A Routine trigger may be a single word; an invocation
name may not, which is why the two are different strings.

On launch the skill resumes what was cut off, else resumes the
queue from earlier, else plays default_query from the Config
tab, else asks. So "अलेक्सा, डीजे" starts music rather than
starting a conversation, as long as default_query is set.

Every line below assumes the music is already playing, or that
the skill is open. The wake word is whatever the Echo is set
to; "अलेक्सा" is written here for brevity.

  start a song   "अलेक्सा, अंश का पिटारा से लग जा गले बजाओ"
  open the skill "अलेक्सा, अंश का पिटारा"  -> it asks, she answers
  next song      "अगला गाना"  "अगला गाना बजाओ"  "गाना बदलो"
  previous song  "पिछला गाना"  "पीछे वाला गाना"
  from the top   "शुरू से बजाओ"
  same again     "दोबारा बजाओ"
  pause          "रोको"  "ज़रा रोको"
  carry on       "चालू करो"  "आगे चलाओ"
  stop           "बंद करो"  "गाना बंद करो"
  help           "मदद करो"

Next and previous move through the queue the skill built: the
songs the search returned, then YouTube's suggestions for the
first one. Previous from the first song stays on the first
song rather than erroring.


Adding your own command
-----------------------

Two places have to agree, and the order matters.

1. docs/interaction-hi-IN.json, under the intent you want to
   extend, add the phrase to its "samples" list.

   Six built in intents reject custom samples outright and the
   build fails with "cannot be extended with custom sample
   utterances":

     AMAZON.NextIntent       AMAZON.PauseIntent
     AMAZON.PreviousIntent   AMAZON.ResumeIntent
     AMAZON.FallbackIntent   AMAZON.NavigateHomeIntent

   The first four are the ones you actually want to extend, so
   this skill declares its own intents beside them and routes
   both to the same handler:

     NextSongIntent    -> ax_do_step forward
     PrevSongIntent    -> ax_do_step back
     PauseSongIntent   -> ax_halt
     ResumeSongIntent  -> ax_do_resume

   Put new next and previous phrases on those, not on the
   AMAZON ones. The AMAZON ones stay declared and empty,
   because Audio Player requires them and they still bring
   their own stock Hindi utterances.

   Stop, Cancel, StartOver, Repeat and Help do accept custom
   samples, so phrases for those go straight on the built in
   intent.

   No utterance may appear in two intents. The build rejects a
   duplicate, and check.sh rejects it first.

2. Save and Build Model in the developer console. Nothing
   changes on the device until the build finishes.

A phrase with a variable part needs a slot instead, which
means a new intent in the model and a new branch in
ax_intent in src/alexa.py. A phrase with no variable part
needs no server change at all if you attach it to an intent
the server already answers.

There is a second, softer place to add a command. AX_NEXT,
AX_PREV and AX_HALT in src/alexa.py are word lists. When
Alexa mishears a control phrase as a song title and sends it
to PlayIntent, ax_ctl rescues it: if every word of the query
is either a filler word or a control word, the query is
treated as the control instead of a search. Adding a word
there costs no model build, and it only fires when the whole
query is control words, so "बस इतना सा ख्वाब" is still
searched as a song even though "बस" means stop.


Sharing the speaker with Amazon Music
-------------------------------------

Amazon Music cannot be switched off. It is part of the
account, not an app, and there is no setting that removes it.
This matters because Alexa decides between its own music
domain and this skill before the skill sees the utterance,
and when it picks wrong the two fight over the speaker.

What actually reduces the collisions:

  Alexa app, Settings, Music and Podcasts, Default Services.
  Set the default library and the default station provider to
  something other than Amazon Music if the account offers an
  alternative. A default that is not set still falls back to
  Amazon Music.

  Unlink any music service you do not use, in the same place.
  Fewer providers means fewer phrases Alexa claims.

  Keep the invocation name in every request that starts
  music. "अंश का पिटारा से X बजाओ" is routed by the name. A bare
  "X बजाओ" with no skill open is routed by Alexa's guess, and
  Amazon Music usually wins it.

A skill cannot speak unprompted, so the skill cannot announce
that Amazon Music is taking over at the moment it happens.
The protocol allows no speech in a reply to an AudioPlayer
event. What it can do is notice afterwards: when playback
stops without the skill having asked for it, the state is
flagged as cut, and the next time the skill is opened it says
"गाना बीच में रुक गया था। वहीं से आगे।" and resumes from the
offset it was cut at. So the recovery is one sentence rather
than silence, and she does not lose her place.
