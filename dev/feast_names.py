"""DEV-ONLY feast-name normalization for the commemoration test.

The engine serves a *feast/fast name of the day* as the ``"Liturgical Day"`` field
(the same value bahk scrapes from sacredtradition.am's ``<div class=dname>`` and feeds
to its AI-context generation). The sacredtradition.am scrape (and therefore bahk's
value, and our ``dev/reference_data/*.json`` ``feast`` field) mashes several ``<br>``-
separated components into ONE string with no separators, e.g.

    "Fifth Sunday after the AssumptionEve of Fast of Exaltation of Holy Cross"

The leading component is a YEAR-VARYING calendar-position label ("Nth day of <Season>",
"Nth Sunday after/of <Anchor>", "Fast day"), and a trailing "Eve of <Fast>..." note is a
status marker. The same liturgical-coordinate key serves many civil years whose ordinal
labels differ, so a static engine cannot byte-reproduce the mashed string. We therefore
compare only the **commemoration component** -- the saint/feast identity -- which IS
reproducible. ``commemoration_of`` strips the position/eve/status noise; ``commem_key``
casefolds it for comparison.

Not shipped (dev tooling); imported by tests/test_feast.py and dev/feast_audit.py.
"""

import re

# Ordinal words that head a "Nth day of <Season>" / "Nth Sunday after/of <Anchor>" label.
ORD = (r"(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|"
       r"Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|"
       r"Eighteenth|Nineteenth|Twentieth|Twenty [A-Z][a-z]+|Thirtieth|Thirty [A-Z][a-z]+|"
       r"Fortieth|Forty [A-Z][a-z]+|Fiftieth)")

# Season names following "Nth day of ...". Longest-first so specific ones win.
_SEASONS = sorted([
    "Great Lent", "Eastertide", "Advent", "Pentecost", "Transfiguration",
    "Assumption", "Nativity", "Easter",
    "the Fast of the Catechumens", "the Fast of Catechumens",
    "the Fast of the Holy Cross", "the Fast of the Transfiguration",
    "the Fast of the Transifiguration",           # sacredtradition.am spelling variant
    "the Fast of Assumption", "the Fast of Nativity", "the Fast of Advent",
    "the Assumption",
], key=len, reverse=True)

# Anchor names following "Nth Sunday after/of ...". Longest-first.
_ANCHORS = sorted([
    "Holy Cross of Varag", "the Exaltation of the Holy Cross", "the Holy Cross",
    "Holy Cross", "Holy Etchmiadzin", "Holy Nativity", "the Assumption",
    "the Great Barekendan", "Great Barekendan", "Advent", "Pentecost", "Great Lent",
    "Nativity", "Transfiguration", "Assumption", "Eastertide", "Exaltation", "Holy",
], key=len, reverse=True)

# Trailing status notes ("Eve of the Fast of ...", "Eve of the Resurrection ...").
_EVES = sorted([
    "Eve of Fast of Prophet Elijah", "Eve of Fast of Saint Gregory the Illuminator",
    "Eve of Fast of Saint James the bishop of Nisibis",
    "Eve of the Nativity and Theophany of our Lord Jesus Christ",
    "Eve of Fast of Assumption of the Holy Mother of God",
    "Eve of Fast of Transfiguration", "Eve of Fast of Exaltation of Holy Cross",
    "Eve of Fast of Nativity", "Eve of Fast of Catechumens",
    "Eve of Fast of the Holy Cross of Varag",
    "Eve of the Resurrection of our Lord Jesus Christ", "Eve of Great Lent",
    "Eve of the Fast of Advent", "Eve of Fast of Advent",
    # Vigil designations (temporal markers, not a commemoration): the eve of the
    # Presentation is a co-celebrated reading block, so the day is headlined by its own
    # commemoration, not "Eve of the Presentation".
    "Eve of the Presentation of the Lord to the Temple",
    "Eve of the Presentation of the Lord",
], key=len, reverse=True)

# Engine placeholders that are NOT a commemoration name -> normalize to empty.
_PLACEHOLDERS = ["(movable ordinary-time reading)", "(commemoration)",
                 "(day not yet in validated table)"]

_PAREN_POS = re.compile(rf"\({ORD} day of [A-Za-z' ]+\)")   # e.g. "(Fifteenth day of Eastertide)"
_DAYOF = re.compile(rf"^{ORD} day of ")
_SUNAO = re.compile(rf"^{ORD} Sunday (after|of) ")
_SUN = re.compile(rf"^{ORD} Sunday")


def _strip_leading_position(s):
    """Strip one leading "Nth day of <Season>" / "Nth Sunday after/of <Anchor>" /
    standalone "Nth Sunday" (Lenten) prefix. Unrecognized season/anchor -> sentinel."""
    m = _DAYOF.match(s)
    if m:
        rest = s[m.end():]
        for sea in _SEASONS:
            if rest.startswith(sea):
                return rest[len(sea):]
        return "\x00" + rest                        # unrecognized: surfaced by the audit
    m = _SUNAO.match(s)
    if m:
        rest = s[m.end():]
        for a in _ANCHORS:
            if rest.startswith(a):
                return rest[len(a):]
        return "\x00" + rest
    m = _SUN.match(s)
    if m:
        return s[m.end():]
    return s


def commemoration_of(feast_str):
    """Return the commemoration component of a (mashed) feast string.

    Strips the year-varying calendar-position prefix, trailing eve/fast status notes,
    engine placeholders, and parenthetical position notes. Returns the saint/feast
    identity (possibly empty for a pure-ordinal day). Casing is preserved; use
    ``commem_key`` for comparison.
    """
    if not feast_str:
        return ""
    # The fetch layer now joins the source's <br>-delimited components with " — " (see
    # fetch_reference.FEAST_SEP); the engine emits the same. Re-mash to the separatorless
    # form this extractor's position/eve stripping expects -- and so a legacy mashed string
    # (no separator) canonicalizes identically. The separator carries no commemoration.
    s = feast_str.replace(" — ", "")
    s = s.replace("Е", "E")                    # Cyrillic 'Е' glitch -> Latin 'E'
    for p in _PLACEHOLDERS:
        s = s.replace(p, "")
    s = _strip_leading_position(s)
    for e in _EVES:
        idx = s.find(e)
        while idx != -1:
            s = s[:idx] + s[idx + len(e):]
            idx = s.find(e)
    s = s.replace("Fast day", "").replace("Feast day", "")   # fast/feast status markers
    s = _PAREN_POS.sub("", s)
    return s.lstrip(". ,").strip()


def commem_key(feast_str):
    """Casefolded commemoration, for equality comparison."""
    return commemoration_of(feast_str).casefold()
