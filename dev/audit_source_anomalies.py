"""DEV-ONLY: hunt for errors in sacredtradition.am's own feast text.

The oracle tests prove the engine reproduces the source. They say nothing about whether
the SOURCE is right -- and after ``fix/feast-name-accuracy`` the engine matches it on
9496/9496 days, so every typo the source makes is now a typo the engine serves. This
script is the other half of the contract: it looks for text the source got wrong.

Nine detectors, run over the corrected text (``apply_source_corrections``), so anything
already registered in ``dev/source_corrections`` is silent and only NEW findings print.

  1  DOUBLED WORD        "Saints Saints Jacoc"
  2  EDGE PUNCTUATION    a component opening or closing on stray punctuation
  3  SPACING             double spaces, space before a comma, comma with no space after
  4  MIXED SEPARATOR     a position label comma-joined into a commemoration component,
                         where every other day uses the em-dash
  5  NEAR-DUPLICATE      two components that differ in a few characters -- one spelling of
                         a recurring feast against another, which is how a one-off typo
                         shows up when the same feast recurs 26 times
  6  TOKEN VARIANT       one word spelled two ways across the corpus (Philip/Phillip)
  7  UNKNOWN WORD        a lowercase word in no dictionary -- catches "Begining",
                         "faithfuls", "mans", which detectors 5 and 6 miss because the
                         source makes them CONSISTENTLY, in all 26 years
  8  DIGITS DISAGREE     a number in the English name that its own Armenian name
                         contradicts
  9  ORDINAL DISAGREES   an ordinal word in the English name that the Armenian numeral
                         contradicts

Detectors 8 and 9 are the strongest, and the reason the ``hy`` map is worth having beyond
translation: the source states the same fact twice, independently, so it can be caught
contradicting itself. Nothing else here is an oracle -- the rest flag candidates for a
human to judge.

Usage:
    python dev/audit_source_anomalies.py             # findings, grouped by detector
    python dev/audit_source_anomalies.py -v          # every occurrence, not just a sample
"""

import collections
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                       # noqa: E402
from dev.source_corrections import apply_source_corrections            # noqa: E402
from armenian_lectionary.engine import (                               # noqa: E402
    _OBSERVANCE_SEP, OBSERVANCE_NAMES_HY_PATH,
)

WORDLIST = "/usr/share/dict/words"

# Words the dictionary lacks that are nonetheless right here: liturgical vocabulary,
# transliterated Armenian, and ordinary words web2 predates. Kept short on purpose -- an
# entry here silences a real detector, so each one is a judgement recorded, not a mute.
KNOWN_WORDS = {
    "aliturgical", "apostles", "catechumens", "catholicos", "eastertide", "etchmiadzin",
    "faithful", "forerunner", "hermits", "martyrs", "melodist", "moneyless", "myrophores",
    "octave", "patriarchs", "pentecost", "prophets", "relics", "saints", "sons",
    "stylite", "theophany", "transfiguration", "translators", "virgins", "wonderworker",
    "wonderworkers", "disciples", "companions", "confessor", "deacons", "eunuchs",
    "evangelists", "physicians", "soldiers", "daughters", "grandsons", "notaries",
    "priests", "angels", "children", "sisters", "women", "others", "sunday", "temple",
    "vardavar", "vespers",
}

# Armenian numerals as the source writes them in feast names, lowercase.
_HY_ORDINALS = {
    "առաջին": 1, "երկրորդ": 2, "երրորդ": 3, "չորրորդ": 4, "հինգերորդ": 5,
    "վեցերորդ": 6, "եօթներորդ": 7, "ութերորդ": 8, "իններորդ": 9, "տասներորդ": 10,
    "քսաներորդ": 20, "երեսներորդ": 30, "քառասներորդ": 40, "յիսներորդ": 50,
}
_EN_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12,
    "thirteenth": 13, "fourteenth": 14, "fifteenth": 15, "sixteenth": 16,
    "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
    "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
}

_POSITION_PHRASES = ("Fast day", "Feast day", "day of ", "Sunday after", "Sunday of")


