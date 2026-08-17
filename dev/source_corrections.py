"""Reviewed source-vs-cache reading corrections.

The governing principle is that a reading must be derivable from the Tōnats'oyts
canonical rubric, and the sacredtradition.am scrape (dev/reference_data/*.json) is a
TEST ORACLE only. Where the digitized Tōnats'oyts and the cache disagree and the source
is confidently correct (reviewed by the maintainer), the engine serves the SOURCE value
and these registries record the discrepancy so the residue tooling scores the source-
faithful output as correct rather than as a "miss" against a cache typo.

## Pre-Lent cohort (Sargis / Atom / Sukias / Voskian / Ghevond), First Vol pp.464-465

Every discrepancy here is a systematic ±1 verse-boundary / versification convention
difference (the pericope is the same); see docs/sources/tonatsooyts-prelent-cohort.md
for the grabar transcription and provenance. The cache uses a slightly different
Wisdom-of-Solomon numbering (source = cache + 1) and inclusive/exclusive endpoint
convention for a couple of Gospels.

IMPORTANT: two of these reading strings ("John 16.1-4", "Luke 12.4-9") ALSO occur on
unrelated feasts (Gayiane, the summer martyrs, All Saints) where the cache is authoritative
and the source itself uses that very range -- so these corrections are applied ONLY on the
days the engine ships from the pre-Lent cohort tier (Source == "first-volume-cohort"),
never globally.
"""

import datetime
import functools
import json
import os

from armenian_lectionary.engine import _FEAST_SEP

# cache reading string -> source (Tōnats'oyts First Vol p.464-465) reading string.
# Applied ONLY on first-volume-cohort days (scoped by the shipping tier, not by text).
COHORT_CORRECTIONS = {
    "Wisdom 6.11-20": "Wisdom 6.12-21",     # Atom OT (Wisdom versification, source = cache+1)
    "John 16.1-4": "John 16.1-5",           # Atom Gospel (endpoint, source = cache+1)
    "Luke 12.4-9": "Luke 12.4-8",           # Sukias Gospel (endpoint, source = cache-1)
    "Wisdom 5.15-22": "Wisdom 5.16-23",     # Ghevond OT (Wisdom versification, source = cache+1)
}


def apply_cohort_corrections(readings):
    """Map a list of cache readings to their source-faithful form for a cohort day."""
    return [COHORT_CORRECTIONS.get(r, r) for r in readings]


# --------------------------------------------------------------------------- #
# Reading-ORDER normalization
#
# sacredtradition.am re-ordered a single Easter Sunday's readings (2011-04-24) at some
# point after the corpus was first cached: the SAME 14 readings, but with the Resurrection
# Gospel (John 20.1-18) demoted from first to eleventh. Every OTHER year's Easter keeps the
# Resurrection Gospel leading, and the engine serves ONE modal entry for the Easter-offset-0
# coordinate, so this lone outlier order splits that entry's cross-year support and drops
# Easter-Sunday coverage (its "RESURRECTION..." name and readings fall through to the
# estimate tier). Restore the consensus order so a freshly re-fetched cache rebuilds the
# shipped artifacts identically. Applied by dev/analyze.load_all on the SAME reading set only.
# --------------------------------------------------------------------------- #
READING_ORDER_FIXES = {
    "2011-04-24": [
        "John 20.1-18", "Acts of the Apostles 1.1-8", "Mark 16.2-8", "John 19.38-42",
        "Luke 23.50-56", "Mark 15.42-16.1", "Matthew 27.57-66", "John 19.16-22",
        "John 11.1-46", "Acts of the Apostles 1.15-26", "Luke 24.13-35", "John 5.24-30",
        "John 19.31-37", "John 20.19-25",
    ],
}


def apply_reading_order(date_iso, readings):
    """Return ``readings`` in the consensus order for ``date_iso`` when a fix is registered
    and it is the SAME set (a pure reorder); otherwise return ``readings`` unchanged."""
    fixed = READING_ORDER_FIXES.get(date_iso)
    if fixed is not None and sorted(fixed) == sorted(readings):
        return list(fixed)
    return readings


