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


# The scrape mixes a few Cyrillic homoglyphs into the *English* feast text (the source
# was evidently typed with a Cyrillic keyboard): Cyrillic Е/о in "Еighth day of Nativity"
# and "Tatоul". They read identically but are the wrong code points, so map them back to
# their Latin twins. Only homoglyphs observed in the data are listed (deliberately
# conservative -- we never want to fold a genuinely non-Latin character).
_CYRILLIC_HOMOGLYPHS = {
    "Е": "E",   # CYRILLIC CAPITAL LETTER IE -> LATIN E
    "о": "o",   # CYRILLIC SMALL LETTER O    -> LATIN o
}


def normalize_confusables(text):
    """Replace the Cyrillic homoglyphs the source mixes into English feast names with
    their Latin equivalents. Idempotent; leaves everything else untouched."""
    if not text:
        return text
    for cyr, lat in _CYRILLIC_HOMOGLYPHS.items():
        text = text.replace(cyr, lat)
    return text


def canonical_commem(commem):
    """Collapse reviewed companion-enumeration variants to a primary commemoration.

    Applied symmetrically to the scraped and engine commemorations before comparison.
    Also repairs the "Fiest" -> "Feast" scrape typo and the Cyrillic-homoglyph
    contamination (Cyrillic Е/о) in the source's English feast text."""
    commem = normalize_confusables(commem)
    commem = commem.replace("Fiest of", "Feast of")     # sacredtradition.am typo
    for canonical, pred in _FEAST_CANON_RULES:
        if pred(commem):
            return canonical
    return commem