def load_words():
    if not os.path.exists(WORDLIST):
        return None
    with open(WORDLIST, encoding="utf-8", errors="ignore") as fh:
        return {w.strip().lower() for w in fh if w.strip()}


def components(feast):
    return [c.strip() for c in (feast or "").split(_OBSERVANCE_SEP) if c.strip()]


def corrected_days():
    """Every cached day with ground truth, after the registered corrections."""
    out = {}
    for iso, day in sorted(load_all().items()):
        d = dict(day)
        d["date"] = iso
        d = apply_source_corrections(d)
        if (d.get("feast") or "").strip():
            out[iso] = d["feast"].strip()
    return out


# --------------------------------------------------------------------------- #
# Detectors. Each takes the {iso: feast} map (plus what it needs) and returns
# [(headline, [iso, ...]), ...].
# --------------------------------------------------------------------------- #

def detect_doubled_word(comps):
    hits = collections.defaultdict(list)
    for comp, isos in comps.items():
        for m in re.finditer(r"\b(\w+)\s+\1\b", comp):
            hits[f"{m.group(0)!r} in {comp!r}"].extend(isos)
    return sorted(hits.items())


def detect_edge_punctuation(comps):
    hits = collections.defaultdict(list)
    for comp, isos in comps.items():
        if comp[-1] in ".,;:-" and not comp.endswith(")"):
            hits[f"trailing {comp[-1]!r}: {comp!r}"].extend(isos)
        if comp[0] in ".,;:-":
            hits[f"leading {comp[0]!r}: {comp!r}"].extend(isos)
    return sorted(hits.items())


def detect_spacing(comps):
    hits = collections.defaultdict(list)
    for comp, isos in comps.items():
        if "  " in comp:
            hits[f"double space: {comp!r}"].extend(isos)
        if re.search(r"\s+[,;.]", comp):
            hits[f"space before punctuation: {comp!r}"].extend(isos)
        if re.search(r",(?!\d)\S", comp):     # not a digit group: "the 20,000 Martyrs"
            hits[f"no space after comma: {comp!r}"].extend(isos)
    return sorted(hits.items())


def detect_mixed_separator(comps):
    """A position label comma-joined into a commemoration instead of em-dash-separated."""
    hits = collections.defaultdict(list)
    for comp, isos in comps.items():
        head = comp.split(",")[0].strip()
        if "," in comp and any(head.startswith(p) or p in head
                               for p in ("Fast day", "Feast day")):
            hits[f"{head!r} comma-joined: {comp!r}"].extend(isos)
    return sorted(hits.items())


# Pairs this audit has already judged and cleared. Each is the source using two words
# that LOOK like a typo of one another but are not: it distinguishes them deliberately.
CLEARED_PAIRS = {
    # The Conception of the Theotokos (Dec 9) reads "Feast day" where the Advent fast
    # would otherwise put "Fast day" -- the feast outranking the fast. 16 occurrences, and
    # engine._POSITION_FAMILIES reproduces the distinction by civil date.
    ("Fast day", "Feast day"),
}

# Token pairs judged and cleared: near-identical spellings that name different things.
CLEARED_TOKENS = {
    ("Armenia", "Armenian"),      # the country and the adjective
    ("MOTHER", "other"),          # a shouted feast title against an ordinary word
    ("Simeon", "Simon"),          # Simon the Apostle; Simeon the Stylite, and the
                                  # Simeon called the Relative of Christ -- three people
    ("Theodore", "Theodoret"),    # Theodore the Tyron / Stratelates; Theodoret the
                                  # Priest of Antioch -- different saints
}


def detect_near_duplicates(comps, counts):
    """Component pairs differing by a few characters -- one is likely a typo of the other.

    Only reported when one side is much rarer, which is what a one-off scrape slip looks
    like against 25 good years.
    """
    hits = {}
    keys = sorted(comps)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if abs(len(a) - len(b)) > 4 or a == b:
                continue
            if tuple(sorted((a, b))) in CLEARED_PAIRS:
                continue
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio < 0.94:
                continue
            rare, common = (a, b) if counts[a] <= counts[b] else (b, a)
            if counts[rare] * 4 > counts[common]:
                continue          # both common: a real variant pair, not a slip
            hits[f"{rare!r} ({counts[rare]}x) vs {common!r} ({counts[common]}x)"] = \
                sorted(comps[rare])
    return sorted(hits.items())