# --------------------------------------------------------------------------- #
# Feast-NAME canonicalization (for tests/test_feast.py)
#
# The engine serves the feast/fast name of the day as "Liturgical Day". The test
# compares the *commemoration component* (dev/feast_names.commemoration_of) of that
# value against the sacredtradition.am scrape (the value bahk uses for AI context).
#
# A handful of fixed saint-keys are enumerated INCONSISTENTLY -- on BOTH sides. The
# scrape lists a saint's companions differently across years (Vahan of Goghtn alone vs.
# with his household; Athanasius & Cyril with or without Gregory; a cohort martyr alone
# vs. co-listed with the saints absorbed on a merge day), and the engine's own label
# varies too because the same saint is served by different tiers on its winter (Jan) and
# summer (Jul/Aug, Second-Volume cycle) occurrences. Neither side has a single canonical
# string, so an equivalence must collapse the variants SYMMETRICALLY.
#
# ``canonical_commem`` is applied to BOTH the scraped and engine commemorations. It is a
# deterministic function, so it can never make a day that already matches diverge (equal
# inputs -> equal outputs); it only reconciles the reviewed companion-enumeration variants
# below to their primary commemoration. Readings on these validated-tier days are cross-
# year validated identical -- it is the same liturgical day, named with a longer/shorter
# companion list.
# --------------------------------------------------------------------------- #

# Ordered (first match wins). Each entry: (predicate on the commemoration) -> canonical.
_FEAST_CANON_RULES = (
    ("Sts. Cyricus and His Mother Julitta",
     lambda c: c.startswith(("Saints Cyricus and His Mother Julitta",
                              "Sts. Cyricus and His Mother Julitta"))),
    ("Holy Fathers Sts. Athanasius and Cyril of Alexandria",
     lambda c: c.startswith(("Holy Fathers Saints Athanasius and Cyril of Alexandria",
                              "Holy Fathers Sts. Athanasius and Cyril of Alexandria"))),
    ("St. Vahan of Goghtn",
     lambda c: "Vahan of Goghtn" in c),
    ("The Hermit Saints Anton",
     lambda c: "Anton" in c and "Hermit" in c),
    ("Sts. Eugenius, Macarius, Valerius, Candidus and Aquila",
     lambda c: c.startswith(("Saints Eugenios", "Saints Eugenius",
                              "Sts. Eugenios", "Sts. Eugenius"))),
    ("St. Sargis the Warrior and his son Martiros and his Fourteen Soldiers",
     lambda c: c.startswith(("Saint Sargis the Warrior", "St. Sargis the Warrior"))),
    ("Sts. Atom and his soldiers",
     lambda c: c.startswith(("Saints Atom and his soldiers", "Sts. Atom and his soldiers"))),
    ("PRESENTATION OF OUR LORD TO THE TEMPLE",
     lambda c: "PRESENTATION OF OUR LORD TO THE TEMPLE" in c),
    # The Theotokos' Presentation (Nov 21) is typed with the first word shouted in 19 of
    # the 26 cached years and in plain title case in the other 7 -- the source disagreeing
    # with itself, with no rule to reproduce. The engine serves the title-case form (the
    # one the hy name map is keyed on); folding on case makes the two score as the same
    # commemoration, which they are.
    ("Presentation of the Holy Mother of God to the Temple",
     lambda c: c.lower().startswith("presentation of the holy mother of god to the temple")),
    # St. Theodore the Recruit: the scrape says "the General", the Tonats'oyts table
    # "the Tyron" (Greek Tiron/Recruit) -- the same soldier-martyr.
    ("Saint Theodore the General",
     lambda c: "Theodore the Tyron" in c or "Theodore the General" in c),
)


