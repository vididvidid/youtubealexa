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

SP_CUT = ["|", "(", "[", "{", " \u2013 ", " \u2014 ", " - "]

SP_NOISE = [
    "official music video", "official video song",
    "full video song", "official audio", "official video",
    "lyrical video", "music video", "full video",
    "video song", "with lyrics", "full audio", "full song",
    "audio song", "song video", "official", "lyrical",
    "lyrics", "hd video", "4k", "hd", "1080p", "720p",
    "\u092b\u0941\u0932 \u0935\u0940\u0921\u093f\u092f\u094b "
    "\u0938\u0949\u0928\u094d\u0917",
    "\u0935\u0940\u0921\u093f\u092f\u094b "
    "\u0938\u0949\u0928\u094d\u0917",
    "\u092b\u0941\u0932 \u0938\u0949\u0928\u094d\u0917",
    "\u0911\u092b\u093f\u0936\u093f\u092f\u0932",
]

SP_TRIM = ".,-|:;\u0964 "


def sp_rank():
    i = 0
    while i < len(SP_NOISE):
        j = i + 1
        while j < len(SP_NOISE):
            if len(SP_NOISE[j]) > len(SP_NOISE[i]):
                t = SP_NOISE[i]
                SP_NOISE[i] = SP_NOISE[j]
                SP_NOISE[j] = t
            j = j + 1
        i = i + 1


sp_rank()


def sp_cut(t):
    best = len(t)
    i = 0
    while i < len(SP_CUT):
        p = t.find(SP_CUT[i])
        i = i + 1
        if p > 0 and p < best:
            best = p
    return t[:best]


def sp_denoise(t):
    i = 0
    while i < len(SP_NOISE):
        w = SP_NOISE[i]
        i = i + 1
        p = t.lower().find(w)
        while p >= 0:
            t = t[:p] + " " + t[p + len(w):]
            p = t.lower().find(w)
    return t


def sp_squash(t):
    out = ""
    gap = 0
    i = 0
    while i < len(t):
        ch = t[i]
        i = i + 1
        if ch == " " or ch == "\t" or ch == "\n" or ch == "\r":
            gap = 1
            continue
        if gap == 1 and len(out) > 0:
            out = out + " "
        gap = 0
        out = out + ch
    return out


def sp_trim(t):
    while len(t) > 0 and t[0] in SP_TRIM:
        t = t[1:]
    while len(t) > 0 and t[len(t) - 1] in SP_TRIM:
        t = t[:len(t) - 1]
    return t


def sp_title(t, lim):
    if type(t) != str:
        return ""
    t = sp_trim(sp_squash(sp_denoise(sp_cut(t))))
    if len(t) <= lim:
        return t
    cut = t[:lim]
    p = cut.rfind(" ")
    if p >= lim // 2:
        cut = cut[:p]
    return sp_trim(cut)


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
