SP_TAB = {
    "hi-IN": {
        "welcome": "नमस्ते, "
                   "क्या "
                   "सुनना "
                   "है?",
        "reprompt": "गाने का "
                    "नाम बोलि"
                    "ये।",
        "playing": "बजा रही "
                   "हूँ।",
        "notfound": "यह गाना "
                    "नहीं "
                    "मिला। "
                    "या कोई "
                    "दूसरा "
                    "गाना "
                    "बोलिये।",
        "failed": "गाना लाने"
                  " में "
                  "दिक्कत "
                  "हुई। प्र"
                  "यास पुनः "
                  "कीजिये।",
        "nomore": "सूड़ी "
                  "खत्म हो "
                  "गई।",
        "help": "कोई भी "
                "गाना या "
                "उसकी लाइ"
                "न बोलिये, "
                "मैं "
                "सुनाती "
                "हूँ।",
        "bye": "ठीक है।",
        "huh": "समझ नहीं "
               "आया। गाने"
               " का नाम "
               "बोलिये।",
        "card": "गाना"
    },
    "en-IN": {
        "welcome": "What would you like to hear?",
        "reprompt": "Say the name of a song.",
        "playing": "Playing.",
        "notfound": "I could not find that. Try another song.",
        "failed": "I could not fetch that one. Please try again.",
        "nomore": "That is the end of the list.",
        "help": "Say any song name or a line from it and I "
                "will play it.",
        "bye": "Okay.",
        "huh": "I did not catch that. Say a song name.",
        "card": "Song"
    }
}

SP_DFLT = "en-IN"


def sp_loc(loc):
    if loc == None:
        return SP_DFLT
    if loc in SP_TAB:
        return loc
    if len(loc) >= 2:
        head = loc[:2].lower()
        for k in SP_TAB:
            if k[:2].lower() == head:
                return k
    return SP_DFLT


def sp_get(loc, key):
    l = sp_loc(loc)
    tab = SP_TAB[l]
    if key in tab:
        return tab[key]
    if key in SP_TAB[SP_DFLT]:
        return SP_TAB[SP_DFLT][key]
    return ""