# The scrape mixes a few wrong-code-point characters into the *English* feast text that
# read identically to their canonical ASCII form, so fold each to the twin the rest of the
# data uses. Two kinds observed:
#   * Cyrillic homoglyphs (the source was evidently typed with a Cyrillic keyboard):
#     Cyrillic Е/о in "Еighth day of Nativity" and "Tatоul";
#   * a typographic curly apostrophe U+2019 in two possessives ("St. Mary’s Box",
#     "…Illuminator’s Commitment…") where every other name uses the ASCII apostrophe.
# Only folds justified by characters actually seen in the data are listed (deliberately
# conservative); anything unlisted is left alone and caught by ``unexpected_chars`` below.
_CONFUSABLE_FOLDS = {
    "Е": "E",   # U+0415 CYRILLIC CAPITAL LETTER IE -> LATIN E
    "о": "o",   # U+043E CYRILLIC SMALL LETTER O     -> LATIN o
    "’": "'",   # U+2019 RIGHT SINGLE QUOTATION MARK -> ASCII APOSTROPHE
}


def normalize_confusables(text):
    """Fold the wrong-code-point characters the source mixes into English feast names to
    the canonical ASCII twin used elsewhere. Idempotent; leaves everything else untouched.

    This is the *fixer*: a narrow, observed-only fold. It is intentionally NOT a general
    "downgrade any confusable" pass -- we never want to silently rewrite a genuinely
    non-Latin character. The general *detector* that catches anything the fixer misses is
    ``unexpected_chars`` below, asserted at the build steps and in the shipped-artifact
    tests, so a NEW contaminant fails loudly (and gets added here) instead of shipping."""
    if not text:
        return text
    for src, dst in _CONFUSABLE_FOLDS.items():
        text = text.replace(src, dst)
    return text


# Plain-spelling typos in the *English* feast text (distinct from the character-level
# confusables above -- these are ordinary misspellings of saint/feast names). Each is
# uniformly the source's modal spelling, contradicted by the form the church actually uses
# (and, where the saint recurs, by the engine's own id/Armenian rendering). Folded so the
# name reads correctly. Applied to every reference_data reader (apply_source_corrections),
# so the shipped table, the hy name map, and the saint schedule all rebuild with the
# corrected names, and inside canonical_commem so the feast-name test compares like-for-like.
# The shipped artifacts carry the corrected spelling directly.
_FEAST_SPELLING_FIXES = {
    "Staint": "Saint",                     # Staint Gregory ... -> Saint
    "Theordore": "Theodore",               # Theordore Stratelates
    "Transifiguration": "Transfiguration",
    "Grogoris": "Grigoris",                # grandson of St. Gregory the Illuminator
    "Marcarius": "Macarius",               # id: ..._makarios_...
    "Hermongenes": "Hermogenes",
    "Alerius": "Valerius",                 # id: ..._valerian; hy: Վաղերիոսի
    "Canditus": "Candidus",
    "Eugraphius": "Eugraphus",             # Menas, Hermogenes and Eugraphus
    "Begining": "Beginning",               # "Begining of the Fast"; hy Սկիզբն պահոց
    "Antiosh": "Antioch",                  # Ignatius, bishop of Antioch
    "Fiest of": "Feast of",                # "Fiest of the Conception ..." (26x)
}


