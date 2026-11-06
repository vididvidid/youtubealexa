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

  one shot    "अलेक्सा, मेरा गाना से लग जा गले बजाओ"
  two turn    "अलेक्सा, मेरा गाना"
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

Invocation name is "मेरा गाना". Two words is safer than one;
Amazon tends to reject single word invocation names. If you
want to try "गाना" alone, change it and rebuild, and if the
build complains put it back.

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

  मेरा गाना खोलो

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
