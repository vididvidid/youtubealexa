#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
FAIL=0

hdr() { printf '\n== %s\n' "$1"; }
bad() { printf '   FAIL %s\n' "$1"; FAIL=$((FAIL+1)); }
good() { printf '   ok   %s\n' "$1"; }

hdr "python version"
if python3 -c "
import sys
assert sys.version_info >= (3, 11), (
    'need python 3.11 or newer, yt-dlp requires it, got %d.%d'
    % (sys.version_info[0], sys.version_info[1]))
" 2>/tmp/pyver.err; then
  good "$(python3 --version)"
else
  bad "python too old"; cat /tmp/pyver.err
fi

hdr "python compiles"
if python3 -m py_compile src/*.py bin/*.py api/*.py tools/*.py \
   2>/tmp/pyc.err; then
  good "all modules compile"
else
  bad "compile errors"; cat /tmp/pyc.err
fi

hdr "80 column limit"
OVER=0
for f in $(git ls-files 2>/dev/null || find . -type f \
           -not -path './.git/*' -not -path './site/*'); do
  case "$f" in
    *.png|*.jpg|*.gif|*.deb|*.tar.gz|site/*) continue ;;
  esac
  [ -f "$f" ] || continue
  N=$(awk 'length>80{c++}END{print c+0}' "$f")
  if [ "$N" != "0" ]; then
    printf '   FAIL %s: %s lines\n' "$f" "$N"
    OVER=$((OVER+N))
  fi
done
if [ "$OVER" = "0" ]; then
  good "nothing over 80 columns"
else
  FAIL=$((FAIL+1))
fi

hdr "no comments in source"
C=$(grep -n '^[[:space:]]*#' src/*.py bin/*.py api/*.py \
    tools/*.py 2>/dev/null | grep -v '#!/' | wc -l)
if [ "$C" = "0" ]; then
  good "no python comment lines"
else
  bad "$C python comment lines"
  grep -n '^[[:space:]]*#' src/*.py bin/*.py api/*.py \
    tools/*.py 2>/dev/null | grep -v '#!/' | head -5
fi
J=$(grep -c '//' src/web/app.js 2>/dev/null)
J=${J:-0}
if [ "$J" = "0" ]; then
  good "no js comment lines"
else
  bad "$J js comment lines"
fi

hdr "shell scripts parse"
SH=0
for f in install.sh bin/*.sh tools/*.sh; do
  [ -f "$f" ] || continue
  bash -n "$f" 2>/dev/null || { bad "$f"; SH=1; }
done
[ "$SH" = "0" ] && good "all shell scripts parse"

hdr "json valid"
if python3 -c "
import json, sys
for f in ['vercel.json','docs/interaction-hi-IN.json']:
    json.load(open(f))
" 2>/dev/null; then
  good "vercel.json and interaction model parse"
else
  bad "invalid json"
fi

hdr "alexa interaction model"
if python3 -c "
import json, sys
d = json.load(open('docs/interaction-hi-IN.json'))
lm = d['interactionModel']['languageModel']
pi = None
for i in lm['intents']:
    if i['name'] == 'PlayIntent':
        pi = i
assert pi != None, 'no PlayIntent'
assert pi['slots'][0]['type'] == 'AMAZON.SearchQuery'
for s in pi['samples']:
    assert s.strip() != '{query}', 'bare slot sample'
    assert '{query}' in s or 'query' not in s
need = ['AMAZON.PauseIntent','AMAZON.ResumeIntent',
        'AMAZON.NextIntent','AMAZON.PreviousIntent',
        'AMAZON.StartOverIntent','AMAZON.LoopOnIntent',
        'AMAZON.LoopOffIntent','AMAZON.ShuffleOnIntent',
        'AMAZON.ShuffleOffIntent','AMAZON.RepeatIntent']
have = [i['name'] for i in lm['intents']]
for n in need:
    assert n in have, 'missing ' + n
" 2>/tmp/model.err; then
  good "SearchQuery carrier phrases and playback intents"
else
  bad "model problem"; cat /tmp/model.err
fi

hdr "no unresolved placeholders"
PAT="OWNER[/]REPO"
P=$(grep -rlE "$PAT" --include='*.md' --include='*.sh' \
    --include='*.py' --include='*.yml' --include='*.json' . \
    2>/dev/null | grep -v '^./site/' | wc -l)
if [ "$P" = "0" ]; then
  good "no repo-slug placeholder left in tracked files"
else
  bad "$P file(s) still carry the slug placeholder"
  grep -rlE "$PAT" --include='*.md' --include='*.sh' \
    --include='*.py' --include='*.yml' --include='*.json' . \
    2>/dev/null | grep -v '^./site/' | sed 's/^/        /'
fi

hdr "no hardcoded api keys"
K=$(grep -rlE "AIza[0-9A-Za-z_-]{30,}" --include='*.py' \
    --include='*.js' --include='*.sh' --include='*.json' \
    --include='*.md' . 2>/dev/null | grep -v '^./site/' | wc -l)
if [ "$K" = "0" ]; then
  good "no google api key shaped literals in tracked files"
else
  bad "$K file(s) carry an AIza... literal"
  grep -rlE "AIza[0-9A-Za-z_-]{30,}" --include='*.py' \
    --include='*.js' --include='*.sh' --include='*.json' \
    --include='*.md' . 2>/dev/null | grep -v '^./site/' \
    | sed 's/^/        /'
fi

hdr "stdlib shadowing"
if python3 -c "
import os
import sys
import sysconfig
std = sysconfig.get_paths()['stdlib']
names = [n[:-3] for n in os.listdir('src') if n.endswith('.py')]
hit = []
for n in names:
    if n in sys.builtin_module_names:
        hit.append(n)
        continue
    if os.path.isfile(os.path.join(std, n + '.py')):
        hit.append(n)
        continue
    if os.path.isdir(os.path.join(std, n)):
        hit.append(n)
assert len(hit) == 0, 'shadows stdlib: ' + ', '.join(hit)
" 2>/tmp/shadow.err; then
  good "no module shadows the stdlib"
else
  bad "shadowing"; cat /tmp/shadow.err
fi

hdr "web console ids"
if python3 -c "
import re
h = open('src/web/index.html').read()
j = open('src/web/app.js').read()
ids = set(re.findall(r'id=\"([A-Za-z0-9_-]+)\"', h))
used = set(re.findall(r'el\(\"([A-Za-z0-9_-]+)\"\)', j))
missing = sorted(used - ids)
assert len(missing) == 0, 'el() ids not in html: %s' % missing
" 2>/tmp/ids.err; then
  good "every el() id exists in the markup"
else
  bad "missing ids"; cat /tmp/ids.err
fi

hdr "docs site builds"
if python3 tools/mkdocs.py /tmp/sitecheck >/dev/null 2>&1; then
  N=$(ls /tmp/sitecheck/*.html 2>/dev/null | wc -l)
  if [ "$N" -ge 9 ]; then
    good "$N pages generated"
  else
    bad "only $N pages generated"
  fi
  python3 -c "
import glob, re, sys
bad = 0
for f in glob.glob('/tmp/sitecheck/*.html'):
    t = open(f).read()
    for tag in ['h1','h2','p','pre','article','main','nav']:
        o = len(re.findall(r'<%s[ >]' % tag, t))
        c = t.count('</%s>' % tag)
        if o != c:
            print('   FAIL %s <%s> %d/%d' % (f, tag, o, c))
            bad = 1
sys.exit(bad)
" && good "generated html tags balanced" || FAIL=$((FAIL+1))
else
  bad "mkdocs.py failed"
fi

hdr "offline test suite"
if python3 tools/selftest.py > /tmp/self.out 2>&1; then
  good "$(tail -1 /tmp/self.out | tr -s ' ')"
else
  bad "selftest failed"
  tail -20 /tmp/self.out
fi

hdr "node js syntax"
if command -v node >/dev/null 2>&1; then
  node --check src/web/app.js 2>/dev/null \
    && good "app.js parses" || bad "app.js syntax"
else
  printf '   skip node not installed\n'
fi

printf '\n'
if [ "$FAIL" = "0" ]; then
  printf 'ALL CHECKS PASSED\n\n'
  exit 0
fi
printf '%s CHECK GROUPS FAILED\n\n' "$FAIL"
exit 1
