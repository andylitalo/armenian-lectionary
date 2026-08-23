"""DEV-ONLY: resolve already-approved display text into observance_catalog.json ids.

Shared by every Phase-2 rewiring step (dev/build_table.py, dev/refresh_artifact_names.py)
so a component-to-id lookup is defined exactly once. Text handed to ``ids_for_text`` is
assumed ALREADY corrected/approved (the output of ``apply_source_corrections`` or
equivalent) -- this module only resolves identity, it does not fix spelling.
"""

import functools
import json
import os

from armenian_lectionary.engine import _OBSERVANCE_SEP

CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "armenian_lectionary", "data", "observance_catalog.json")


@functools.lru_cache(maxsize=1)
def _catalog():
    with open(CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=1)
def _text_to_id():
    """English component -> id.

    One entry per component: no two observances share an English text, an invariant
    dev/build_observance_catalog.py enforces. That is what lets a storage tier -- which
    has text and no date -- resolve identity on its own.
    """
    return {entry["en"]: sid for sid, entry in _catalog().items()}


def ids_for_text(text):
    """Ordered list of observance ids for a (possibly _OBSERVANCE_SEP-joined) served string.

    Raises KeyError, naming the missing component, rather than silently dropping it --
    an unresolvable component here means observance_catalog.json has drifted out of date
    with what's actually served; that must be caught, not swallowed. Run
    dev/build_observance_catalog.py (and dev/verify_observance_catalog.py) again first.
    """
    by_text = _text_to_id()
    ids = []
    for component in [c.strip() for c in (text or "").split(_OBSERVANCE_SEP) if c.strip()]:
        if component not in by_text:
            raise KeyError(
                f"no observance_catalog.json entry for component {component!r}; "
                "rerun dev/build_observance_catalog.py")
        ids.append(by_text[component])
    return ids


# --------------------------------------------------------------------------- #
# Packed pools
#
# The Tonats'oyts sets these out as SEPARATE canons, each with its own propers: the
# post-Theophany insertions at First Volume pp.460-462 and the pre-Lent cohort at
# pp.464-465. The Second Volume then packs them onto however many days the taregir leaves
# between the fixed Theophany and the movable Fast of the Catechumens, and its preface
# (Sixth, p.556) says it prints "only the name of the first saints in many places for the
# sake of brevity", instructing the reader to celebrate the companions from the First
# Volume anyway.
#
# So a day where the source prints one head canon and the engine serves that canon plus the
# others packed with it is the book's own instruction, not an invention -- but it IS a
# difference from the printed string, so it is declared here and counted rather than
# folded silently. The engine serves one packing per liturgical coordinate; which canons
# the source names varies by year-type, and reconciling that is a readings question.
#
# Membership is by id and enumerated from the First Volume, never inferred from text.
# --------------------------------------------------------------------------- #

_PACKED_POOLS = (
    # First Volume pp.460-462 -- inserted after the Theophany octave.
    frozenset({
        "hermit_st_anton", "hermit_sts_tryphon_barsauma", "theodosius_and_the_children",
        "cyricus_and_his_mother", "vahan_of_goghtn", "fathers_sts_athanasius_and",
        "gregory_the_theologian", "gordius_polyeuctus_and_grigoris",
        "eugenia_the_virgin_her", "eugenius_macarius_valerius_candidus",
        # Andrew's own canon is at p.527, in the Assumption cycle -- but the Second
        # Volume's preface (Seventh, p.556) names him among the feasts that "frequently
        # shift and are celebrated in various and different intervals", and the source
        # does pack him into the January run (2009-01-27). Declared here on that warrant,
        # not on a First Volume page.
        "andrew_the_general_and",
    }),
    # First Volume pp.464-465 -- the pre-Lent martyr cohort.
    frozenset({"sargis", "atom", "mark_the_bishop_pionius", "sukias", "voskian",
               "ghevond"}),
)


def pool_of_text(text):
    """The packed pool the component belongs to, or ``None``.

    Text, not id, because the callers are the discrepancy reports, which compare strings.
    Unknown text is not an error here (the source publishes spellings that reach nothing);
    it simply belongs to no pool.
    """
    sid = _text_to_id().get(text)
    if sid is None:
        return None
    return next((pool for pool in _PACKED_POOLS if sid in pool), None)


# Observances the engine ADDS: served on a fixed civil date that the source's English never
# names on any day. Not a correction -- there is no printed English to correct -- so
# apply_ground_truth has no way to register them and they would otherwise read as a
# contradiction on every occurrence. Declared here instead, and counted by their own ratchet
# (tests/test_observance_name_raw.FEAST_ADDITION_CEILING) so the number stays visible.
#
# The bar is deliberately high: the source must state the day in its OTHER language, so the
# addition is a translation gap rather than an editorial opinion, and docs section 9 must
# say what the served name asserts beyond what the source's text does.
_ADDED_OBSERVANCES = frozenset({"blessing_of_the_pomegranates"})


def is_added_text(text):
    """True if the component is a declared addition (see ``_ADDED_OBSERVANCES``)."""
    return _text_to_id().get(text) in _ADDED_OBSERVANCES


