"""DEV-ONLY: resolve already-approved display text into observance_catalog.json ids.

Shared by every Phase-2 rewiring step (dev/build_table.py, dev/refresh_artifact_names.py)
so a component-to-id lookup is defined exactly once. Text handed to ``ids_for_text`` is
assumed ALREADY corrected/approved (the output of ``apply_source_corrections`` or
equivalent) -- this module only resolves identity, it does not fix spelling.
"""

import functools
import json
import os

from armenian_lectionary.engine import _OBSERVANCE_SEP, packed_pool

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


def _generated_id(component, date):
    """The id of ``component`` if it is the position or eve label the engine composes for
    ``date``, else ``None``.

    The text is checked against the rule's own output before its id is accepted, so this
    can only ever identify a component the engine really did generate for this date.

    Why a second route at all: a table entry stores the LITERAL label
    (``source_corrections.named_fast_label`` asks ``engine._position_label`` for the
    calendar-rule text on purpose, not for a catalogued rename), while the catalog holds
    the current ``approved_en``. Those are the same string until someone renames the label,
    and from then on the stored text resolves to nothing by text -- though the runtime
    serves it perfectly well, because it resolves by readings/coordinate. This asks the
    same question the runtime asks.
    """
    from armenian_lectionary.engine import (
        _eve_label, _position_label, generated_observance_id)
    for kind, label in (("position", _position_label(date)), ("eve", _eve_label(date))):
        if label == component:
            return generated_observance_id(date, kind)
    return None


def ids_for_text(text, date=None):
    """Ordered list of observance ids for a (possibly _OBSERVANCE_SEP-joined) served string.

    ``date`` -- any date the text is served on -- lets a generated position/eve component
    resolve by id when it no longer resolves by text; see :func:`_generated_id`. Without
    it, text is the only route, which is correct for callers whose text is a stored
    commemoration rather than a calendar-derived label.

    Raises KeyError, naming the missing component, rather than silently dropping it --
    an unresolvable component here means observance_catalog.json has drifted out of date
    with what's actually served; that must be caught, not swallowed. Run
    dev/build_observance_catalog.py (and dev/verify_observance_catalog.py) again first.
    """
    by_text = _text_to_id()
    ids = []
    for component in [c.strip() for c in (text or "").split(_OBSERVANCE_SEP) if c.strip()]:
        sid = by_text.get(component)
        if sid is None and date is not None:
            sid = _generated_id(component, date)
        if sid is None:
            raise KeyError(
                f"no observance_catalog.json entry for component {component!r}; "
                "rerun dev/build_observance_catalog.py")
        ids.append(sid)
    return ids


def text_for_id(sid):
    """The catalog's current English text for ``sid`` -- the inverse of
    :func:`ids_for_text`.

    An id never moves (CLAUDE.md: "the id is the only thing about it a rename cannot
    move"), so once a caller already knows the id, this is the only lookup that stays
    correct no matter how many times the observance has been renamed since. Matching on
    stored TEXT instead only ever recognizes the text's own original form -- fine the
    first time a component is corrected, silently wrong the second time, because the
    stored text is then neither the source spelling nor necessarily the current one.
    :func:`dev.refresh_artifact_names.refresh` is the caller this matters for.

    Raises KeyError, naming the id, if it is not (or no longer) in the catalog -- e.g. a
    retired id nothing migrated off of.
    """
    catalog = _catalog()
    if sid not in catalog:
        raise KeyError(
            f"no observance_catalog.json entry for id {sid!r}; "
            "rerun dev/build_observance_catalog.py, or check "
            "build_observance_catalog._RETIRED_IDS")
    return catalog[sid]["en"]


# --------------------------------------------------------------------------- #
# Packed pools
#
# One day's printed line can carry several First Volume canons: the Second Volume packs
# them onto however many days the taregir leaves, and its preface (Sixth, p.556) says it
# prints "only the name of the first saints in many places for the sake of brevity",
# instructing the reader to celebrate the companions from the First Volume anyway.
#
# So a day where the source prints one head canon and the engine serves that canon plus
# the others packed with it is the book's own instruction, not an invention -- but it IS a
# difference from the printed string, so it is counted here rather than folded silently.
#
# The pools themselves live in engine._PACKED_POOLS, not here: since the runtime enforces
# the OTHER half of preface Sixth (a companion is packed only where it has no day of its
# own -- engine._drop_owned_companions), the engine needs the membership too, and one
# copy is the only way the two cannot disagree.
# --------------------------------------------------------------------------- #


def pool_of_text(text):
    """The packed pool the component belongs to, or ``None``.

    Text, not id, because the callers are the discrepancy reports, which compare strings.
    Unknown text is not an error here (the source publishes spellings that reach nothing);
    it simply belongs to no pool.
    """
    return packed_pool(_text_to_id().get(text))


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

# A specific position label the rule does not produce, declared for the same reason as the
# markers above -- distinct from them because this is not a generic marker restating what
# another name already establishes; it is the source's OWN plain day count, correctly left
# unrenamed. "Seventh day of Pentecost" (Pentecost+6, a Saturday) sits one day past the Fast
# of the Prophet Elijah, which is Mon-Fri only (the source marks each of those five days
# "Fast day" and carries none on this Saturday, every sampled year) -- so
# engine._POSITION_FAMILIES' PE-fast family stops at offset 5 and this day is served by the
# validated table alone, exactly as the source states it. See
# docs/observance-name-corrections.md section 6b.
_DECLINED_POSITION_LABELS_EN = frozenset({"Seventh day of Pentecost"})


def is_declined_en(text):
    """True if the English component is one the engine deliberately does not serve."""
    return text in _DECLINED_FAST_MARKERS_EN or text in _DECLINED_POSITION_LABELS_EN


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
    "feast_of_the_holy_cross":
        "Feast of the Holy Cross, kept on three days of the Exaltation octave",
    "tenth_sunday_of_the_holy_cross":
        "boundary artifact: the last Sunday before Advent, counted from the Holy Cross "
        "(September) while the year is cut at Heesnak (November). When Heesnak falls late "
        "the pre-Advent Sunday lands inside the previous window too. 364 days apart, and "
        "the source prints it on both",
    "abraham_and_khoren_moneyless_and_theodoron":
        "boundary artifact, same shape: this canon's slot moved from late December to "
        "mid-November between two consecutive laydowns, and the Heesnak cut moved later "
        "still. 329 days apart, and the source prints it on both",
}


def recurs_by_design(sid):
    """True if ``sid`` may legitimately appear twice in one liturgical year."""
    return sid in _RECURRING_OBSERVANCES