# --------------------------------------------------------------------------- #
# Source TEXT repairs, beyond single misspelled words
#
# Found by ``dev/audit_source_anomalies.py``, which reads the source rather than the
# engine. It matters now in a way it did not before: the engine reproduces the source's
# feast string on 9496/9496 days, so from here on every error the source makes is an error
# the engine serves. Each entry below is the source contradicting ITSELF -- its own
# Armenian name for the same feast, its own wording for the same saint elsewhere, or plain
# arithmetic -- never an editorial preference. Where the right form could not be
# established that way it is left alone and listed in the script's output instead.
#
# Grouped by what makes each one certain:
#
#   * FACTUAL, contradicted by the source's own Armenian. The hy name is an independent
#     rendering of the same day by the same publisher, which makes it an oracle:
#       - the Council of Ephesus is dated "(AD 341)" in English and "(431 թ.)" in Armenian.
#         431 is the historical council; 341 is a digit transposition.
#       - Pentecost reads "(Fifteenth day of Eastertide)" in English and
#         "յիսներորդ օր" (fiftieth) in Armenian. Fiftieth is also what the day IS -- it is
#         Easter+49, and the source's own Eastertide count reaches "Forty Ninth" the day
#         before. "Pentecost" means fiftieth.
#
#   * GRAMMATICAL, where the Armenian settles the intended sense:
#       - "the poor mans John and Alexis" -> "poor men"; hy "կամաւոր աղքատացն" is plural.
#       - "many faithfuls" -> "faithful"; hy "ժողովրդոցն" (the people).
#       - "Gregory of Theologian" -> "Gregory the Theologian"; hy "Գրիգորի Աստուածաբանին".
#       - "Saint Patriarchs" / "Saint Virgins" -> "Saints ..."; both hy forms are plural
#         (Սրբոց հայրապետացն / Սրբոց կուսանացն), and the source itself writes "Saints
#         Virgins Nune and Mane" on other days.
#       - "Clement the Bishop Rome" -> "Bishop of Rome"; a dropped preposition.
#
#   * MECHANICAL slips:
#       - "Saints Saints Jacoc" -- the word typed twice.
#       - "Saints St. Aret" -- two titles stacked on one name.
#       - "Discovery of the Holy Cross." -- a trailing period no other component has.
#       - "Fast day, Remembrance of the Ten Virgins" -- the day's fast marker comma-joined
#         into the commemoration. The source's own Armenian for that day separates them
#         with FEAST_SEP, as does its English on all 2139 other fast days.
#
#   * ONE SAINT, TWO SPELLINGS -- the source disagreeing with itself about a name:
#       - the Apostle is "Philip" in one component and "Phillip" in another;
#       - St. Nicholas of Myra is "Nicolas" in one and "Nicholas" in two others (hy
#         Նիկողայոս throughout);
#       - the Catholicos of Aghvank is "Gregoris" here and "Grigoris" elsewhere
#         (hy Գրիգորիսի) -- the same fold the "Grogoris" entry above already makes.
#     Each is folded to the form the source uses more often, which is also the standard
#     English one.
#
# NOT fixed, because no evidence establishes the intended form -- see the audit script's
# output: "Jacoc" (hy Յակովկայ), "Theodoron" (hy Աստուածատրոյ), "coming out of Pit",
# "Twelve Holy Doctors of Church", and the source's lowercase "Saints martyrs" /
# "Saints virgins". Those are left exactly as the source states them.
# --------------------------------------------------------------------------- #
_FEAST_TEXT_FIXES = {
    # factual
    "Council of Ephesus (AD 341)": "Council of Ephesus (AD 431)",
    "PENTECOST (Fifteenth day of Eastertide)": "PENTECOST (Fiftieth day of Eastertide)",
    # grammatical
    "the poor mans ": "the poor men ",
    "many faithfuls": "many faithful",
    "Gregory of Theologian": "Gregory the Theologian",
    "Saint Patriarchs ": "Saints Patriarchs ",
    "Saint Virgins ": "Saints Virgins ",
    "Clement the Bishop Rome": "Clement the Bishop of Rome",
    # mechanical
    "Saints Saints ": "Saints ",
    "Saints St. Aret": "Saints Aret",
    "Discovery of the Holy Cross.": "Discovery of the Holy Cross",
    "Fast day, Remembrance of the Ten Virgins":
        "Fast day — Remembrance of the Ten Virgins",
    # one saint, two spellings
    "Phillip": "Philip",
    "Nicolas ": "Nicholas ",
    "Gregoris ": "Grigoris ",
}