def _same_lemma(a, b):
    """True if two tokens are the same word in different inflections.

    Singular/plural and possessive pairs (Martyr/Martyrs, Father/Fathers) dominate any
    similarity measure over this corpus and are never the defect being hunted, so they are
    excluded rather than ranked.
    """
    lo, hi = sorted((a.lower(), b.lower()), key=len)
    return hi in (lo + "s", lo + "es", lo + "'s") or (lo.endswith("y")
                                                      and hi == lo[:-1] + "ies")


def detect_token_variants(comps, counts):
    """One word spelled two ways across the corpus -- the source disagreeing with itself
    about a name (Philip/Phillip, Nicolas/Nicholas).

    Restricted to pairs where one spelling is a small minority: two forms in comparable
    use are how the source refers to two different people (Cyril/Cyrillus, Gregory the
    Wonderworker vs. of Nyssa), while a 1-in-3 minority spelling of the same name is a
    slip. Inflections of one word are excluded by :func:`_same_lemma`.
    """
    weight = collections.Counter()
    where = collections.defaultdict(set)
    for comp, isos in comps.items():
        for tok in re.findall(r"\b[A-Za-z]{4,}\b", comp):
            weight[tok] += counts[comp]
            where[tok].update(isos)
    hits = {}
    toks = sorted(weight)
    for i, a in enumerate(toks):
        for b in toks[i + 1:]:
            if a.lower() == b.lower() or abs(len(a) - len(b)) > 2:
                continue
            if _same_lemma(a, b) or tuple(sorted((a, b))) in CLEARED_TOKENS:
                continue
            if difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() < 0.90:
                continue
            rare, common = (a, b) if weight[a] <= weight[b] else (b, a)
            if weight[rare] * 2 > weight[common]:
                continue          # comparable use: two names, not one misspelled
            hits[f"{rare} ({weight[rare]}x) vs {common} ({weight[common]}x)"] = \
                sorted(where[rare])[:6]
    return sorted(hits.items())


_SUFFIXES = (("s", ""), ("es", ""), ("ed", ""), ("ed", "e"), ("ing", ""), ("ing", "e"),
             ("ly", ""), ("'s", ""), ("ies", "y"))


def _in_dictionary(tok, words):
    """``tok`` or an uninflected form of it is a dictionary word."""
    low = tok.lower()
    if low in words or low in KNOWN_WORDS:
        return True
    return any(low.endswith(suf) and (low[:-len(suf)] + repl) in words
               for suf, repl in _SUFFIXES)


def detect_unknown_words(comps, words):
    """Lowercase words in no dictionary -- a misspelling the source makes consistently.

    The backstop for the detectors above, which all work by finding the source
    disagreeing with itself and so are blind to an error it makes in all 26 years
    ("Begining of the Fast"). Restricted to lowercase words: proper nouns are
    legitimately absent from any word list and there are hundreds of them here.

    Its blind spot in turn is a misspelling that is itself a word -- "the poor mans" and
    "many faithfuls" both pass a dictionary. Those came out of reading all 187
    commemoration components, which this corpus is small enough to make practical, and
    which is what to do again after a re-fetch adds any.
    """
    if words is None:
        return []
    hits = collections.defaultdict(list)
    for comp, isos in comps.items():
        for tok in re.findall(r"\b[a-z]{3,}\b", comp):
            if not _in_dictionary(tok, words):
                hits[f"{tok!r} in {comp!r}"].extend(isos)
    return sorted(hits.items())