# Source text we deliberately DO NOT serve. The mirror of ``_ADDED_OBSERVANCES``: there the
# engine states what the source omits, here it omits what the source states, and both need
# declaring or the accuracy ratchets stop meaning "unexplained".
#
# Armenian strings rather than ids, because a thing we do not serve has no id to name it by.
#
# "Կաղանդ. տարեմուտ" -- sacredtradition.am prints the civil New Year on Jan 1 in Armenian
# (and nothing in English). The 1915 Tonatsoyts does not: grabar-ocr/corpus has no
# occurrence of Կաղանդ on any of its 189 pages. So it is the scrape's addition, not the
# book's. From 2015 the engine serves the rite actually kept on that day instead
# (blessing_of_the_pomegranates); before it was instituted, the day is its position label
# alone. See docs/observance-name-corrections.md section 9.
# Both spellings: what the source prints, and what our own review row renames it to. The
# reports fold registered Armenian corrections onto the source BEFORE comparing, so by the
# time a component reaches here it may already read "Նռնօրհնէք" -- and that fold is not
# dead weight, it is what keeps 2015 onward exact, since sacredtradition.am goes on printing
# the civil New Year there and knows nothing of the rite.
_DECLINED_SOURCE_HY = frozenset({"Կաղանդ. տարեմուտ", "Նռնօրհնէք"})


def is_declined_hy(text):
    """True if the Armenian component is one the engine deliberately does not serve."""
    return text in _DECLINED_SOURCE_HY or text in _DECLINED_FAST_MARKERS_HY


# The undifferentiated fast marker, in both languages. Declared here for the same reason as
# the civil New Year above: the engine omits what the source states, and an omission that is
# a decision has to be distinguishable from one that is a bug.
#
# Unlike that entry this is not a question of what the Tonats'oyts carries -- the source is
# right that these are fast days. It is a question of what belongs in a NAME. The marker is
# an attribute of the day, and on every day that has any other name it only restates what
# the rest already establishes: "Great Thursday" is Holy Week, "Third day of the Fast of
# Prophet Elijah" is a day of a fast. Nothing is lost by dropping it, because whether a day
# is a fast is a function of the date and the engine computes the date -- it was never a
# fact only sacredtradition.am knew. Where the day IS the weekly fast and nothing else, the
# section 6c split names it specifically instead.
#
# 437 days in English, and their Armenian counterparts. See docs section 6e.
_DECLINED_FAST_MARKERS_EN = frozenset({"Fast day", "Feast day"})
_DECLINED_FAST_MARKERS_HY = frozenset({"Պահք"})


def is_declined_en(text):
    """True if the English component is one the engine deliberately does not serve."""
    return text in _DECLINED_FAST_MARKERS_EN


# --------------------------------------------------------------------------- #
# Observances that legitimately recur within one liturgical year
#
# The Tonats'oyts lays each saint's canon down ONCE per annual cycle, so an id served on
# two days of the same liturgical year is a duplicate commemoration -- see
# dev/audit_duplicate_commemorations.py, which is the check that statement exists to feed.
# The ids below are the exceptions, and each is an exception for a stated reason rather
# than because flagging it was inconvenient. Anything not listed here that recurs is a
# finding.
#
# Two shapes. The first five recur BY DESIGN: they are not saint canons at all, but
# positions and feasts the calendar returns to. The last two are artifacts of where the
# year is cut -- Heesnak (the Sunday closest to Nov 18) drifts by up to a week, so an
# observance anchored to a DIFFERENT feast can fall on either side of the boundary and
# land twice in one window. Both are ~a full year apart (329d and 364d), both are named by
# the source on both days, and neither is the engine serving anything twice.
# --------------------------------------------------------------------------- #
_RECURRING_OBSERVANCES = {
    "wednesday_fast": "the weekly fast, served on every unclaimed Wednesday (docs 6c)",
    "friday_fast": "the weekly fast, served on every unclaimed Friday (docs 6c)",
    "remembrance_of_the_dead":
        "kept the day after each of the five tabernacle feasts -- Nativity, Easter, "
        "Transfiguration, Assumption, Exaltation",
    "feast_of_the_holy":
        "Feast of the Holy Church, kept on three days of the Exaltation octave",
    "feast_of_the_holy_2":
        "Feast of the Holy Cross, kept on three days of the Exaltation octave",
    "second_sunday_after_pentecost":
        "the source prints no FIRST Sunday after Pentecost -- Pentecost itself is the "
        "first -- so Pentecost+7 and Pentecost+14 both carry this ordinal, in the source "
        "as well as here. Verified on every cached year; see _position_label's docstring "
        "on the counting rule not being exact on every occurrence",
    "tenth_sunday_after_the":
        "boundary artifact: the last Sunday before Advent, counted from the Holy Cross "
        "(September) while the year is cut at Heesnak (November). When Heesnak falls late "
        "the pre-Advent Sunday lands inside the previous window too. 364 days apart, and "
        "the source prints it on both",
    "abraham_and_khoren_moneyless_2":
        "boundary artifact, same shape: this canon's slot moved from late December to "
        "mid-November between two consecutive laydowns, and the Heesnak cut moved later "
        "still. 329 days apart, and the source prints it on both",
}


def recurs_by_design(sid):
    """True if ``sid`` may legitimately appear twice in one liturgical year."""
    return sid in _RECURRING_OBSERVANCES

