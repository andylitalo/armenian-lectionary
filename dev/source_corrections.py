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
    ("Saints Cyricus and His Mother Julitta",
     lambda c: c.startswith("Saints Cyricus and His Mother Julitta")),
    ("Holy Fathers Saints Athanasius and Cyril of Alexandria",
     lambda c: c.startswith("Holy Fathers Saints Athanasius and Cyril of Alexandria")),
    ("Saint Vahan of Goghtn",
     lambda c: "Vahan of Goghtn" in c),
    ("The Hermit Saints Anton",
     lambda c: "Anton" in c and "Hermit" in c),
    ("Saints Eugenios, Makarios, Valerian, Candidus and Aquila",
     lambda c: c.startswith(("Saints Eugenios", "Saints Eugenius"))),
    ("Saint Sargis the Warrior and his son Martiros and his Fourteen Soldiers",
     lambda c: c.startswith("Saint Sargis the Warrior")),
    ("Saints Atom and his soldiers",
     lambda c: c.startswith("Saints Atom and his soldiers")),
    ("PRESENTATION OF OUR LORD TO THE TEMPLE",
     lambda c: "PRESENTATION OF OUR LORD TO THE TEMPLE" in c),
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
}


def normalize_feast_spelling(text):
    """Fold known English feast/saint-name misspellings (``_FEAST_SPELLING_FIXES``) to their
    canonical form. Idempotent; leaves everything else untouched."""
    if not text:
        return text
    for wrong, right in _FEAST_SPELLING_FIXES.items():
        text = text.replace(wrong, right)
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


def apply_source_corrections(day):
    """Apply the on-read source corrections to a cached reference-day dict, in place.

    Single home for the corrections every reference_data reader must apply identically:
    the Easter-Sunday reading-order fix, the Malachi book-name typo fold, and the
    Cyrillic-homoglyph fold on the English feast text. Returns ``day`` for convenience.
    (Caches are git-ignored/local and may predate these fixes, so they are applied on
    read, not assumed baked into the cache.)"""
    day["readings"] = apply_reading_order(day.get("date", ""), day.get("readings", []))
    day["readings"] = apply_book_name_fixes(day.get("readings", []))
    day["feast"] = normalize_feast_spelling(normalize_confusables(day.get("feast", "")))
    return day


def canonical_commem(commem):
    """Collapse reviewed companion-enumeration variants to a primary commemoration.

    Applied symmetrically to the scraped and engine commemorations before comparison.
    Also repairs the "Fiest" -> "Feast" scrape typo and the Cyrillic-homoglyph
    contamination (Cyrillic Е/о) in the source's English feast text."""
    commem = normalize_feast_spelling(normalize_confusables(commem))
    commem = commem.replace("Fiest of", "Feast of")     # sacredtradition.am typo
    for canonical, pred in _FEAST_CANON_RULES:
        if pred(commem):
            return canonical
    return commem