def normalize_feast_spelling(text):
    """Fold the source's known English feast-text errors to the corrected form.

    Two registers, applied in order: single misspelled words (``_FEAST_SPELLING_FIXES``)
    then multi-word repairs (``_FEAST_TEXT_FIXES``). Every replacement is idempotent, so
    applying this twice is the same as applying it once.
    """
    if not text:
        return text
    for wrong, right in _FEAST_SPELLING_FIXES.items():
        text = text.replace(wrong, right)
    for wrong, right in _FEAST_TEXT_FIXES.items():
        text = text.replace(wrong, right)
    return text


# --------------------------------------------------------------------------- #
# Calendar-POSITION label normalization
#
# The engine regenerates the source's position label per date (engine._position_label),
# verified against every occurrence in the cache by dev/verify_position_labels.py. Seven
# occurrences are the source contradicting ITSELF rather than a rule the engine is missing,
# so they are folded here -- the same treatment BOOK_NAME_FIXES gives the "Malach" typo:
#
#   * a stray trailing period on "the Fast of Nativity." (4 x Jan 1; every other day in the
#     same window has no period);
#   * a comma where the source's own 25 other occurrences of each phrase use a period
#     ("Great Lent, Sunday of the Expulsion" / "... the Advent");
#   * one wrong ordinal word: 2008-04-07 reads "Thirteenth day of Eastertide" where the
#     count is 16. Its neighbours pin it -- Apr 5 is "Fourteenth" (offset 13) and Apr 8 is
#     "Seventeenth" (offset 16) -- so 13 is a typo for 16, not a different counting rule.
#
# An eighth, "Feast day" -> "Fast day" on Dec 9, is deliberately NOT here: these folds are
# substring replaces over the whole feast string, and a bare "Feast day" would also rewrite
# "Feast day of the Discovery of the Belt of the Holy Mother of God" (a different feast, 26
# other days) into a nonsense "Fast day of the Discovery ...". It is registered as a
# component-exact ground-truth row instead -- see apply_ground_truth and
# docs/feast-name-corrections.md section 1.
# --------------------------------------------------------------------------- #
POSITION_LABEL_FIXES = {
    "day of the Fast of Nativity.": "day of the Fast of Nativity",
    "Great Lent, Sunday of the Expulsion": "Great Lent. Sunday of the Expulsion",
    "Great Lent, Sunday of the Advent": "Great Lent. Sunday of the Advent",
}

# The wrong-ordinal fix must be DATE-SCOPED: "Thirteenth day of Eastertide" is the correct
# label on every other year's Easter+12, so folding it globally would corrupt 25 good days
# to fix one bad one.
POSITION_LABEL_FIXES_BY_DATE = {
    "2008-04-07": {"Thirteenth day of Eastertide": "Sixteenth day of Eastertide"},
}

# --------------------------------------------------------------------------- #
# Fast of St. Gregory the Illuminator: the source is more specific in Armenian than in
# English, on the same day.
#
# It heads the fast's five weekdays (Pentecost+22..+26) "Ա/Բ/Գ/Դ/Ե օր Լուսաւորչի պահոց" --
# First..Fifth day of the Fast of the Illuminator -- while its English says only "Fast
# day", the same two words it prints on 2,139 ordinary Wed/Fri fast days. One English
# string, six different observances. The source contradicting its own other-language
# statement of the same fact is the standing justification for a repair here (Ephesus
# "AD 341" vs "431", Pentecost "Fifteenth day of Eastertide" vs fiftieth); this is that,
# applied to a position label rather than to a commemoration.
#
# This is not only a nicety. While the English was ambiguous, no consumer could tell the
# six apart by text, and the engine carried a date-scoped side channel to recover the
# distinction for its own Armenian resolution. Saying in English what the source already
# says in Armenian retires that channel.
#
# Date-scoped, for the reason the Eastertide fix above is: "Fast day" is the correct and
# complete label on every other fast day in the corpus.
# --------------------------------------------------------------------------- #
_ILLUMINATOR_FAST_WINDOW = (22, 26)      # Pentecost+21 is the Sunday eve; Mon-Fri follow
_ILLUMINATOR_FAST_ORDINALS = ("First", "Second", "Third", "Fourth", "Fifth")
_ILLUMINATOR_FAST_TEMPLATE = "{ord} day of the Fast of St. Gregory the Illuminator"
_AMBIGUOUS_FAST_LABEL = "Fast day"