def _hy_map():
    if not os.path.exists(OBSERVANCE_NAMES_HY_PATH):
        return {}
    with open(OBSERVANCE_NAMES_HY_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("feasts", data) if isinstance(data, dict) else {}


def detect_digit_disagreement(comps, hy):
    """A YEAR the English states and its own Armenian name contradicts.

    Years only, not every number: the English writes a council's attendance in digits
    ("150 Fathers") where the Armenian writes it in words ("հարիւր յիսուն"), so comparing
    all digits reports a disagreement on every one of them. Both languages write the year
    in digits, so that comparison is exact -- and it is what caught the Council of Ephesus
    dated 341 in English and 431 in Armenian.
    """
    hits = {}
    for comp, isos in comps.items():
        arm = hy.get(comp)
        if not arm:
            continue
        en_years = set(re.findall(r"\b(\d{3,4})\b", comp))
        hy_years = set(re.findall(r"\b(\d{3,4})\b", arm))
        if en_years and hy_years and not (en_years & hy_years):
            hits[f"en {sorted(en_years)} vs hy {sorted(hy_years)}: {comp!r} / {arm!r}"] = \
                sorted(isos)[:4]
    return sorted(hits.items())


def detect_ordinal_disagreement(comps, hy):
    """An ordinal word the English states and the Armenian numeral contradicts."""
    hits = {}
    for comp, isos in comps.items():
        arm = hy.get(comp)
        if not arm:
            continue
        en = {_EN_ORDINALS[w] for w in re.findall(r"\b[A-Za-z]+\b", comp.lower())
              if w in _EN_ORDINALS}
        hy_vals = {v for w, v in _HY_ORDINALS.items() if w in arm.lower()}
        if en and hy_vals and not (en & hy_vals):
            hits[f"en {sorted(en)} vs hy {sorted(hy_vals)}: {comp!r} / {arm!r}"] = \
                sorted(isos)[:4]
    return sorted(hits.items())


def main():
    verbose = "-v" in sys.argv
    days = corrected_days()
    comps = collections.defaultdict(list)
    for iso, feast in days.items():
        for c in components(feast):
            comps[c].append(iso)
    counts = {c: len(v) for c, v in comps.items()}
    words = load_words()
    hy = _hy_map()

    print(f"{len(days)} days with ground truth, {len(comps)} distinct feast components")
    if words is None:
        print(f"(no {WORDLIST}; UNKNOWN WORD detector skipped)")
    if not hy:
        print("(no observance_names_hy.json; the two cross-language detectors are skipped)")
    print()

    checks = (
        ("1  DOUBLED WORD", detect_doubled_word(comps)),
        ("2  EDGE PUNCTUATION", detect_edge_punctuation(comps)),
        ("3  SPACING", detect_spacing(comps)),
        ("4  MIXED SEPARATOR", detect_mixed_separator(comps)),
        ("5  NEAR-DUPLICATE", detect_near_duplicates(comps, counts)),
        ("6  TOKEN VARIANT", detect_token_variants(comps, counts)),
        ("7  UNKNOWN WORD", detect_unknown_words(comps, words)),
        ("8  DIGITS DISAGREE", detect_digit_disagreement(comps, hy)),
        ("9  ORDINAL DISAGREES", detect_ordinal_disagreement(comps, hy)),
    )

    total = 0
    for title, findings in checks:
        print(f"=== {title} -- {len(findings)}")
        total += len(findings)
        for headline, isos in (findings if verbose else findings[:25]):
            print(f"  {headline}")
            print(f"      {len(isos)}x, e.g. {', '.join(sorted(isos)[:4])}")
        if not verbose and len(findings) > 25:
            print(f"  ... {len(findings) - 25} more (-v)")
        print()

    if not total:
        print("0 findings -- every judged anomaly is registered in dev/source_corrections "
              "or cleared above by name.")
        return 0
    print(f"{total} findings. None is automatically a defect: each is a candidate for a "
          "human to judge. Anything judged wrong belongs in dev/source_corrections so the "
          "engine serves the corrected form; anything judged fine belongs in CLEARED_PAIRS "
          "/ CLEARED_TOKENS / KNOWN_WORDS here, with the reason. Either way the next run "
          "goes quiet, which is what makes a clean run mean something.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
