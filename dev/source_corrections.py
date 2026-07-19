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
)


def canonical_commem(commem):
    """Collapse reviewed companion-enumeration variants to a primary commemoration.

    Applied symmetrically to the scraped and engine commemorations before comparison.
    Also repairs the "Fiest" -> "Feast" scrape typo."""
    commem = commem.replace("Fiest of", "Feast of")     # sacredtradition.am typo
    for canonical, pred in _FEAST_CANON_RULES:
        if pred(commem):
            return canonical
    return commem


# Days where the engine's commemoration genuinely differs from the scrape and is NOT a
# reviewed equivalence -- the generative best-guess tier, which the "bugs + wording"
# scope does not resolve. Enumerated (not ratcheted) so any NEW divergence fails the
# test, and a stale entry that stops diverging also fails (keeping the allowlist honest).
# Each is a structural limitation of a best-guess tier, not a wording miss:
#   * Feb-13 (Presentation eve): a year-varying pre-Lent floating martyr (or Lenten
#     Sunday, or nothing) falls here; the generative composite ships the fixed "Eve of
#     the Presentation of the Lord" identity, not the year's floating saint.
#   * Apr-7 (Annunciation): the fixed Annunciation collides with the movable Holy
#     Week/Lent day; the scrape co-lists that day (2018/2019 name both) or transfers the
#     Annunciation away entirely (2023 = Great Friday). The generative composite ships
#     the Annunciation identity regardless.
KNOWN_FEAST_DIVERGENCES = {
    "2001-02-13", "2005-02-13", "2007-02-13", "2008-02-13", "2011-02-13",
    "2016-02-13", "2019-02-13", "2020-02-13", "2022-02-13",
    "2001-04-07", "2004-04-07", "2018-04-07", "2019-04-07", "2023-04-07",
}