def illuminator_fast_label(date_iso):
    """The specific label for a weekday of the Fast of St. Gregory the Illuminator.

    ``None`` on every other date, including the fast's own Sunday eve (which the source
    names in full already) and the Saturday that closes it.
    """
    if not date_iso:
        return None
    from armenian_lectionary.engine import calculate_gregorian_easter

    d = datetime.date.fromisoformat(date_iso)
    pentecost = calculate_gregorian_easter(d.year) + datetime.timedelta(days=49)
    lo, hi = _ILLUMINATOR_FAST_WINDOW
    offset = (d - pentecost).days
    if not lo <= offset <= hi:
        return None
    return _ILLUMINATOR_FAST_TEMPLATE.format(
        ord=_ILLUMINATOR_FAST_ORDINALS[offset - lo])


def normalize_position_label(text, date_iso=""):
    """Fold the source's self-contradicting position labels to the form it uses elsewhere.

    Idempotent. Date-scoped fixes apply only on their own date.
    """
    if not text:
        return text
    for wrong, right in POSITION_LABEL_FIXES.items():
        text = text.replace(wrong, right)
    for wrong, right in POSITION_LABEL_FIXES_BY_DATE.get(date_iso, {}).items():
        text = text.replace(wrong, right)
    specific = illuminator_fast_label(date_iso)
    if specific:
        # Component-exact, not a substring replace: the bare label is what is ambiguous,
        # and rewriting it inside a longer component would corrupt a name that merely
        # contains the words.
        text = _FEAST_SEP.join(
            specific if part.strip() == _AMBIGUOUS_FAST_LABEL else part
            for part in text.split(_FEAST_SEP))
    return text


# --------------------------------------------------------------------------- #
# Character-set guard (the detector backing ``normalize_confusables``)
#
# Feast/book text legitimately draws from exactly these code points:
#   * ASCII        -- English words, Latin digits, and the punctuation both languages use
#                     (the Armenian feast names carry Latin digits/parens, e.g. "(381 թ.)");
#   * the Armenian block U+0530-U+058F -- letters AND Armenian punctuation;
#   * the Armenian ligatures U+FB13-U+FB17 (եւ etc.);
#   * the em-dash U+2014 -- the FEAST_SEP joining a feast's <br>-delimited components.
# Anything else (Cyrillic/Greek homoglyphs, curly quotes, zero-width joiners, ...) is a
# contaminant. Positively validating against this allow-list is more robust than chasing a
# growing blacklist of specific confusables.
# --------------------------------------------------------------------------- #
def _is_expected_char(c):
    o = ord(c)
    return (c.isascii()
            or 0x0530 <= o <= 0x058F        # Armenian block (letters + punctuation)
            or 0xFB13 <= o <= 0xFB17        # Armenian ligatures (եւ etc.)
            or c == "—")               # em-dash FEAST_SEP


def unexpected_chars(text):
    """Sorted, de-duplicated list of characters in ``text`` outside the expected
    English+Armenian character set (empty list == clean). See ``_is_expected_char``."""
    return sorted({c for c in (text or "") if not _is_expected_char(c)})


# --------------------------------------------------------------------------- #
# Book-NAME spelling normalization
#
# The source truncates one book name on the Presentation-eve (Feb 13) block: "Malach
# 3.1-4" is Malachi 3:1-4 (Մաղաքիա / Malachi) -- the same book the source (and this
# engine) spell "Malachi" on every other day it appears. It is a plain typo, not a
# distinct book, so fold the lone outlier spelling to the canonical name. Applied to
# every reference_data reader (via apply_source_corrections) so the shipped table
# (dev/build_table) and hy name map (dev/fetch_translations) rebuild with "Malachi" and
# the oracle scores the engine's "Malachi" as a hit. The runtime artifacts that carry
# this reading directly -- engine._PRESENTATION_EVE_BLOCK and the shipped
# lectionary_data.json -- already spell it "Malachi".
# --------------------------------------------------------------------------- #
BOOK_NAME_FIXES = {
    "Malach": "Malachi",
}


