"""DEV-ONLY: scrape sacredtradition.am for the Armenian (``hy``) names of every
feast and Bible book the engine can emit, and build the shipped translation tables.

NOT imported by the app at runtime. The runtime stays offline: this tool writes two
static JSON maps that the engine loads to answer ``language="hy"`` requests.

How it works
------------
The English ground truth already lives in ``dev/reference_data/`` (one JSON per day,
2001-2027, scraped at ``iL=2``). The same source pages render in Classical Armenian at
``iL=0`` with the readings in the *same order*, so for a given day English reading *i*
and Armenian reading *i* are the same citation with only the book name translated
(the ``chapter.verse`` tail is identical across languages). We exploit that to:

  1. pick one representative date per distinct English feast string, and per book head;
  2. fetch each representative date once at ``iL=0``;
  3. pair English<->Armenian by matching the numeric tail, voting the book-head and
     feast-name translations; and
  4. write ``armenian_lectionary/data/{feast_names_hy,book_names_hy}.json``.

Usage:
    python dev/fetch_translations.py            # build both maps (uses hy cache)
    python dev/fetch_translations.py --force    # re-fetch every hy page
"""

import collections
import datetime
import glob
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The engine serves some validated-composite feasts under a canonicalized English name
# (e.g. the source's "Fiest of ..." typo repaired to "Feast of ..."); apply the same
# reconciliation to the map keys so those labels resolve. Optional: degrade to identity
# if the dev module is unavailable.
try:
    from dev.source_corrections import canonical_commem, apply_source_corrections
except Exception:  # pragma: no cover - dev-only convenience
    def canonical_commem(c):
        return c

    def apply_source_corrections(day):
        return day

HERE = os.path.dirname(__file__)
REF_DIR = os.path.join(HERE, "reference_data")
HY_CACHE_DIR = os.path.join(HERE, "reference_data_hy")
DATA_DIR = os.path.join(os.path.dirname(HERE), "armenian_lectionary", "data")
FEAST_MAP_PATH = os.path.join(DATA_DIR, "feast_names_hy.json")
BOOK_MAP_PATH = os.path.join(DATA_DIR, "book_names_hy.json")

# iL=0 -> Classical Armenian (iL=2 is English, iL=1 Russian). Everything else in the
# query string mirrors dev/fetch_reference.py so we hit the identical calendar page.
URL = ("https://www.sacredtradition.am/Calendar/nter.php"
       "?NM=0&iM=1103&iA=0&iL=0&ymd={ymd}")

# Must match the engine's join convention (armenian_lectionary.engine._FEAST_SEP) and
# dev/fetch_reference.py so feast components split/rejoin identically across languages.
FEAST_SEP = " — "

# A citation is "<book head> <chapter.verse tail>"; the tail is language-independent.
_REF_RE = re.compile(r"^(.*?)(\d+\.\d.*)$")


