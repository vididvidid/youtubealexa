FD_DEVA = {
    "क": "k", "ख": "kh", "ग": "g",
    "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j",
    "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d",
    "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d",
    "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b",
    "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l",
    "व": "v", "श": "sh", "ष": "sh",
    "स": "s", "ह": "h",
    "ळ": "l", "ऱ": "r",
    "क़": "k", "ख़": "kh", "ग़": "g",
    "ज़": "j", "ड़": "d", "ढ़": "dh",
    "फ़": "f", "य़": "y",
    "अ": "a", "आ": "a", "इ": "i",
    "ई": "i", "उ": "u", "ऊ": "u",
    "ए": "e", "ऐ": "ai", "ओ": "o",
    "औ": "au", "ऋ": "ri", "ॐ": "om"
}

FD_DIG = [
    ["chh", "c"], ["shh", "s"], ["ksh", "ks"],
    ["ch", "c"], ["sh", "s"], ["ph", "f"], ["th", "t"],
    ["kh", "k"], ["gh", "g"], ["jh", "j"], ["bh", "b"],
    ["dh", "d"], ["ck", "k"], ["ks", "x"], ["gy", "g"]
]

FD_ONE = {
    "q": "k", "w": "v", "z": "j", "x": "x", "c": "c"
}

FD_VOW = "aeiou"
FD_PUNCT = ".,!?;:'\"()[]{}|/\\-_*#@&+=~`—–।"
FD_MIN = 2

FD_STOP = [
    "song", "songs", "gana", "gaana", "geet", "play",
    "sunao", "suna", "bajao", "baja", "wala", "wali",
    "full", "video", "audio", "hindi", "new", "old",
    "ka", "ki", "ke", "ko", "se", "me", "mein", "hai",
    "the", "of", "and", "mp3", "lyrics", "lyrical"
]


def fd_deva(txt):
    out = ""
    i = 0
    while i < len(txt):
        c = txt[i]
        i = i + 1
        if c in FD_DEVA:
            out = out + FD_DEVA[c]
            continue
        o = ord(c)
        if o >= 0x0900 and o <= 0x097f:
            continue
        out = out + c
    return out


def fd_squash(w):
    out = ""
    i = 0
    while i < len(w):
        c = w[i]
        i = i + 1
        if len(out) > 0 and out[len(out) - 1] == c:
            continue
        out = out + c
    return out


def fd_digraph(w):
    i = 0
    while i < len(FD_DIG):
        pair = FD_DIG[i]
        i = i + 1
        w = w.replace(pair[0], pair[1])
    out = ""
    i = 0
    while i < len(w):
        c = w[i]
        i = i + 1
        if c in FD_ONE:
            out = out + FD_ONE[c]
            continue
        out = out + c
    return out


def fd_skel(w):
    if len(w) == 0:
        return ""
    out = ""
    i = 0
    while i < len(w):
        c = w[i]
        i = i + 1
        if c in FD_VOW:
            if len(out) == 0:
                out = out + c
            continue
        out = out + c
    if len(out) == 0:
        return w[:1]
    return out


def fd_word(w):
    w = fd_deva(w).lower()
    w = fd_squash(w)
    w = fd_digraph(w)
    w = fd_skel(w)
    return fd_squash(w)


def fd_split(txt):
    out = ""
    i = 0
    while i < len(txt):
        c = txt[i]
        i = i + 1
        if FD_PUNCT.find(c) >= 0:
            out = out + " "
            continue
        if c.isdigit():
            out = out + " "
            continue
        out = out + c
    return out.split()


def fd_toks(txt):
    raw = fd_split(txt)
    out = []
    i = 0
    while i < len(raw):
        w = raw[i]
        i = i + 1
        if w.lower() in FD_STOP:
            continue
        f = fd_word(w)
        if len(f) < FD_MIN:
            continue
        if f in out:
            continue
        out.append(f)
    return out


def fd_cover(qtok, txt):
    if len(qtok) == 0:
        return 0.0
    hay = fd_toks(txt)
    if len(hay) == 0:
        return 0.0
    hit = 0
    i = 0
    while i < len(qtok):
        w = qtok[i]
        i = i + 1
        if fd_find(hay, w) == 1:
            hit = hit + 1
    return float(hit) / float(len(qtok))


def fd_find(hay, w):
    i = 0
    while i < len(hay):
        h = hay[i]
        i = i + 1
        if h == w:
            return 1
        if len(w) >= 3 and h.find(w) >= 0:
            return 1
        if len(h) >= 3 and w.find(h) >= 0:
            return 1
    return 0