def apply_book_name_fixes(readings):
    """Fold source book-name typos (BOOK_NAME_FIXES) to their canonical spelling in a
    list of reading strings. Matches on the book head only, so an already-correct
    "Malachi ..." is left untouched; idempotent."""
    fixed = []
    for r in readings:
        for wrong, right in BOOK_NAME_FIXES.items():
            if r == wrong or r.startswith(wrong + " "):
                r = right + r[len(wrong):]
                break
        fixed.append(r)
    return fixed


# --------------------------------------------------------------------------- #
# Ground-truth component names, reviewed via dev/feast_name_review.tsv
#
# ``dev/feast_name_ground_truth.json`` is the frozen approved-name mapping (built by
# ``dev/build_ground_truth.py``): raw feast-name component -> the English text a human
# has signed off on. Unlike ``_FEAST_TEXT_FIXES``/``_FEAST_SPELLING_FIXES`` above (a small,
# individually-commented set, each justified by the source contradicting itself), this
# covers every component in the 2001-2026 corpus and folds in a style decision too
# ("Saint"/"Saints" -> "St."/"Sts."), so it is generated rather than hand-curated.
#
# Applied FIRST, before the older folds: each entry replaces the ENTIRE raw component in
# one shot (it is already the fully-corrected text), so the confusable/spelling/position
# folds that follow are a no-op on whatever it touched and only still act on components
# the ground truth left alone.
#
# NOT everything in the ground truth is reachable this way. Two families of component
# --  calendar-position labels and "Eve of ..." notes -- are excluded from the shipped
# TABLE (``dev/build_table.unanimous_feast`` drops any calendar-derived text the years
# sharing a key do not state identically) and regenerated live instead, from hardcoded
# templates in ``engine._POSITION_FAMILIES``/``engine._EVE_FAMILIES``. A ground-truth entry
# for one of those has no effect on what is actually served unless the matching engine.py
# template is edited too (see the two "St. Gregory"/"St. James" eve labels there for the
# pattern) -- and some, like the Advent eve's deliberate dual form, are correct exactly as
# the engine already reproduces them and must NOT be folded to one spelling. Rows where
# this applies are marked in the TSV's ``note`` rather than silently included here; see
# ``docs/feast-name-corrections.md``.
# --------------------------------------------------------------------------- #
_GROUND_TRUTH_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "feast_name_ground_truth.json")