def _strip(s: str) -> str:
    """Collapse the source's <br>-delimited components onto FEAST_SEP (mirrors
    dev/fetch_reference.py so the Armenian feast splits into the same components)."""
    import html as _html
    s = re.sub(r"\s*<br\s*/?>\s*", "\x00", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = _html.unescape(s)
    parts = [p.strip() for p in s.split("\x00") if p.strip()]
    return FEAST_SEP.join(parts)


# --------------------------------------------------------------------------- #
# Orthography: reformed ("Soviet"/Abeghyan) -> traditional (Mashtots)
# --------------------------------------------------------------------------- #
# sacredtradition.am enters the feast titles in traditional orthography but the
# *reading* (book) names in Modern-Eastern reformed orthography. The Armenian Church
# uses the Mashtots orthography, so we reverse the reform on the book names only,
# preserving the source's words/morphology (orthography-only, per the maintainer).

# Systematic, context-free reversals (safe as plain substring swaps on this data set).
_MASHTOTS_SYSTEMATIC = (
    ("ություն", "ութիւն"),   # the -ություն abstract suffix
    ("Ավ", "Աւ"),            # /aw/ word-initial capital (Ավետարան -> Աւետարան)
    ("ավ", "աւ"),            # the /aw/ diphthong: Թագավոր, Նավե, Նավում…
    ("և", "եւ"),             # the ligature -> classical digraph
    ("առաքյալ", "առաքեալ"),  # "apostle": յա -> եա
    ("մարգարե", "մարգարէ"),  # "prophet": final ե -> է
)

# Proper-noun reversals (ե->է in stressed syllables; reformed initial հ-> classical
# յ- for the Greek Io-/I- names such as John/Joel/Jonah; Hosea's եե->էէ). Applied
# AFTER the systematic pass,
# so the search sides are already in their post-systematic form.
_MASHTOTS_PROPER = (
    ("Հովհաննես", "Յովհաննէս"),   # John (Gospel genitive + the three epistles)
    ("Մատթեոս", "Մատթէոս"),       # Matthew
    ("Դանիել", "Դանիէլ"),
    ("Եզեկիել", "Եզեկիէլ"),
    ("Հովել", "Յովէլ"),           # Joel
    ("Հովնան", "Յովնան"),         # Jonah
    ("Հակոբ", "Յակոբ"),           # James
    ("Հուդ", "Յուդ"),             # Jude (Հուդա) + Judith (Հուդիթ)
    ("Հոբ", "Յոբ"),               # Job
    ("Հեսու", "Յեսու"),           # Joshua (son of Nun)
    ("Նավե", "Նաւէ"),             # Nun (post-systematic: already Նաւե -> Նաւէ)
    ("Նաւե", "Նաւէ"),
    ("Անգե", "Անգէ"),             # Haggai
    ("Օսեե", "Օսէէ"),             # Hosea
    ("Տիմոթեոս", "Տիմոթէոս"),      # Timothy
)


def to_mashtots(s: str) -> str:
    """Convert a reformed-orthography book name to traditional (Mashtots) orthography,
    preserving the source's words. Only the reform is reversed (see the tables above)."""
    for a, b in _MASHTOTS_SYSTEMATIC:
        s = s.replace(a, b)
    for a, b in _MASHTOTS_PROPER:
        s = s.replace(a, b)
    return s


def _split_ref(ref: str):
    """('St. Paul's Epistle to the Hebrews', '12.18-27') or None if not a citation."""
    m = _REF_RE.match(ref.strip())
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


def fetch_hy(d: datetime.date, force: bool = False) -> dict:
    """Return {date, feast, readings:[refs]} for a day at iL=0, using a local cache."""
    os.makedirs(HY_CACHE_DIR, exist_ok=True)
    path = os.path.join(HY_CACHE_DIR, d.isoformat() + ".json")
    if os.path.exists(path) and not force:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    req = urllib.request.Request(URL.format(ymd=d.strftime("%Y%m%d")),
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    dname = re.search(r"<div class=dname>(.*?)</div>", raw, re.S)
    refs = [_strip(m) for m in re.findall(r"<b>(.*?)</b>", raw, re.S)]
    refs = [r for r in refs if re.search(r"\d+\.\d", r)]
    data = {
        "date": d.isoformat(),
        "feast": _strip(dname.group(1)) if dname else "",
        "readings": refs,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _representative_dates():
    """Pick the minimal date set that surfaces every distinct English feast and book
    head. Returns (dates, feast_date, en_by_date) where en_by_date[date] is the cached
    English record so we can pair it with the Armenian fetch without re-reading."""
    feast_date = {}       # english feast string -> earliest date it appears
    book_date = {}        # english book head    -> a date it appears on
    en_by_date = {}
    for f in sorted(glob.glob(os.path.join(REF_DIR, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            rec = json.load(fh)
        # Apply the same on-read source corrections as every other cache reader (folds the
        # Cyrillic homoglyphs in the English feast text) so the keys below are already clean.
        apply_source_corrections(rec)
        date = rec["date"]
        keep = False
        feast = rec.get("feast", "")
        if feast and feast not in feast_date:
            feast_date[feast] = date
            keep = True
        for r in rec.get("readings", []):
            sp = _split_ref(r)
            if sp and sp[0] not in book_date:
                book_date[sp[0]] = date
                keep = True
        if keep:
            en_by_date[date] = rec
    dates = sorted(set(feast_date.values()) | set(book_date.values()))
    return dates, feast_date, en_by_date


def build(force: bool = False):
    dates, feast_date, en_by_date = _representative_dates()
    print(f"{len(feast_date)} distinct feasts, "
          f"{len(dates)} representative dates to fetch")

    feast_votes = collections.defaultdict(collections.Counter)   # en feast -> hy votes
    book_votes = collections.defaultdict(collections.Counter)    # en head  -> hy votes
    misaligned = []
    fetched = 0
    for i, date in enumerate(dates, 1):
        d = datetime.date.fromisoformat(date)
        path = os.path.join(HY_CACHE_DIR, date + ".json")
        was_cached = os.path.exists(path) and not force
        hy = fetch_hy(d, force=force)
        en = en_by_date[date]

        # en records arrive already source-corrected (Cyrillic homoglyphs folded) via
        # _representative_dates, so the English keys match the engine's cleaned output.
        if en.get("feast") and hy.get("feast"):
            feast_votes[en["feast"]][hy["feast"]] += 1
            # Also vote per component. The engine composes some labels itself
            # (Annunciation collisions, the Genocide-Remembrance note, ...) by joining
            # FEAST_SEP components, so a per-component map lets those translate even
            # when the exact composite was never scraped as one string. Only pair when
            # both sides split into the same number of components (same structure).
            en_parts = en["feast"].split(FEAST_SEP)
            hy_parts = hy["feast"].split(FEAST_SEP)
            if len(en_parts) == len(hy_parts) > 1:
                for ep, hp in zip(en_parts, hy_parts):
                    feast_votes[ep][hp] += 1

        # Pair readings by matching numeric tail (order is normally identical; the tail
        # is language-independent, so it both aligns and confirms the pairing). A few
        # citations differ by a versification convention between the source's English and
        # Armenian (e.g. 3 John "1.1-14" vs "1.1-15", Judith "15.7" vs "15.8"), so their
        # tails won't match; fall back to positional pairing when both lists have equal
        # length (a strong same-order signal). Voting absorbs any residual noise.
        en_split = [(_split_ref(r), r) for r in en["readings"]]
        hy_split = [_split_ref(r) for r in hy["readings"]]
        hy_by_tail = {}
        for sp in hy_split:
            if sp:
                hy_by_tail.setdefault(sp[1], sp[0])
        equal_len = len(en_split) == len(hy_split)
        for i, (sp, raw) in enumerate(en_split):
            if not sp:
                continue
            head_en, tail = sp
            head_hy = hy_by_tail.get(tail)
            if head_hy is None and equal_len and hy_split[i]:
                head_hy = hy_split[i][0]      # positional fallback (versification skew)
            if head_hy is None:
                misaligned.append((date, raw))
                continue
            book_votes[head_en][head_hy] += 1

        if not was_cached:
            fetched += 1
            time.sleep(0.5)  # be polite to the server
        if i % 25 == 0 or i == len(dates):
            print(f"  {i}/{len(dates)} ({fetched} fetched)")

    feast_map = {en: votes.most_common(1)[0][0]
                 for en, votes in feast_votes.items()}
    # Book names arrive in reformed orthography; the Church uses Mashtots. Reverse the
    # reform (orthography only). Feast titles are already traditional, so leave them.
    book_map = {en: to_mashtots(votes.most_common(1)[0][0])
                for en, votes in book_votes.items()}

    # Add canonicalized-name aliases (the engine emits some validated-composite feasts
    # under a repaired English label). Only add where the canonical form isn't already a
    # scraped key, so genuine scraped names always win.
    for en, hy in list(feast_map.items()):
        canon = canonical_commem(en)
        if canon != en:
            feast_map.setdefault(canon, hy)

    # Report any English key that never resolved to an Armenian name.
    missing_feasts = sorted(set(feast_date) - set(feast_map))
    if missing_feasts:
        print(f"\nWARNING: {len(missing_feasts)} feasts had no Armenian name:")
        for f in missing_feasts[:20]:
            print(f"    {f!r}")
    if misaligned:
        print(f"\nNote: {len(misaligned)} readings had no tail-matched Armenian "
              f"pair (first 10):")
        for date, r in misaligned[:10]:
            print(f"    {date}: {r}")

    # Gate: no map key or value may carry a contaminant (Cyrillic/Greek homoglyph, curly
    # quote, ...). Fold known ones in normalize_confusables; anything else fails here so
    # the maintainer decides fold-vs-allow rather than silently shipping it.
    from dev.source_corrections import unexpected_chars
    dirty = []
    for name, m in (("feast_names_hy", feast_map), ("book_names_hy", book_map)):
        for k, v in m.items():
            for label, s in (("key", k), ("value", v)):
                bad = unexpected_chars(s)
                if bad:
                    dirty.append(f"{name} {label} {s!r}: unexpected {bad}")
    if dirty:
        raise ValueError("hy map contains unexpected characters:\n  "
                         + "\n  ".join(dirty[:20]))

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FEAST_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(feast_map, f, ensure_ascii=False, indent=2, sort_keys=True)
    with open(BOOK_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(book_map, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"\nWrote {len(feast_map)} feast names -> {FEAST_MAP_PATH}")
    print(f"Wrote {len(book_map)} book names  -> {BOOK_MAP_PATH}")


if __name__ == "__main__":
    build(force="--force" in sys.argv[1:])