@functools.lru_cache(maxsize=1)
def _ground_truth_fixes():
    """[(source, approved), ...], LONGEST source first.

    Composite (glued-day) components contain their own sub-component rows as literal
    substrings -- e.g. "Saints Cyricus..., and Saints Gordius..." contains "Saints
    Cyricus..." verbatim. Iterating shortest-first lets the sub-component's fix fire first
    and consume that substring, so the composite's OWN entry (which would have fixed the
    remaining half too) no longer matches. Longest-first guarantees a composite gets first
    claim on its full text before any of its parts can.

    Each entry is registered under BOTH the pristine raw source AND, where it differs, the
    older confusables/spelling chain's output for that source. ``saint_schedule.json`` is a
    checked-in artifact, not rebuilt from the raw cache (its own generator is not
    reproducible -- see CLAUDE.md); some of its labels were already run through the OLD
    fixes when it was last built (e.g. "Gregory of Theologian" -> "Gregory the Theologian"
    is already baked in), so the text this fold actually sees there is that older-corrected
    form, not the raw one. Keying on both means the fold fires either way.
    """
    with open(_GROUND_TRUTH_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    fixes = {}
    for src, v in data.items():
        approved = v["approved_en"]
        if not approved or approved == src:
            continue
        fixes[src] = approved
        old = normalize_feast_spelling(normalize_confusables(src))
        if old != src:
            fixes[old] = approved
    ordered = sorted(fixes.items(), key=lambda pair: len(pair[0]), reverse=True)
    return ordered


@functools.lru_cache(maxsize=1)
def _ground_truth_reviewed():
    """Every reviewed component, INCLUDING the rows whose approved text equals the source.

    ``_ground_truth_fixes`` drops those no-op rows -- there is nothing to replace. But they
    still carry information: they say "a human looked at this exact component and it is
    already right", which is exactly what a shorter fix firing inside them would violate.
    See ``apply_ground_truth``.
    """
    with open(_GROUND_TRUTH_PATH, encoding="utf-8") as fh:
        return {src: v["approved_en"]
                for src, v in json.load(fh).items() if v["approved_en"]}


def apply_ground_truth(text):
    """Fold every reviewed component in ``text`` to its approved English spelling.

    Component-exact first, substring chain second. The ground truth is keyed by COMPONENT
    (see dev/build_ground_truth.py's docstring on why), so when a component matches a
    reviewed row outright, that row is the answer and no other fix may touch it.

    Without that short-circuit a short fix fires inside a longer reviewed component that
    merely starts the same way. ``_ground_truth_fixes``'s longest-first ordering only
    protects the case where BOTH are changing rows; it cannot protect a no-op row, because
    no-op rows are not in the list at all. Registering ``Feast day`` -> ``Fast day``
    (the Dec 9 marker) turned that latent hole into a live one: it rewrote
    ``Feast day of the Discovery of the Belt of the Holy Mother of God`` -- a different,
    correctly-spelled feast on 26 other days -- into ``Fast day of the Discovery ...``.

    The substring pass still runs on components with no exact row, because a composite the
    source glued from two commemorations may have no row of its own while each half does.
    """
    if not text:
        return text
    reviewed = _ground_truth_reviewed()
    folded = []
    for component in text.split(_FEAST_SEP):
        if component in reviewed:
            folded.append(reviewed[component])
            continue
        for wrong, right in _ground_truth_fixes():
            component = component.replace(wrong, right)
        folded.append(component)
    return _FEAST_SEP.join(folded)


def apply_source_corrections(day):
    """Apply the on-read source corrections to a cached reference-day dict, in place.

    Single home for the corrections every reference_data reader must apply identically:
    the Easter-Sunday reading-order fix, the Malachi book-name typo fold, the reviewed
    ground-truth names, and the Cyrillic-homoglyph fold on the English feast text. Returns
    ``day`` for convenience. (Caches are git-ignored/local and may predate these fixes, so
    they are applied on read, not assumed baked into the cache.)"""
    day["readings"] = apply_reading_order(day.get("date", ""), day.get("readings", []))
    day["readings"] = apply_book_name_fixes(day.get("readings", []))
    day["feast"] = normalize_position_label(
        normalize_feast_spelling(normalize_confusables(
            apply_ground_truth(day.get("feast", "")))),
        day.get("date", ""))
    return day


def canonical_commem(commem):
    """Collapse reviewed companion-enumeration variants to a primary commemoration.

    Applied symmetrically to the scraped and engine commemorations before comparison.
    Also repairs the "Fiest" -> "Feast" scrape typo, the Cyrillic-homoglyph
    contamination (Cyrillic Е/о) in the source's English feast text, and folds in the
    reviewed ground truth -- so the source's raw spelling and the engine's approved one
    canonicalize to the same string and register as a reviewed difference, not a
    contradiction."""
    commem = normalize_feast_spelling(normalize_confusables(apply_ground_truth(commem)))
    commem = commem.replace("Fiest of", "Feast of")     # sacredtradition.am typo
    for canonical, pred in _FEAST_CANON_RULES:
        if pred(commem):
            return canonical
    return commem
