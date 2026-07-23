"""Armenian Church lectionary engine (Տօնացոյց / Ճաշոց).

Self-contained and OFFLINE. Computes the liturgical day and its scripture
readings for any date by:

  1. computing the date's *liturgical coordinates* (Easter-offset, solar-anchor
     offsets, civil date) from the movable/fixed feast framework, and
  2. looking those coordinates up, by precedence, in an embedded data table
     (lectionary_data.json) that was distilled and cross-year-validated from
     13 years of the authoritative Tonatsooyts (see dev/ tooling).

No network access is used at runtime. For the small set of days not yet in the
validated table (chiefly the winter "hinge": Advent -> Theophany -> pre-Lent,
whose ferial saint/fast tracks need a slot engine), the engine returns a
best-effort algorithmic classification flagged as an estimate.

The calendar math (anchors, coordinates, windows, precedence) lives here so the
runtime owns it; the dev table-builder imports these helpers.
"""

import calendar
import datetime
import functools
import json
import os
import re

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "data", "lectionary_data.json")

# Armenian ("hy") name maps, scraped from sacredtradition.am by
# dev/fetch_translations.py. Each degrades to {} if absent; language="hy" then falls
# back to the English name. FEAST maps a whole scraped feast string OR a single
# FEAST_SEP component -> its Armenian form; BOOK maps an English book head -> Armenian.
FEAST_NAMES_HY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "data", "feast_names_hy.json")
BOOK_NAMES_HY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "data", "book_names_hy.json")

SUPPORTED_LANGUAGES = ("en", "hy")


# --------------------------------------------------------------------------- #
# Calendar framework
# --------------------------------------------------------------------------- #

def calculate_gregorian_easter(year: int) -> datetime.date:
    """Easter Sunday via Meeus/Jones/Butcher (Gregorian; Armenian since 1923)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month = (h + L - 7 * m + 114) // 31
    day = ((h + L - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def sunday_closest_to(year: int, month: int, day: int) -> datetime.date:
    """The Sunday closest to a fixed civil target (solar feast rule)."""
    target = datetime.date(year, month, day)
    for i in range(4):
        if (target + datetime.timedelta(days=i)).weekday() == 6:
            return target + datetime.timedelta(days=i)
        if (target - datetime.timedelta(days=i)).weekday() == 6:
            return target - datetime.timedelta(days=i)
    return target


def _pn_len(year: int) -> int:
    """Length (days) of the post-Nativity window Jan 14 -> eve of the Fast of
    Catechumens (Easter-70). This is the *leap-correct* paschal-run-up scalar: it
    moves with the date of Easter but also picks up the Feb-29 shift in the
    Jan 14 -> Easter span, which a raw Easter date misses (cf. the Mar-31 years
    2002/2013 vs 2024). Used to band the pre-Lent / boundary Easter-core days."""
    e = calculate_gregorian_easter(year)
    return ((e - datetime.timedelta(days=70)) - datetime.date(year, 1, 14)).days


# Bin width (days of pn_len) for the Easter-band sub-key. Wider = more support per
# band but coarser; narrower = isolates extreme-Easter outlier years more sharply.
_EB_BIN = 4


def _easter_band(year: int) -> int:
    """Ordinal pn_len band for a civil year (extreme-Easter years fall in their
    own bands, isolating the single-outlier readings the plain Easter-offset key
    cannot separate)."""
    p = _pn_len(year)
    return p // _EB_BIN if p >= 0 else -1   # earliest-Easter (pn_len<0) is its own band


def _adv_len(year: int) -> int:
    """Length (days) of Advent: this year's Heesnak Sunday -> next year's Theophany
    (Jan 6). Heesnak = Sunday closest to Nov 18, so this swings ~46-52 days. Used
    to band the Heesnak-anchored Advent keyspaces: the same Heesnak offset carries
    different readings across Advent-length classes (the Hebrews/Luke continua
    fast-forwards in short Advents), so banding by length separates them. The span
    is Nov->Jan with no Feb-29 inside, so it needs no leap correction."""
    he = sunday_closest_to(year, 11, 18)
    return (datetime.date(year + 1, 1, 6) - he).days


def anchors(year: int) -> dict:
    """The chain of governing feasts for a civil year."""
    e = calculate_gregorian_easter(year)
    return {
        "E": e,                                       # Easter
        "TR": e + datetime.timedelta(days=98),        # Transfiguration (Vardavar)
        "AS": sunday_closest_to(year, 8, 15),         # Assumption
        "EX": sunday_closest_to(year, 9, 14),         # Exaltation of the Cross
        "HE": sunday_closest_to(year, 11, 18),        # Heesnak (Advent start)
        "TH": datetime.date(year, 1, 6),              # Theophany / Nativity
    }


# --------------------------------------------------------------------------- #
# Winter-hinge scheduler (Advent -> Nativity/Theophany -> pre-Lent)
#
# The winter ferial zone resisted the plain day-offset keying because saints are
# laid onto the free Mon/Tue/Thu/Sat weekdays in a fixed order and a single
# merge/drop shifts every downstream day. The fix is to give each winter day a
# *stable grid coordinate* (window, week-relative-to-a-governing-feast, weekday)
# plus forward/backward fast-track and numbered-Sunday coordinates. The same
# saint then lands on the same key every year; the dev build/validate pipeline
# strictly keeps only coordinates whose readings agree across all years.
# --------------------------------------------------------------------------- #

_WD = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_SAINT_WD = (0, 1, 3, 5)   # Mon, Tue, Thu, Sat carry saints; Wed/Fri/Sun do not

# Fixed-date feasts (and feast-eves) whose PROPER readings float across the
# movable ferial slots: in whichever year a feast lands on a given Easter /
# Assumption / Exaltation / Advent offset it injects its proper readings there,
# breaking the otherwise-unanimous ferial consensus so the whole bucket drops.
# They are therefore excluded from every anchored learning bucket (coords_for
# emits no anchored coordinate for them) and resolve only through the dedicated
# top-precedence CF keyspace -- either as a validated composite or, failing that,
# as a flagged estimate. They are also kept off the winter saint/fast grid.
EMBEDDED_FIXED = {
    (4, 7),    # Annunciation to the Holy Theotokos
    (2, 13),   # Eve of the Presentation of the Lord to the Temple
    (9, 8),    # Nativity of the Holy Theotokos
    (11, 21),  # Presentation of the Holy Mother of God to the Temple
    (12, 9),   # Conception of the Holy Theotokos by Anna
}

# The Annunciation (Apr 7) and its eve (Apr 6) are fixed-date feasts whose
# readings are reordered by their collision with the movable Lent / Holy Week /
# Eastertide cycle. The reorder is fully DETERMINISTIC in the Easter offset: for
# each (civil-date, Easter-offset) bucket the reading-set is cross-year identical
# (verified over 2001-2026). So they get a dedicated Easter-offset keyspace
# (AnnE), learned by the strict pipeline -- they ship VALIDATED, not best-guess.
# The feast (Apr 7) is also in EMBEDDED_FIXED (it must not contaminate the E
# ferial buckets); the eve (Apr 6) is left on the normal path and merely gains an
# extra AnnE coordinate, so its single-sample extreme-Easter years still fall
# through to E exactly as before (no coverage regression).
_ANNUNCIATION_MD = {(4, 7), (4, 6)}

# The eve of the Presentation of the Lord (Feb 13) is the exact analog of the
# Annunciation eve (Apr 6): a fixed-date eve whose reading-set is reordered by its
# collision with the movable pre-Lent / Lent cycle, DETERMINISTIC in the Easter
# offset. It gets its own dedicated Easter-offset keyspace (PrLE), learned by the
# strict pipeline and shipped VALIDATED -- keeping it out of the generic ferial
# buckets (no pollution). Single-sample extreme-Easter offsets stay honest blanks.
_PRESENTATION_EVE_MD = {(2, 13)}


def _next_saint_weekday(d):
    """First day on/after d whose weekday carries saints (Mon/Tue/Thu/Sat)."""
    while d.weekday() not in _SAINT_WD:
        d += datetime.timedelta(days=1)
    return d


def winter_window(year: int) -> dict:
    """The two winter ferial windows (start, end inclusive) for a civil year.

    - Advent:        day after this year's Heesnak Sunday (late Nov) .. Jan 5 of
                     the *next* year (the eve of Theophany).
    - Post-Nativity: Jan 14 (day after the octave) .. the Sunday that is the eve
                     of the Fast of Catechumens (= Easter - 70 days).
    """
    he = sunday_closest_to(year, 11, 18)
    return {
        "ADV": (he + datetime.timedelta(days=1), datetime.date(year + 1, 1, 5)),
        "PN": (datetime.date(year, 1, 14),
               calculate_gregorian_easter(year) - datetime.timedelta(days=70)),
    }


def _count_wf(after: datetime.date, upto: datetime.date) -> int:
    """Number of Wed/Fri days in (after, upto] (ordinal in the ferial track)."""
    n = 0
    d = after + datetime.timedelta(days=1)
    while d <= upto:
        if d.weekday() in (2, 4):
            n += 1
        d += datetime.timedelta(days=1)
    return n


def _count_sun(after: datetime.date, upto: datetime.date) -> int:
    """Number of Sundays in [after, upto) -- i.e. strictly before upto."""
    n = 0
    d = after
    while d < upto:
        if d.weekday() == 6:
            n += 1
        d += datetime.timedelta(days=1)
    return n


def _advent_slot(d, he, out):
    """Stable winter coordinates for an Advent day (he < d <= Jan 5).

    The Advent length (Heesnak -> Theophany) varies by ~a week, and the Hebrews/
    Luke lectio-continua fast-forwards in short years, so the same forward ordinal
    carries different readings across length classes. We therefore emit, besides
    the plain forward keys, length-classed variants (prefixed by the Advent length
    in days) and a backward index (counted from Theophany) so a coordinate that is
    only stable within a length class, or only from the tail, can still ship."""
    wd = d.weekday()
    days_from_he = (d - he).days          # >= 1
    week = days_from_he // 7              # week 0 == the opening Fast-of-Advent week
    nat = datetime.date(he.year + 1, 1, 6)
    adv_len = (nat - he).days             # Advent length class (days)
    if wd == 6:                           # numbered Sunday of Advent
        sun = days_from_he // 7
        out["AdvSunL"] = f"{adv_len}:{sun}"               # length-classed forward
        out["AdvSunB"] = str(_count_sun(d, nat))          # backward (1 = last)
        out["AdvSun"] = str(sun)                          # plain forward ordinal
        return
    if week == 0 and wd in (0, 1, 2, 3, 4):   # opening Fast of Advent (Mon-Fri)
        out["AoF"] = str(days_from_he)
        return
    if wd in (2, 4):                      # ferial Wed/Fri fast (lectio continua)
        s1 = he + datetime.timedelta(days=7)   # 1st Sunday of Advent
        fer = _count_wf(s1, d)
        out["AdvFerL"] = f"{adv_len}:{fer}"               # length-classed forward
        out["AdvFerB"] = str(_count_wf(d, nat))           # backward Wed/Fri index
        out["AdvFer"] = str(fer)                          # plain forward
        return
    # saint weekday (Mon/Tue/Thu/Sat): forward + backward, plain + length-classed.
    back_week = (nat - d).days // 7
    out["AdvSatL"] = f"{adv_len}:{week}:{_WD[wd]}"
    out["AdvSatBL"] = f"{adv_len}:{back_week}:{_WD[wd]}"
    out["AdvSat"] = f"{week}:{_WD[wd]}"
    out["AdvSatB"] = f"{back_week}:{_WD[wd]}"


def _civil_fixed_md():
    """(month, day) pairs the immovable-feast civil keyspace claims, so the saint
    replay drops them exactly as the build/mining layer does (keeping the laydown
    aligned with ground truth)."""
    return {tuple(int(x) for x in k.split("-")) for k in _TABLES.get("C", {})}


def _postnat_slot(d, start, end, out):
    """Stable winter coordinates for a post-Nativity day (Jan 14 .. eve of Fast).

    The post-Nativity window length swings widely (Easter governs its end), so the
    same forward ordinal carries different readings across length classes. As in
    Advent we emit plain forward keys plus length-classed and backward variants and
    let the strict filter keep whichever is cross-year consistent."""
    wd = d.weekday()
    nsun = sum(1 for k in range((d - start).days + 1)
               if (start + datetime.timedelta(days=k)).weekday() == 6)
    pn_len = (end - start).days           # post-Nativity length class (days)
    back_week = (end - d).days // 7
    # John the Forerunner: Jan 14, transferred to the next saint weekday when
    # Jan 14 is penitential (Wed/Fri) or a Sunday.
    john = _next_saint_weekday(datetime.date(d.year, 1, 14))
    if d == john:
        out["PnJohn"] = "John"
        return
    if wd == 6:
        if d == end:
            # Eve of the Fast of Catechumens (Easter-70). It is simultaneously a
            # numbered Sunday-after-Nativity, and its readings follow that Sunday
            # number (First Sunday carries an extra Luke 4.14-30 the later Sundays
            # drop), which the Easter-band+offset EB key conflates. Band the eve by
            # the Sunday count so First vs Second separate; the extreme-Easter
            # singletons (nsun 0/5: Jan-13 octave collision, Presentation overlap)
            # fall to their own unsupported keys and stay estimate.
            out["PnEveN"] = str(nsun)
            out["PnEve"] = "0"            # eve of Fast of Catechumens (backward)
        else:
            out["PnSunL"] = f"{pn_len}:{nsun}"
            out["PnSunB"] = str(_count_sun(d, end))     # backward (1 = last before eve)
            out["PnSun"] = str(nsun)      # numbered Sunday after Nativity
        return
    if wd in (2, 4):                      # ferial Wed/Fri
        # Forward Wed/Fri continua index from the window start: the post-Nativity
        # Wed/Fri fast is a sequential Epistle+Gospel march (Hebrews/Luke) that
        # advances per FAST-DAY, not per Sunday, so the count of preceding Wed/Fri
        # days is the stable coordinate (mirrors AdvFer). Keying it by Sunday count
        # (PnFer) instead splits the same continua reading across years.
        out["PnFerF"] = f"{_count_wf(start - datetime.timedelta(days=1), d)}:{_WD[wd]}"
        out["PnFerL"] = f"{pn_len}:{nsun}:{_WD[wd]}"
        out["PnFerB"] = f"{back_week}:{_WD[wd]}"
        out["PnFer"] = f"{nsun}:{_WD[wd]}"
        return
    # saint weekday: senior-saint identity (most specific) + forward/backward grid.
    sid = _zone_saint_replay("PN", d.year).get(d)
    if sid:
        out["PnSaintMD"] = f"{sid}:{d.month:02d}-{d.day:02d}"  # identity x civil date
        out["PnSaintB"] = f"{_easter_band(d.year)}:{sid}"   # Easter-banded variant
        out["PnSaint"] = sid
    out["PnSatL"] = f"{pn_len}:{nsun}:{_WD[wd]}"
    out["PnSatBL"] = f"{pn_len}:{back_week}:{_WD[wd]}"
    out["PnSat"] = f"{nsun}:{_WD[wd]}"
    out["PnSatB"] = f"{back_week}:{_WD[wd]}"


def _winter_coords_raw(d: datetime.date) -> dict:
    """Winter-zone slot coordinates for a date, ignoring the embedded-fixed guard
    (used both by winter_coords and by the embedded-feast slot resolver)."""
    out = {}
    # Advent: a January 1-5 date belongs to the *previous* civil year's Advent.
    for y in (d.year, d.year - 1):
        adv_start, adv_end = winter_window(y)["ADV"]
        if adv_start <= d <= adv_end:
            _advent_slot(d, adv_start - datetime.timedelta(days=1), out)
            break
    # Post-Nativity (Jan 14 .. eve of Fast of Catechumens).
    start, end = winter_window(d.year)["PN"]
    if start <= d <= end:
        _postnat_slot(d, start, end, out)
    return out


def winter_coords(d: datetime.date) -> dict:
    """Winter-zone slot coordinates for a date (empty if outside both windows)."""
    if (d.month, d.day) in EMBEDDED_FIXED:
        return {}                         # don't let floating feasts pollute the grid
    return _winter_coords_raw(d)


# Winter keyspaces, most specific first (forward grids before backward grids).
WINTER_KS = ["PnOct", "PnJohn", "PnEveN", "PnEve",
             "AdvSunL", "AdvSunB", "AdvSun",
             "PnSunL", "PnSunB", "PnSun", "AoF",
             "AdvFerL", "AdvFerB", "AdvFer",
             "PnFerF", "PnFerL", "PnFerB", "PnFer",
             "AdvSatL", "AdvSatBL", "AdvSat", "AdvSatB",
             "PnSaintMD", "PnSaintB", "PnSaint",
             "PnSatL", "PnSatBL", "PnSat", "PnSatB"]


# --------------------------------------------------------------------------- #
# Summer & autumn hinge schedulers
#
# Two more variable-gap zones with the same drift as winter:
#   * Summer  (Transfiguration -> Assumption): Transfiguration is Easter-anchored
#     (Easter+98) while the Fast of Assumption is solar-anchored (before the
#     Sunday closest to Aug 15), so the saints/Sundays/Wed-Fri fasts laid in the
#     gap drift in Easter-offset and plain offset keys are dropped.
#   * Autumn  (Assumption -> Exaltation): both anchors are "Sunday closest to"
#     solar dates, but the count of Sundays / the Fast-of-Holy-Cross position
#     between them still varies year to year.
# Each day gets a stable grid coordinate (numbered Sunday, forward/backward fast
# index, (week, weekday) saint grid) so the same saint lands on the same key.
# --------------------------------------------------------------------------- #


def _hinge_anchors(year: int) -> dict:
    """The summer/autumn/post-Exaltation anchor dates and ferial-window edges for a
    civil year. Shared by the grid-coordinate builder (`_hinge_coords_raw`) and the
    saint-replay window helpers so the two can never drift out of step."""
    e = calculate_gregorian_easter(year)
    tr = e + datetime.timedelta(days=98)              # Transfiguration (Vardavar)
    asun = sunday_closest_to(year, 8, 15)             # Assumption
    ex = sunday_closest_to(year, 9, 14)               # Exaltation
    he = sunday_closest_to(year, 11, 18)              # Heesnak (Advent start)
    as_fast_mon = asun - datetime.timedelta(days=6)   # Mon of Fast of Assumption
    ex_fast_mon = ex - datetime.timedelta(days=6)     # Mon of Fast of Holy Cross
    return {
        "TR": tr, "AS": asun, "EX": ex, "HE": he,
        "AS_FAST_MON": as_fast_mon, "EX_FAST_MON": ex_fast_mon,
        "SUMMER_EVE": as_fast_mon - datetime.timedelta(days=1),
        "AUTUMN_EVE": ex_fast_mon - datetime.timedelta(days=1),
    }


def _summer_slot(d, tr, fast_mon, eve, out):
    """Grid coordinates for a Transfiguration->Assumption day (tr < d <= eve).

    Transfiguration is Easter-anchored, the Fast of Assumption solar, so the gap
    (and the saint grid laid in it) varies; we emit plain + length-classed +
    backward keys exactly as in the winter Advent grid."""
    wd = d.weekday()
    days_from_tr = (d - tr).days          # >= 1
    week = days_from_tr // 7
    span = (eve - tr).days                # summer length class (days)
    back_week = (fast_mon - d).days // 7
    if wd == 6:
        if d == eve:                      # eve of the Fast of Assumption (backward)
            out["TrEve"] = "0"
        else:
            out["TrSunL"] = f"{span}:{days_from_tr // 7}"
            out["TrSun"] = str(days_from_tr // 7)
        return
    if wd in (2, 4):                      # Wed/Fri fast (forward continua index)
        fer = _count_wf(tr, d)
        out["TrFerL"] = f"{span}:{fer}"
        out["TrFer"] = str(fer)
        return
    # saint weekday: senior-saint identity (most specific) + forward/backward grid.
    sid = _zone_saint_replay("Tr", d.year).get(d)
    if sid:
        out["TrSaintMD"] = f"{sid}:{d.month:02d}-{d.day:02d}"  # identity x civil date
        out["TrSaintB"] = f"{_easter_band(d.year)}:{sid}"   # Easter-banded variant
        out["TrSaint"] = sid
    out["TrSatL"] = f"{span}:{week}:{_WD[wd]}"
    out["TrSatBL"] = f"{span}:{back_week}:{_WD[wd]}"
    out["TrSat"] = f"{week}:{_WD[wd]}"
    out["TrSatB"] = f"{back_week}:{_WD[wd]}"


def _autumn_slot(d, asun, exfast_mon, out):
    """Grid coordinates for an Assumption->Exaltation day (asun < d <= eve)."""
    wd = d.weekday()
    days_from_as = (d - asun).days        # >= 1
    week = days_from_as // 7
    eve = exfast_mon - datetime.timedelta(days=1)
    span = (eve - asun).days              # autumn length class (days)
    back_week = (exfast_mon - d).days // 7
    if wd == 6:
        if d == eve:                      # eve of Fast of Cross
            out["AsEve"] = "0"
        else:
            out["AsSunL"] = f"{span}:{days_from_as // 7}"
            out["AsSun"] = str(days_from_as // 7)
        return
    if wd in (2, 4):
        fer = _count_wf(asun, d)
        out["AsFerL"] = f"{span}:{fer}"
        out["AsFer"] = str(fer)
        return
    sid = _zone_saint_replay("As", d.year).get(d)
    if sid:
        out["AsSaintMD"] = f"{sid}:{d.month:02d}-{d.day:02d}"  # identity x civil date
        out["AsSaintB"] = f"{_easter_band(d.year)}:{sid}"   # Easter-banded variant
        out["AsSaint"] = sid
    # Weekday x civil-date saint-grid key (solar-anchored zone; see ExSatMD).
    out["AsSatMD"] = f"{_WD[wd]}:{d.month:02d}-{d.day:02d}"
    out["AsSatL"] = f"{span}:{week}:{_WD[wd]}"
    out["AsSatBL"] = f"{span}:{back_week}:{_WD[wd]}"
    out["AsSat"] = f"{week}:{_WD[wd]}"
    out["AsSatB"] = f"{back_week}:{_WD[wd]}"


def _postex_slot(d, ex, he, out):
    """Grid coordinates for a post-Exaltation day (ex < d < Advent start)."""
    wd = d.weekday()
    days_from_ex = (d - ex).days          # >= 1
    week = days_from_ex // 7
    span = (he - datetime.timedelta(days=1) - ex).days   # post-Ex length class
    back_week = (he - d).days // 7
    if wd == 6:
        out["ExSunL"] = f"{span}:{days_from_ex // 7}"
        out["ExSun"] = str(days_from_ex // 7)
        return
    if wd in (2, 4):
        fer = _count_wf(ex, d)
        out["ExFerL"] = f"{span}:{fer}"
        out["ExFer"] = str(fer)
        return
    sid = _zone_saint_replay("Ex", d.year).get(d)
    if sid:
        out["ExSaintMD"] = f"{sid}:{d.month:02d}-{d.day:02d}"  # identity x civil date
        out["ExSaintB"] = f"{_easter_band(d.year)}:{sid}"   # Easter-banded variant
        out["ExSaint"] = sid
    # Weekday x civil-date saint-grid key: the post-Exaltation zone is doubly
    # solar-anchored (Exaltation = Sunday nearest Sep 14), so its saint-weekday
    # slots sit on near-fixed civil dates. A single phase-shift year (the saint
    # laid one weekday earlier) drops the otherwise-unanimous span:week grid for
    # all years; keying the bare slot by (weekday, civil-date) clusters the
    # consistent years and isolates the shifted one. Solar zones only (not Tr).
    out["ExSatMD"] = f"{_WD[wd]}:{d.month:02d}-{d.day:02d}"
    out["ExSatL"] = f"{span}:{week}:{_WD[wd]}"
    out["ExSatBL"] = f"{span}:{back_week}:{_WD[wd]}"
    out["ExSat"] = f"{week}:{_WD[wd]}"
    out["ExSatB"] = f"{back_week}:{_WD[wd]}"


def _hinge_coords_raw(d: datetime.date) -> dict:
    """Summer/autumn grid coordinates (no embedded-fixed guard)."""
    out = {}
    a = _hinge_anchors(d.year)
    # Summer: strictly after Transfiguration, up to the eve of Fast of Assumption.
    if a["TR"] < d <= a["SUMMER_EVE"]:
        _summer_slot(d, a["TR"], a["AS_FAST_MON"], a["SUMMER_EVE"], out)
    # Autumn: strictly after Assumption, up to the eve of Fast of Holy Cross.
    if a["AS"] < d <= a["AUTUMN_EVE"]:
        _autumn_slot(d, a["AS"], a["EX_FAST_MON"], out)
    # Post-Exaltation: after Exaltation up to the start of Advent (Heesnak).
    if a["EX"] < d < a["HE"]:
        _postex_slot(d, a["EX"], a["HE"], out)
    return out


def hinge_coords(d: datetime.date) -> dict:
    """Summer/autumn grid coordinates (empty for embedded floating feasts)."""
    if (d.month, d.day) in EMBEDDED_FIXED:
        return {}
    return _hinge_coords_raw(d)


# Summer/autumn keyspaces, most specific first (forward grids before backward).
# Each {Zone}Saint identity coordinate sits immediately above its zone's grid
# saint keys, mirroring how PnSaint outranks PnSat* in WINTER_KS.
HINGE_KS = ["TrEve", "AsEve",
            "TrSunL", "AsSunL", "ExSunL", "TrSun", "AsSun", "ExSun",
            "TrFerL", "AsFerL", "ExFerL", "TrFer", "AsFer", "ExFer",
            "TrSaintMD", "TrSaintB", "TrSaint", "TrSatL", "TrSatBL",
            "AsSaintMD", "AsSaintB", "AsSaint", "AsSatMD", "AsSatL", "AsSatBL",
            "ExSaintMD", "ExSaintB", "ExSaint", "ExSatMD", "ExSatL", "ExSatBL",
            "TrSat", "AsSat", "ExSat", "TrSatB", "AsSatB", "ExSatB"]


# --------------------------------------------------------------------------- #
# Saint-identity replay (winter post-Nativity + summer / autumn / post-Exaltation)
#
# In every variable-gap zone the saints are laid in a CANONICAL ORDER onto the
# free Mon/Tue/Thu/Sat slots, so a single merge/drop shifts every downstream saint
# onto a different grid key and the strict cross-year filter drops it. The fix is
# to key each physical day by the SENIOR SAINT'S IDENTITY ({Zone}Saint) rather than
# its drifting grid position. The mined schedule (dev/saint_schedule.json) carries
# ordering / pins / weekday-locks ONLY -- never readings -- so an imperfect replay
# can only lower coverage (a mis-keyed day makes its bucket cross-year-inconsistent
# and is dropped), never ship a wrong reading. Readings stay in the validated table
# under the {Zone}Saint keyspace, learned by the existing strict pipeline.
# --------------------------------------------------------------------------- #


def _summer_saint_window(year: int):
    """(start, end) free-slot window of the summer (Transfiguration->Assumption)
    saint zone: the day after Transfiguration .. eve of the Fast of Assumption."""
    a = _hinge_anchors(year)
    return (a["TR"] + datetime.timedelta(days=1), a["SUMMER_EVE"])


def _autumn_saint_window(year: int):
    """(start, end) free-slot window of the autumn (Assumption->Exaltation) saint
    zone: the day after Assumption .. eve of the Fast of the Holy Cross."""
    a = _hinge_anchors(year)
    return (a["AS"] + datetime.timedelta(days=1), a["AUTUMN_EVE"])


def _postex_saint_window(year: int):
    """(start, end) free-slot window of the post-Exaltation saint zone: the day
    after Exaltation .. the eve of Advent (Heesnak)."""
    a = _hinge_anchors(year)
    return (a["EX"] + datetime.timedelta(days=1), a["HE"] - datetime.timedelta(days=1))


SAINT_SCHEDULE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "data", "saint_schedule.json")


def _load_saint_schedule():
    """The mined per-zone saint schedules (ordering / pins / weekday locks only --
    never readings), keyed by zone ("PN"/"Tr"/"As"/"Ex"). Absent in a thin checkout
    -> {}; then no {Zone}Saint coordinate is emitted and the grid keys behave
    exactly as before."""
    try:
        with open(SAINT_SCHEDULE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


_SAINT_SCHEDULE = _load_saint_schedule()

SAINT_READINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "data", "saint_readings.json")


def _load_saint_readings():
    """The intrinsic reading-set per saint identity ({zone: {sid: [readings]}}),
    mined alongside the schedule. Consumed ONLY by the labeled generative
    best-guess tier; absent in a thin checkout -> {} -> no generative saint
    readings (days stay estimate, exactly as before)."""
    try:
        with open(SAINT_READINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


_SAINT_READINGS = _load_saint_readings()

SECOND_VOLUME_CYCLES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "second_volume_cycles.json")


def _load_cycle_saints():
    """Per-year-type saint placements distilled from the Tonatsoyts Second Volume,
    keyed by Julian Easter date -> {"MM-DD": [zone, saint_id]} (see
    dev/build_second_volume_cycles.py). A Gregorian year is matched to the cycle whose
    Julian Easter equals its Gregorian Easter date -- valid because Easter (a Sunday)
    fixes the year's weekday grid for post-Feb-29 dates. Absent in a thin checkout ->
    {} -> the cycle tier is inert and the engine behaves exactly as before."""
    try:
        with open(SECOND_VOLUME_CYCLES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


_CYCLE_SAINTS = _load_cycle_saints()

CONTINUA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "data", "continua_sequence.json")


def _load_continua():
    """Modal reading per (span, index, weekday) for the Fast-of-Assumption Wed/Fri
    continua. Consumed ONLY by the labeled generative best-guess tier; absent in a
    thin checkout -> {} -> those days stay estimate, exactly as before."""
    try:
        with open(CONTINUA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


_CONTINUA = _load_continua()

# id -> human label per zone, for the generative tier's feast name.
_SAINT_LABEL = {
    zone: {e["id"]: e.get("label", e["id"])
           for e in sec.get("sequence", [])}
    for zone, sec in _SAINT_SCHEDULE.items()
}

# Per-zone replay descriptor: the identity coordinate emitted, the free-slot
# window, and whether the John-the-Forerunner Jan-14 slot is skipped (PN only).
_SAINT_ZONES = {
    "PN": {"coord": "PnSaint", "window": lambda y: winter_window(y)["PN"],
           "skip_john": True},
    "Tr": {"coord": "TrSaint", "window": _summer_saint_window, "skip_john": False},
    "As": {"coord": "AsSaint", "window": _autumn_saint_window, "skip_john": False},
    "Ex": {"coord": "ExSaint", "window": _postex_saint_window, "skip_john": False},
}


@functools.lru_cache(maxsize=None)
def _zone_saint_replay(zone, year, full=False):
    """Lay a zone's canonical saint schedule onto `year`'s actual free
    saint-weekdays and return {date: saint_id}.

    Pure calendar function -- emits identities ({Zone}Saint coordinates) only,
    never readings, so an imperfect replay can only lower coverage, never ship a
    wrong reading. Three anchor classes (see dev/saint_schedule.py):
      * pin:Sat -- a high-rank Father locked to the Saturday in its solar window;
      * head    -- the opening flow block, laid FORWARD from the window start
                   (stable: optional minor saints only ever appear after it);
      * tail    -- the closing block, each locked to one weekday and laid
                   BACKWARD (last free <weekday>), since its forward ordinal
                   drifts with the count of optional middle saints.

    `full=False` (the validated default used by `coords_for`) leaves middle /
    low-support saints UNASSIGNED -- they fall through to the grid keys or to
    estimate, and the strict cross-year filter governs shipping. `full=True` adds
    a fourth middle-fill pass that places every remaining free slot from the
    canonical order; it is consumed ONLY by the labeled generative best-guess
    tier (`_generative_saint`), never by `coords_for`, so the validated build is
    byte-identical regardless."""
    z = _SAINT_ZONES[zone]
    seq = _SAINT_SCHEDULE.get(zone, {}).get("sequence")
    if not seq:
        return {}
    start, end = z["window"](year)
    john = (_next_saint_weekday(datetime.date(year, 1, 14))
            if z["skip_john"] else None)
    civil = _civil_fixed_md()
    slots = []
    d = start
    while d <= end:
        md = (d.month, d.day)
        if (d.weekday() in _SAINT_WD and d != john
                and md not in EMBEDDED_FIXED and md not in civil):
            slots.append(d)
        d += datetime.timedelta(days=1)

    assigned, used = {}, set()

    # Pass A -- pinned Saturdays claim the Saturday in their solar window.
    pins = [e for e in seq if e["anchor"] == "pin:Sat"]
    placed_pins = set()
    for e in pins:
        lo = tuple(int(x) for x in e["date_lo"].split("-"))
        hi = tuple(int(x) for x in e["date_hi"].split("-"))
        for dd in slots:
            if (dd.weekday() == 5 and dd not in used
                    and lo <= (dd.month, dd.day) <= hi):
                assigned[dd] = e["id"]
                used.add(dd)
                placed_pins.add(e["id"])
                break

    # Pass B -- the head flow block fills the earliest free non-pinned slots.
    free = [dd for dd in slots if dd not in used]
    heads = [e for e in seq if e["anchor"] == "head"]
    for e, dd in zip(heads, free):
        assigned[dd] = e["id"]
        used.add(dd)

    # Pass C -- the closing block is laid backward (each tail saint takes the LAST
    # still-free slot of its weekday), but ONLY in long windows: the tail block
    # co-occurs exactly with the last pinned Saturday, so gate on it to avoid
    # grabbing a middle saint's leftover weekday slot in a short year.
    if pins and pins[-1]["id"] in placed_pins:
        for e in seq:
            if e["anchor"] != "tail":
                continue
            w = _WD.index(e["weekday"])
            cands = [dd for dd in slots if dd.weekday() == w and dd not in used]
            if cands:
                assigned[cands[-1]] = e["id"]
                used.add(cands[-1])

    # Pass D (generative best-guess only) -- fill every still-free slot from the
    # canonical order. `seq` is order-sorted, so zipping the remaining entries
    # onto the remaining slots in calendar order lays the middle/minor saints
    # deterministically. Unvalidated by construction (these are the single-sample
    # / floating days), so it is gated behind `full` and never feeds coords_for.
    if full:
        placed = set(assigned.values())
        free_slots = sorted(dd for dd in slots if dd not in used)
        remaining = [e for e in seq if e["id"] not in placed]
        for e, dd in zip(remaining, free_slots):
            assigned[dd] = e["id"]
            used.add(dd)
    return assigned


def _generative_saint(d: datetime.date):
    """Labeled best-guess for a saint-weekday the validated table can't cover:
    run the FULL laydown for d's zone and ship the placed saint's intrinsic
    readings (from dev/saint_readings.json). Returns (zone, sid, label, readings)
    or None. Unvalidated by construction -- the caller tags it generative-saint."""
    if d.weekday() not in _SAINT_WD or not _SAINT_READINGS:
        return None
    for zone in ("PN", "Tr", "As", "Ex"):
        start, end = _SAINT_ZONES[zone]["window"](d.year)
        if not (start <= d <= end):
            continue
        sid = _zone_saint_replay(zone, d.year, full=True).get(d)
        if not sid:
            return None
        refs = _SAINT_READINGS.get(zone, {}).get(sid)
        if not refs:
            return None
        label = _SAINT_LABEL.get(zone, {}).get(sid, sid)
        return zone, sid, label, list(refs)
    return None


def _cycle_saint(d: datetime.date):
    """Authoritative saint for a saint-weekday from the Tonatsoyts Second Volume cycle
    matched to this year's Easter. Returns (zone, sid, label, readings) or None.

    Unlike `_generative_saint` (a fixed-order laydown that is systematically wrong on
    the floating-saint days), this reads the per-year-type calendar directly: the year's
    Gregorian Easter date selects the cycle, and the cycle gives the saint identity for
    d's civil date. Identity -> readings reuses dev/saint_readings.json. Validated
    against ground truth (dev/second_volume_resolve.py)."""
    if d.weekday() not in _SAINT_WD or not _CYCLE_SAINTS or not _SAINT_READINGS:
        return None
    e = calculate_gregorian_easter(d.year)
    cyc = _CYCLE_SAINTS.get(f"{e.month:02d}-{e.day:02d}")
    if not cyc:
        return None
    rec = cyc.get(f"{d.month:02d}-{d.day:02d}")
    if isinstance(rec, dict):
        # Leap-conditional placement: a leap year advances the summer Saturday chain, so
        # the same Easter date ships a distinct leap-parity saint (build-time keyed).
        rec = rec.get("leap" if calendar.isleap(d.year) else "common")
    if not rec:
        return None
    stored_zone, sid = rec
    # Fire only inside an actual saint zone (PN/Tr/As/Ex), where d's saint readings live.
    runtime_zone = next((z for z, zd in _SAINT_ZONES.items()
                         if zd["window"](d.year)[0] <= d <= zd["window"](d.year)[1]),
                        None)
    if runtime_zone is None:
        return None
    for z in (runtime_zone, stored_zone):
        refs = _SAINT_READINGS.get(z, {}).get(sid)
        if refs:
            label = _SAINT_LABEL.get(z, {}).get(sid) or _SAINT_LABEL.get(
                stored_zone, {}).get(sid, sid)
            return z, sid, label, list(refs)
    return None


def _generative_continua(d: datetime.date):
    """Labeled best-guess for a Fast-of-the-Assumption Wed/Fri day the validated
    table can't cover: the post-Transfiguration lectio-continua's deep tail. Ship
    the modal reading for this (summer-span, forward-Wed/Fri-index, weekday)
    bucket. Returns a readings list or None. ~85% correct on the cache."""
    if d.weekday() not in (2, 4) or not _CONTINUA:
        return None
    a = _hinge_anchors(d.year)
    if not (a["TR"] < d < a["AS"]):             # Transfiguration -> Assumption
        return None
    span = (a["SUMMER_EVE"] - a["TR"]).days
    idx = _count_wf(a["TR"], d)
    e = calculate_gregorian_easter(d.year)
    emd = f"{e.month:02d}-{e.day:02d}"
    refs = _CONTINUA.get("TrFast", {}).get("buckets", {}).get(
        f"{emd}:{span}:{idx}:{d.weekday()}")
    return list(refs) if refs else None


def coords_for(d: datetime.date) -> dict:
    """All candidate (keyspace -> key) liturgical coordinates for a date."""
    md = (d.month, d.day)
    if md in EMBEDDED_FIXED:
        # Floating fixed-feast: resolve ONLY via civil date -> CF, never through
        # an anchored cycle whose cleaned ferial bucket it would otherwise grab.
        out = {"C": md, "CF": f"{d.month:02d}-{d.day:02d}"}
        if md in _ANNUNCIATION_MD:
            # ...except the Annunciation, whose Holy-Week reorder IS computable:
            # key it by (civil-date, Easter-offset) so the strict build learns
            # each reorder bucket and ships it validated.
            e_off = (d - anchors(d.year)["E"]).days
            out["AnnE"] = f"{d.month:02d}-{d.day:02d}:{e_off}"
        if md in _PRESENTATION_EVE_MD:
            # ...and the Presentation eve, whose pre-Lent reorder is likewise
            # computable: key it by (civil-date, Easter-offset) so the strict
            # build learns each reorder bucket and ships it validated. (PrLE is a
            # distinct keyspace from the winter-grid PnEve = eve of the Fast of
            # Catechumens; do not conflate them.)
            e_off = (d - anchors(d.year)["E"]).days
            out["PrLE"] = f"{d.month:02d}-{d.day:02d}:{e_off}"
        return out
    y = d.year
    a = anchors(y)
    a_prev = anchors(y - 1)
    e_off = (d - a["E"]).days
    cs = {
        "C": (d.month, d.day),                  # civil date (immovable feasts)
        "E": e_off,                             # Easter-anchored core
        "AS": (d - a["AS"]).days,               # Assumption period
        "EX": (d - a["EX"]).days,               # Exaltation period
        "HE": (d - a["HE"]).days,               # Advent (this year)
        "HEp": (d - a_prev["HE"]).days,         # Advent tail into early January
        "TH": (d - a["TH"]).days,               # weeks after Nativity
        "THp": (d - a_prev["TH"]).days,
    }
    # Easter-band sub-key: same Easter offset, prefixed by the year's pn_len band,
    # so single-outlier extreme-Easter years separate from the cross-year consensus
    # (emitted only inside the Easter-core window; string-keyed, self-guarded).
    if WINDOWS["E"][0] <= e_off <= WINDOWS["E"][1]:
        cs["EB"] = f"{_easter_band(y)}:{e_off}"
    # Advent-length-band sub-keys for the Heesnak offset cycles (this year + the
    # tail into early January), so the Heesnak Sunday and the Advent continua
    # separate by Advent-length class the same way the winter grid keys do. Placed
    # at low precedence (just above HE/HEp), so the winter grid still wins where it
    # ships; these only catch days the grid leaves (chiefly Heesnak Sunday itself).
    if WINDOWS["HE"][0] <= cs["HE"] <= WINDOWS["HE"][1]:
        cs["HEB"] = f"{_adv_len(y)}:{cs['HE']}"
    if WINDOWS["HEp"][0] <= cs["HEp"] <= WINDOWS["HEp"][1]:
        cs["HEpB"] = f"{_adv_len(y - 1)}:{cs['HEp']}"
    # Naming octave (Jan 13, the eighth day of Nativity): a fixed-date feast with
    # cross-year-invariant proper readings that the civil pass cannot claim because
    # in the rare extreme-Easter year where Jan 13 coincides with the eve of the
    # Fast of Catechumens (Easter-70) the movable eve displaces the octave. Emit a
    # dedicated constant key for every year EXCEPT that collision, so the octave
    # ships and the eve year falls through to its Easter-anchored slot / estimate.
    if md == (1, 13) and e_off != -70:
        cs["PnOct"] = "01-13"
    # Annunciation eve (Apr 6): an extra Easter-offset coordinate so its Holy-Week
    # reorder buckets ship validated, while leaving its normal E coordinate intact
    # (single-sample extreme years fall through to E exactly as before).
    if md in _ANNUNCIATION_MD:
        cs["AnnE"] = f"{d.month:02d}-{d.day:02d}:{e_off}"
    cs.update(winter_coords(d))                 # winter grid slots (string keys)
    cs.update(hinge_coords(d))                  # summer/autumn grid slots
    return cs


def _movable_coords(d: datetime.date) -> dict:
    """The anchored + winter coordinates a date WOULD have if it were not an
    embedded fixed-feast -- i.e. the movable ferial/Sunday slot it lands on.

    Used only to resolve the underlying slot for an embedded feast's composite;
    excludes the civil ("C") keyspace (which would just be the feast itself)."""
    y = d.year
    a = anchors(y)
    a_prev = anchors(y - 1)
    cs = {
        "E": (d - a["E"]).days,
        "AS": (d - a["AS"]).days,
        "EX": (d - a["EX"]).days,
        "HE": (d - a["HE"]).days,
        "HEp": (d - a_prev["HE"]).days,
        "TH": (d - a["TH"]).days,
        "THp": (d - a_prev["TH"]).days,
    }
    # Advent-length-band sub-keys (mirroring coords_for): the movable slot that a
    # Heesnak-Sunday-collision embedded feast lands on lives in the HEB band, which
    # _movable_slot_readings can only reach if we emit it here the same way.
    if WINDOWS["HE"][0] <= cs["HE"] <= WINDOWS["HE"][1]:
        band = _adv_len(d.year)
        # The band-46 Advent (Heesnak) Sunday is ALWAYS Nov 21 -- the Presentation
        # of the Theotokos -- so its own slot is never learnable (it is only ever an
        # embedded feast). But the Tonats'oyts (p. 543, which lays the Nov-21 canon
        # directly after it) assigns Nov 21 the "Eleventh Sunday after the Holy Cross,"
        # which is exactly band 47's Advent Sunday (both bands share that numbered
        # Sunday; confirmed over the band-47 years 2005/2011/2016/2022 and the band-46
        # years 2004/2010/2021). So resolve the offset-0 slot of
        # the shortest Advent through band 47's validated reading-set. See
        # docs/sources/tonatsooyts-presentation-theotokos.md.
        if band == 46 and cs["HE"] == 0:
            band = 47
        cs["HEB"] = f"{band}:{cs['HE']}"
    if WINDOWS["HEp"][0] <= cs["HEp"] <= WINDOWS["HEp"][1]:
        cs["HEpB"] = f"{_adv_len(d.year - 1)}:{cs['HEp']}"
    cs.update(_winter_coords_raw(d))
    cs.update(_hinge_coords_raw(d))
    return cs


# --------------------------------------------------------------------------- #
# Embedded fixed-feast composites
#
# A floating feast combines with the movable slot it lands on by liturgical
# rank: it DISPLACES a dedicated saint-weekday slot (its own proper only) but
# CO-CELEBRATES with a Sunday / ferial-fast / post-feast continua slot (proper
# readings ++ that slot's readings). Saturday (a saint/vigil day) is always
# displaced. The proper blocks below are the cross-year-invariant prefix mined
# from ground truth (see dev/composite_probe.py). Only feasts whose composite
# is deterministic under this rule are listed; irregular ones (Annunciation
# Apr 7, the Presentation eve Feb 13) are intentionally absent and stay flagged
# estimates so the 0-wrong contract holds.
# --------------------------------------------------------------------------- #

EMBEDDED_PROPER = {
    (9, 8): ("Proverbs 31.29-31", "Isaiah 61.9",
             "St. Paul's Epistle to the Galatians 3.24-29", "Matthew 1.1-17"),
    (11, 21): ("Song of Solomon 1.2-11", "Proverbs 11.30-12.4", "Isaiah 52.7-10",
               "Zechariah 2.10-13", "Malachi 3.1-2",
               "St. Paul's Second Epistle to the Corinthians 6.16-7.1",
               "Luke 1.39-56"),
    (12, 9): ("Song of Solomon 6.3-8", "Malachi 3.1-2",
              "St. Paul's Epistle to the Galatians 3.24-29", "Luke 1.39-56"),
}

_EMBEDDED_FEAST = {
    (9, 8): "Feast of the Birth of Holy Virgin Mary from Anna",
    (11, 21): "Presentation of the Holy Mother of God to the Temple",
    (12, 9): "Feast of the Conception of the Holy Virgin Mary by Anna",
}

# Dedicated saint-weekday slots a floating feast displaces (proper only).
_REPLACE_KS = {"AdvSat", "AdvSatB", "PnSat", "PnJohn", "PnEve"}


def _embedded_composite(d, tables):
    """Readings for an embedded fixed-feast via the displace/co-celebrate rule,
    or None if its slot is not (yet) resolvable. Returns a list of refs."""
    proper = EMBEDDED_PROPER.get((d.month, d.day))
    if proper is None:
        return None
    cs = _movable_coords(d)
    # Saturday, or any dedicated winter saint-weekday slot -> feast displaces it.
    if d.weekday() == 5 or any(ks in cs for ks in _REPLACE_KS):
        return list(proper)
    # Otherwise co-celebrate: proper ++ the resolved movable slot's readings.
    slot = _movable_slot_readings(d, tables, with_band=False)
    if slot is not None:
        return list(proper) + slot
    return None


# --------------------------------------------------------------------------- #
# Annunciation (Apr 7) collision composite
#
# The Annunciation is a fixed-date feast (Apr 7) whose readings the Tonatsooyts
# prescribes by COMBINING a fixed proper with the movable Lent / Holy Week /
# Eastertide day it lands on, ordered by the rank of that day. Source rubric:
# Tonatsooyts pp. 486-488 (see docs/sources/tonatsooyts-annunciation-canon.md).
#
# The strict pipeline already learns the cross-year-consistent buckets via the
# AnnE keyspace (keyed on the civil date + Easter offset) and ships them VALIDATED
# for every offset observed in >=2 agreeing years. This composite is the BEST-GUESS
# fallback for the offsets AnnE cannot validate -- single-sample collisions and
# Easter offsets never seen in 2001-2026 (e.g. 2027, where Apr 7 = Easter+10). It
# is labeled generative/best-guess, never validated: the reading ORDER follows the
# rubric deterministically, but the published calendar liturgically REDUCES the day
# portion (e.g. Eastertide keeps only a Gospel; a Lenten day drops its vespers set) in
# a way the flat E/EB slots cannot express -- which sub-run is Matins vs Liturgy vs
# vespers is not recorded anywhere reachable. So the composite does not attempt that
# reduction: it errs toward a SUPERSET (extra day readings are acceptable) and only
# guarantees it never DROPS a reading the calendar keeps. See _annunciation_composite.
# --------------------------------------------------------------------------- #

_ANNUNCIATION_PROPER = (
    "Song of Solomon 1.2-11", "Proverbs 11.30-12.4", "Isaiah 52.7-10",
    "Zechariah 2.10-13", "Malachi 3.1-2",
    "St. Paul's Second Epistle to the Corinthians 6.16-7.1", "Luke 1.26-38",
)

# Easter offset of Apr 7 -> combination order (Tonatsooyts pp. 486-488):
#   day -> proper : Lazarus Saturday (-8), Great Mon/Tue/Wed (-6/-5/-4), and deep-Lent
#                   SUNDAYS (offset <= -9 and offset % 7 == 0), which have a Liturgy.
#   proper -> day : Palm Sunday (-7), Great Thu/Fri (-3/-2), Holy Sat (-1), Easter (0),
#                   and all of Eastertide / Yinants (offset >= +1).
#   proper alone  : aliturgical deep-Lent WEEKDAY ferias (offset <= -9, non-Sunday),
#                   which have no Liturgy readings, so the feast proper stands alone.
_ANN_DAY_FIRST = frozenset({-8, -6, -5, -4})
_ANN_PROPER_FIRST = frozenset({-7, -3, -2, -1, 0})


def _movable_slot_entry(d, tables=None, with_band=True):
    """The validated table entry (dict with "feast"/"readings") of the movable
    ferial/Sunday slot a fixed-date feast lands on, or None. Excludes the civil/
    Annunciation keyspaces and the dedicated saint-weekday slots a feast displaces. When
    ``with_band`` is set, the leap-corrected Easter-band sub-key (EB) is tried first,
    matching the runtime precedence for the underlying paschal day."""
    if tables is None:
        tables = _TABLES
    cs = dict(_movable_coords(d))
    if with_band:
        e_off = cs.get("E")
        if e_off is not None and WINDOWS["E"][0] <= e_off <= WINDOWS["E"][1]:
            cs["EB"] = f"{_easter_band(d.year)}:{e_off}"
    for ks in PRECEDENCE:
        if ks in ("C", "CF", "AnnE") or ks in _REPLACE_KS or ks not in cs:
            continue
        key = cs[ks]
        win = WINDOWS[ks]
        if win is not None and not (win[0] <= key <= win[1]):
            continue
        entry = tables.get(ks, {}).get(key)
        if entry:
            return entry
    return None


def _movable_slot_readings(d, tables=None, with_band=True):
    """Readings of the movable slot a fixed-date feast lands on, or None."""
    entry = _movable_slot_entry(d, tables, with_band)
    return list(entry["readings"]) if entry is not None else None


def _collision_base_feast(d, tables=None):
    """The NAME of the movable/base commemoration a fixed-date feast co-celebrates on
    ``d``: the pre-Lent cohort martyr keyed to this Easter offset, else the movable
    slot's feast string, else None. The source calendar headlines a fixed/movable
    collision day by this movable day (adding the fixed feast alongside), so the engine
    names it the same way instead of by the fixed feast alone."""
    e_off = (d - calculate_gregorian_easter(d.year)).days
    for _sid, off, _may_shift, label, _reads in _PRELENT_COHORT:
        if off == e_off:
            return label
    entry = _movable_slot_entry(d, tables)
    return entry["feast"] if entry is not None else None


# Separator between the components the source packs into one feast name (calendar-position
# label, commemoration, eve/status note). The source delimits them with <br>; the fetch
# layer (dev/fetch_reference._strip) preserves that boundary as this string, so the shipped
# table and every served label carry the components already split -- the engine never has
# to re-derive the boundary. Keep in sync with dev/fetch_reference.FEAST_SEP.
_FEAST_SEP = " — "


def _annunciation_composite(d, tables=None):
    """Best-guess Annunciation (Apr 7) readings via the Tonatsooyts collision rule,
    for offsets the validated AnnE keyspace does not cover. Returns a list of refs
    or None (None only if the date is not Apr 7).

    The flat E/EB slots carry no service structure, so the co-celebration reductions
    the printed calendar applies (dropping a day's Matins/vespers set, keeping only a
    Gospel) cannot be reproduced from the data. Rather than risk DROPPING a reading the
    calendar keeps, this best-guess errs toward a superset: it may carry a few extra day
    readings the published calendar omits, but it never omits one the calendar keeps
    (verified: GT is a subset of the output for every cached Apr-7 collision, 2001-2026)."""
    if (d.month, d.day) != (4, 7):
        return None
    proper = list(_ANNUNCIATION_PROPER)
    e_off = (d - calculate_gregorian_easter(d.year)).days
    day = _movable_slot_readings(d, tables) or []
    if e_off <= -9:
        # Deep Lent: an aliturgical WEEKDAY feria has no Liturgy readings, so the feast
        # proper stands alone. A Lenten SUNDAY (offset % 7 == 0) has a Divine Liturgy
        # whose readings co-celebrate -- do not suppress them.
        return (day + proper) if e_off % 7 == 0 else proper
    if e_off in _ANN_DAY_FIRST:
        return day + proper                             # day -> proper
    if e_off >= 1:
        # Eastertide. The digitized Tonatsooyts collision rubric (pp.486-488; auto-OCR
        # in grabar-ocr runs/auto__proj__trocr500__gemini-min page_0487) prescribes:
        # read the Annunciation Book+Gospel, then "the Gospel of the day"; and "in the
        # Midday and in the Evening the Psalm, Book, and Gospels are of the Resurrection"
        # -- i.e. the day keeps its own Eastertide readings. So the day's readings are
        # proper ++ the day's movable slot, and NOTHING is taken from the eve: Apr 6 (the
        # Nakhatonak pre-festive) is celebrated on Apr 6 alone. The one exception is the
        # Easter OCTAVE (e_off <= 8), where the octave repeats the feast-day resurrection
        # Gospel, so the eve's Gospel is co-read; outside the octave (e.g. 2027, where
        # Apr 7 = Easter+10) folding the eve Gospels in over-reads, so we drop them.
        if e_off <= 8:
            eve = _movable_slot_readings(d - datetime.timedelta(days=1), tables) or []
            extra = [r for r in eve if _classify_reading(r) == "Gospel"
                     and r not in day and r not in proper]
            return proper + day + extra
        return proper + day
    return proper + day                                 # proper -> day (Holy Week supreme days)


# --------------------------------------------------------------------------- #
# Presentation-eve (Feb 13) collision composite
#
# Feb 14 is the Presentation of the Lord (Tearnndaraj); its eve (Feb 13) co-celebrates
# the day's own base proper with a FIXED Presentation-eve block -- the Feb-14 feast
# readings, laid out in the Tōnats'oyts First Volume p.462, whose rubric there directs
# that when Feb 14 falls in the Fast of Catechumens / Great Lent the day's own Scriptures
# are read on Feb 13 at Midday and the eve service follows. The strict pipeline learns the
# cross-year-consistent buckets via the
# PrLE keyspace (civil date + Easter offset) and ships them VALIDATED. This composite
# is the BEST-GUESS fallback for the offsets PrLE cannot validate -- single-sample
# near-Easter years where Feb 13 lands on a coordinate seen in no other cache year.
# Like _annunciation_composite it composes deterministically and errs toward a
# SUPERSET (it never drops a reading GT keeps), so it is labeled best-guess, never
# validated.
# --------------------------------------------------------------------------- #

_PRESENTATION_EVE_BLOCK = (
    "Leviticus 12.6-8", "Proverbs 8.22-34", "Ezekiel 44.1-2", "Malachi 3.1-4",
    "St. Paul's Epistle to the Galatians 3.24-29", "Luke 2.22-40",
)


def _presentation_eve_composite(d, tables=None):
    """Best-guess Presentation-eve (Feb 13) readings via the co-celebration rule, for
    offsets the validated PrLE keyspace does not cover. Returns a list of refs, or None
    (None if the date is not Feb 13, or its movable base cannot be resolved).

    Base = the day's own movable/saint proper (the readings it would carry without the
    eve); the fixed Presentation-eve block is appended. The base resolves via the movable
    slot for a Sunday/ferial/saint the strict table already carries; when that is a
    single-sample coordinate it falls back to the pre-Lent cohort martyr co-celebrating
    the eve (Easter-offset-keyed). If neither resolves (an extreme-Easter movable Sunday
    the table cannot reach, e.g. the Easter-70 Fast-of-Catechumens eve) it returns None
    and the day stays an honest blank rather than shipping a subset."""
    if (d.month, d.day) != (2, 13):
        return None
    if tables is None:
        tables = _TABLES
    base = _movable_slot_readings(d, tables)
    if base is None:
        # A pre-Lent cohort martyr (Sargis/Atom/Sukias/Voskian/Ghevond) co-celebrating
        # the eve: its proper is Easter-offset-keyed (its movable slot is single-sample
        # here). Uses the source versification, which may differ from the cache by a
        # verse convention -- so this ships best-guess, not validated.
        e_off = (d - calculate_gregorian_easter(d.year)).days
        for _sid, off, _ms, _label, reads in _PRELENT_COHORT:
            if off == e_off:
                base = list(reads)
                break
    if base is None:
        # The Aṙajawor Barekendan (Feb 13 = Easter-70): its Sunday proper is the
        # First-Volume movable continua base (p.462), onto which the eve block appends.
        base = _first_volume_continua(d)
    if base is None:
        return None
    # Superset-safe append: keep GT order (base, then the eve block) without duplicating
    # a reading the base already carries.
    return list(base) + [r for r in _PRESENTATION_EVE_BLOCK if r not in base]


# --------------------------------------------------------------------------- #
# First-Volume movable ordinary-time continua (winter arc)
#
# The after-Theophany winter continua (Tōnats'oyts First Volume pp.457-460, reading
# 1-2 Timothy + John) and its line-75 bridge into the after-Vardavar continua (pp.517-519,
# reading 1 Corinthians + Matthew/Mark), plus the Aṙajawor Barekendan proper (p.462). These
# positions are reached only in the latest-Easter winters (2011, 2022), so they are
# single-sample in the 2001-2026 cache and the strict learner leaves them blank. The
# readings here are taken from the First Volume directly (source-confirmed byte-for-byte;
# see reports/blank_sourcing.md) and ship best-guess. Keyed by Easter offset -- the
# coordinate that fixes the position within the fixed-length (70-day) pre-Lent interval;
# offsets -79..-70 always fall in this Jan/Feb window. This is the interim "A" wiring: the
# general continua model (a dual-anchor walk of the source laydown that also covers the
# summer after-Transfiguration arc, e.g. 2008) is left to a later source-modeling pass.
# --------------------------------------------------------------------------- #

_FV_WINTER_CONTINUA = {
    # Easter offset -> First-Volume movable readings (verbatim, GT-format)
    -79: ["St. Paul's First Epistle to the Corinthians 5.9-6.10",     # p.518 (Friday)
          "Matthew 18.23-35"],
    -77: ["Isaiah 3.16-4.1",                                          # p.517 (2nd Sun. a. Vardavar)
          "St. Paul's First Epistle to the Corinthians 1.25-30",
          "Matthew 18.10-14"],
    -74: ["St. Paul's First Epistle to the Corinthians 7.25-35",      # p.519 (Wednesday)
          "Matthew 19.13-26"],
    -72: ["St. Paul's First Epistle to the Corinthians 11.1-16",      # p.519 (Friday; 2011+2022)
          "Mark 1.35-45"],
    -70: ["Isaiah 61.10-62.9",                                        # p.462 Aṙajawor Barekendan
          "St. Paul's Second Epistle to Timothy 2.15-26",
          "John 6.15-21"],
}


def _first_volume_continua(d):
    """Source-derived readings for a First-Volume movable ordinary-time day in the
    after-Theophany winter interval that the strict table leaves single-sample. Keyed by
    Easter offset (the fixed-length pre-Lent interval fixes the continua position). Returns
    a list of refs or None. Best-guess, never validated -- so it can never break the
    0-wrong contract."""
    # Only after the Nativity octave: in the earliest-Easter years the same offsets fall on
    # early-January feasts (e.g. offset -70 = Jan 13, the octave, when Easter is Mar 23),
    # which have their own resolvers -- the winter continua proper begins after the octave.
    if d <= datetime.date(d.year, 1, 13):
        return None
    e_off = (d - calculate_gregorian_easter(d.year)).days
    refs = _FV_WINTER_CONTINUA.get(e_off)
    return list(refs) if refs else None


# The summer counterpart: the after-Transfiguration Sundays reached as a blank only in the
# earliest-Easter years (Easter Mar 23 -> 2008), where the winter continua overflows its
# grid and the source bridges it forward onto the "Nth Sunday after Transfiguration" via the
# p.460/line-75 rubric (see reports/blank_sourcing.md lines 171-173). Normal-Easter years
# cover these offsets in the validated summer grid, so this tier is reached only when the
# strict table has no entry. Single-sample -> source-derived best-guess, byte-matching GT.
# Keyed by Easter offset -> (liturgical-day label, First-Volume movable readings, verbatim).
_FV_SUMMER_CONTINUA = {
    119: ("Fourth Sunday after Transfiguration",
          ["Luke 4.14-30", "Isaiah 54.1-13",
           "St. Paul's First Epistle to Timothy 1.1-11", "John 2.1-11"]),
    126: ("Fifth Sunday after Transfiguration",
          ["Isaiah 58.13-59.7",
           "St. Paul's First Epistle to Timothy 4.12-5.10", "John 3.13-21"]),
    133: ("Sixth Sunday after Transfiguration",
          ["Isaiah 62.1-11",
           "St. Paul's Second Epistle to Timothy 2.15-19", "John 6.39-47"]),
}


def _first_volume_summer_continua(d):
    """Source-derived readings for an after-Transfiguration summer Sunday the strict table
    leaves single-sample (only the earliest-Easter years reach these positions as a blank).
    Keyed by Easter offset. Returns (label, refs) or None. Best-guess, never validated."""
    entry = _FV_SUMMER_CONTINUA.get((d - calculate_gregorian_easter(d.year)).days)
    return (entry[0], list(entry[1])) if entry else None


def _fast_of_catechumens_eve(year: int) -> datetime.date:
    """Eve of the Fast of Catechumens (Aṙaǰawor) -- the Sunday at Easter-70 that opens
    the aliturgical fast week (Mon-Fri, Easter-69..-65) before Great Lent's Sunday."""
    return anchors(year)["E"] - datetime.timedelta(days=70)


def _john_forerunner_date(year: int) -> datetime.date:
    """Civil date the Nativity of John the Forerunner (nominal Jan 14) is actually
    celebrated. Besides the ordinary transfer off penitential weekdays (Wed/Fri/Sun),
    in an extreme-early-Easter year the Fast of Catechumens (Easter-70 eve) reaches
    back to Jan 14; the fast is aliturgical, so a Liturgy feast falling inside it is
    displaced to the first saint-weekday after the fast week (Tonats'oyts p. 464: the
    octave/fast boundary tracks Easter, so the fast can encroach on mid-January)."""
    jan14 = datetime.date(year, 1, 14)
    eve = _fast_of_catechumens_eve(year)
    fast_end = eve + datetime.timedelta(days=5)          # Friday of the fast week
    start = fast_end + datetime.timedelta(days=1) if eve < jan14 <= fast_end else jan14
    return _next_saint_weekday(start)


def _john_forerunner_composite(d, tables=None):
    """Nativity of John the Forerunner readings when its feast is transferred INTO an
    extreme-early-Easter January by the Fast of Catechumens encroachment (the winter
    grid's post-Nativity window is empty in that year, so its PnJohn slot never fires).
    Byte-exact: it ships the same cross-year-validated PnJohn proper on the transferred
    date. Returns the reading list or None."""
    if tables is None:
        tables = _TABLES
    jan14 = datetime.date(d.year, 1, 14)
    eve = _fast_of_catechumens_eve(d.year)
    fast_end = eve + datetime.timedelta(days=5)
    # Only fires in the encroachment year, where Jan 14 lands inside the aliturgical
    # fast week so the feast is displaced out of it; a normal year's Jan 14 is handled
    # by the winter grid and must be left untouched.
    if eve < jan14 <= fast_end and d == _john_forerunner_date(d.year):
        entry = tables.get("PnJohn", {}).get("John")
        if entry:
            return list(entry["readings"])
    return None


def _nativity_octave_readings(tables) -> list:
    """The eighth-day Nativity octave (Naming, Jan 13) proper (PnOct '01-13')."""
    entry = tables.get("PnOct", {}).get("01-13")
    return list(entry["readings"]) if entry else []


def _eve_of_fast_readings(tables) -> list:
    """The cross-year-validated Liturgy of the eve of the Fast of Catechumens, taken as
    the modal PnEveN reading-set (identical across the 2nd/3rd/4th-Sunday keys; the
    1st-Sunday key merely prepends an extra Luke 4.14-30, which we do not assume)."""
    from collections import Counter
    sets = [tuple(v["readings"]) for v in tables.get("PnEveN", {}).values()]
    if not sets:
        return []
    return list(Counter(sets).most_common(1)[0][0])


def _nativity_octave_composite(d, tables=None):
    """Best-guess Jan-13 readings for the extreme-early-Easter year where the octave of
    the Nativity (Naming, Jan 13) coincides with the eve of the Fast of Catechumens
    (Easter-70). Both feasts are celebrated with Liturgy (Tonats'oyts p. 464: the octave
    is kept 'with services and Liturgy' even as it encroaches on the fast), so the day
    is a co-celebration. The flat slots carry no Matins/Liturgy structure, so which part
    of each proper the printed calendar reduces is not derivable; like the Annunciation
    composite this errs toward a SUPERSET (octave proper ++ eve Liturgy) that never drops
    a reading the calendar keeps -- verified GT is a subset for the one cached collision
    (2008). Returns the reading list or None (None unless Jan 13 at Easter-70)."""
    if tables is None:
        tables = _TABLES
    if (d.month, d.day) != (1, 13):
        return None
    if (d - anchors(d.year)["E"]).days != -70:
        return None
    octave = _nativity_octave_readings(tables)
    eve = _eve_of_fast_readings(tables)
    return octave + [r for r in eve if r not in octave]


# --------------------------------------------------------------------------- #
# Pre-Lent martyr cohort (Sargis / Atom / Sukias / Voskian / Ghevond)
#
# Five fixed martyr feasts laid in the pre-Lent gap between the Fast of Catechumens
# and the Great Barekendan. Their propers are recorded in the Tōnats'oyts FIRST VOLUME
# (pp.464-465, right after the Nativity-octave rubric); the per-taregir Second Volume
# only names the feast + hymn tone and cross-refers "see the First Volume up to Vardavar,
# keeping the order of this place." So these readings are source-derived, not cache-fit.
# The verse ranges follow the source; the sacredtradition cache uses a slightly different
# Wisdom-of-Solomon numbering / Gospel endpoint convention on four of them, reconciled by
# dev/source_corrections.py (reviewed). See docs/sources/tonatsooyts-prelent-cohort.md.
#
# The feasts sit at fixed Easter offsets (all determined by Easter, which fixes their
# weekday too): Sargis -64 (Sat), Atom -62 (Mon), Sukias -61 (Tue), Voskian -59 (Thu),
# Ghevond -54 (Tue). When a higher feast occupies a slot -- the transferred John the
# Forerunner on Sargis's Saturday (extreme-early Easter), or the Presentation of the Lord
# (Feb 14) on a cohort weekday -- the senior "Generals" (Sargis, Atom) shift forward onto
# the next cohort slot and win the merge; the junior martyrs/priests are absorbed. On the
# embedded Presentation-eve (Feb 13) the feast co-celebrates via the embedded composite, so
# the cohort abstains there. This layout is drop-guard-validated 0-wrong over 2001-2026.
# --------------------------------------------------------------------------- #

_PRELENT_COHORT = (
    # (id, easter_offset, may_shift, label, source readings)
    ("sargis", -64, True,
     "Saint Sargis the Warrior and his son Martiros and his Fourteen Soldiers",
     ["Proverbs 3.13-17", "Isaiah 41.1-3",
      "St. Paul's Epistle to the Ephesians 6.10-17", "Luke 21.10-19"]),
    ("atom", -62, True,
     "Saints Atom and his soldiers",
     ["Wisdom 6.12-21", "Isaiah 18.7-19.7",
      "St. Paul's Second Epistle to the Corinthians 4.10-5.5", "John 16.1-5"]),
    ("sukias", -61, False,
     "Saints Sukiasians the Martyrs",
     ["Proverbs 22.1-12", "Isaiah 56.6-7",
      "St. Paul's Epistle to the Hebrews 11.32-40", "Luke 12.4-8"]),
    ("voskian", -59, False,
     "Saints Voskians the Priests",
     ["Proverbs 24.1-12", "Jeremiah 30.18-22",
      "St. Paul's Second Epistle to Timothy 3.10-12", "Matthew 5.1-12"]),
    ("ghevond", -54, False,
     "Saints Ghevond the Priest and His Companions",
     ["Wisdom 5.16-23", "Isaiah 35.1-2", "Isaiah 61.6-7",
      "St. Peter's First Epistle General 1.3-9", "Luke 12.4-10"]),
)
_PRELENT_OFFSETS = frozenset(off for _, off, _, _, _ in _PRELENT_COHORT)


@functools.lru_cache(maxsize=None)
def _prelent_cohort_layout(year):
    """Map {date: (id, label, readings)} for the pre-Lent cohort in ``year``.

    Feasts are laid at their fixed Easter offsets. A feast whose slot is taken by a
    higher feast (the transferred John the Forerunner, or the Feb-14 Presentation) is
    handled per rank: the senior Generals (Sargis/Atom) shift to the next cohort slot and
    win the merge (senior placed first via setdefault); the juniors abstain. The embedded
    Presentation-eve (Feb 13) is left to the embedded composite."""
    e = calculate_gregorian_easter(year)
    blocked = {_john_forerunner_date(year), datetime.date(year, 2, 14)}
    layout = {}
    for sid, off, may_shift, label, reads in _PRELENT_COHORT:
        d = e + datetime.timedelta(days=off)
        if (d.month, d.day) in EMBEDDED_FIXED:
            continue                                    # co-celebrates via embedded composite
        if d in blocked:
            if not may_shift:
                continue                                # junior feast: absorbed, abstain
            d2 = d + datetime.timedelta(days=1)
            while (d2.weekday() not in _SAINT_WD or d2 in blocked
                   or (d2.month, d2.day) in EMBEDDED_FIXED):
                d2 += datetime.timedelta(days=1)
            if (d2 - e).days not in _PRELENT_OFFSETS:
                continue                                # shifted off the cohort entirely
            d = d2
        layout.setdefault(d, (sid, label, reads))       # senior placed first wins a merge
    return layout


def _prelent_cohort(d):
    """Source-derived pre-Lent cohort feast for ``d``: (id, label, readings) or None."""
    return _prelent_cohort_layout(d.year).get(d)


# Date windows (days relative to anchor) where each keyspace may apply, to keep
# far-away dates from matching an anchor by coincidence. Winter keyspaces use
# string grid keys and are self-guarded (only emitted inside their window), so
# they carry no numeric guard (None).
WINDOWS = {
    "C": None,
    "CF": None,
    "AnnE": None,
    "PrLE": None,
    "EB": None,
    "E": (-72, 116),
    "AS": (-14, 27),
    "EX": (-9, 60),
    "HEB": None,
    "HEpB": None,
    "HE": (0, 60),
    "HEp": (40, 75),
    "TH": (-46, 40),
    "THp": (320, 380),
}
WINDOWS.update({ks: None for ks in WINTER_KS})
WINDOWS.update({ks: None for ks in HINGE_KS})

# Resolution precedence (first match wins): immovable feasts, then the
# solar/Easter anchored cycles, then the winter grid slots, then the generic
# Theophany/Heesnak season counts.
PRECEDENCE = (["C", "CF", "AnnE", "PrLE", "EB", "E"] + WINTER_KS + HINGE_KS
              + ["AS", "EX", "HEB", "HE", "HEpB", "HEp", "TH", "THp"])

# Keyspaces whose keys are integers (day-offsets); all others are string keys.
INT_KEYSPACES = {"E", "AS", "EX", "HE", "HEp", "TH", "THp"}

# Human-readable season label per keyspace, refined by offset for the Easter core.
_KS_SEASON = {
    "C": "Immovable Feast",
    "CF": "Feast",
    "AnnE": "Annunciation",
    "PrLE": "Eve of the Presentation of the Lord",
    "AS": "Assumption Cycle",
    "EX": "Exaltation of the Cross Cycle",
    "HE": "Advent (Heesnak)",
    "HEp": "Advent (Heesnak)",
    "TH": "Season after Nativity",
    "THp": "Advent / Nativity Fast",
    # Winter grid slots:
    "AdvSun": "Advent (Heesnak)",
    "AdvSunL": "Advent (Heesnak)",
    "AdvSunB": "Advent (Heesnak)",
    "AoF": "Fast of Advent",
    "AdvFer": "Advent (Heesnak)",
    "AdvFerL": "Advent (Heesnak)",
    "AdvFerB": "Advent (Heesnak)",
    "AdvSat": "Advent (Heesnak)",
    "AdvSatB": "Advent (Heesnak)",
    "AdvSatL": "Advent (Heesnak)",
    "AdvSatBL": "Advent (Heesnak)",
    "PnOct": "Feast of the Naming of the Lord",
    "PnJohn": "Season after Nativity",
    "PnSaint": "Season after Nativity",
    "PnSaintB": "Season after Nativity",
    "PnSaintMD": "Season after Nativity",
    "PnEveN": "Eve of the Fast of Catechumens",
    "PnEve": "Eve of the Fast of Catechumens",
    "PnSun": "Season after Nativity",
    "PnSunL": "Season after Nativity",
    "PnSunB": "Season after Nativity",
    "PnFer": "Season after Nativity",
    "PnFerF": "Season after Nativity",
    "PnFerL": "Season after Nativity",
    "PnFerB": "Season after Nativity",
    "PnSat": "Season after Nativity",
    "PnSatL": "Season after Nativity",
    "PnSatBL": "Season after Nativity",
    "PnSatB": "Season after Nativity",
    # Summer/autumn hinge slots:
    "TrEve": "Eve of the Fast of the Assumption",
    "AsEve": "Eve of the Fast of the Holy Cross",
}
_KS_SEASON.update({ks: "After Transfiguration"
                   for ks in ("TrSun", "TrSunL", "TrFer", "TrFerL", "TrSaintMD",
                              "TrSaintB", "TrSaint", "TrSat", "TrSatL", "TrSatB",
                              "TrSatBL")})
_KS_SEASON.update({ks: "After the Assumption"
                   for ks in ("AsSun", "AsSunL", "AsFer", "AsFerL", "AsSaintMD",
                              "AsSaintB", "AsSaint", "AsSatMD", "AsSat", "AsSatL",
                              "AsSatB", "AsSatBL")})
_KS_SEASON.update({ks: "After the Exaltation of the Cross"
                   for ks in ("ExSun", "ExSunL", "ExFer", "ExFerL", "ExSaintMD",
                              "ExSaintB", "ExSaint", "ExSatMD", "ExSat", "ExSatL",
                              "ExSatB", "ExSatBL")})


def _easter_season(offset: int) -> str:
    if offset <= -64:
        return "Pre-Lent"
    if -63 <= offset <= -50:
        return "Pre-Lenten Fast"
    if -49 <= offset <= -8:
        return "Great Lent"
    if -7 <= offset <= -1:
        return "Holy Week"
    if offset == 0:
        return "Easter"
    if 1 <= offset <= 49:
        return "Eastertide (Hinank)"
    if 50 <= offset <= 97:
        return "After Pentecost"
    return "After Transfiguration"


def season_for(keyspace: str, key) -> str:
    if keyspace == "E":
        return _easter_season(key)
    if keyspace == "EB":                        # "band:offset" -> Easter season
        return _easter_season(int(str(key).split(":")[1]))
    if keyspace in ("HEB", "HEpB"):
        return "Advent (Heesnak)"
    return _KS_SEASON.get(keyspace, "Ordinary Time")


# --------------------------------------------------------------------------- #
# Embedded validated table
# --------------------------------------------------------------------------- #

def _load_table():
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    tables = raw.get("tables", {})
    # JSON object keys are strings; integer-keyed keyspaces need int keys, while
    # civil-date and winter-grid keyspaces stay string-keyed.
    out = {}
    for ks, entries in tables.items():
        if ks in INT_KEYSPACES:
            out[ks] = {int(k): v for k, v in entries.items()}
        else:
            out[ks] = entries
    return out


_TABLES = _load_table()


def _lookup(d: datetime.date, tables=None):
    if tables is None:
        tables = _TABLES
    cs = coords_for(d)
    for ks in PRECEDENCE:
        if ks not in tables:
            continue
        if ks == "C":
            m, dd = cs["C"]
            key = f"{m:02d}-{dd:02d}"
        else:
            if ks not in cs:           # winter keyspace not applicable to this date
                continue
            key = cs[ks]
            win = WINDOWS[ks]
            if win is not None and not (win[0] <= key <= win[1]):
                continue
        entry = tables[ks].get(key)
        if entry:
            return ks, key, entry
    return None, None, None


# --------------------------------------------------------------------------- #
# Reading classification (for presentation)
# --------------------------------------------------------------------------- #

_OT_BOOKS = (
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "Samuel", "Kings", "Chronicles", "Ezra", "Nehemiah",
    "Job", "Psalm", "Proverbs", "Ecclesiastes", "Song", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah",
    "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
    "Malachi", "Wisdom", "Baruch", "Sirach", "Maccabees", "Azariah", "Esther",
    "Tobit", "Judith", "Zachariah",
)
_GOSPELS = ("Matthew", "Mark", "Luke", "John")


def _classify_reading(ref: str) -> str:
    head = ref.strip()
    # Drop a leading book number (e.g. "2 Kings", "1 Samuel") for matching.
    bare = head
    if len(bare) > 2 and bare[0].isdigit() and bare[1] == " ":
        bare = bare[2:]
    if bare.startswith(_GOSPELS) and "Epistle" not in head:
        return "Gospel"
    if "Epistle" in head or "Acts of the Apostles" in head or bare.startswith(
            ("Acts", "Revelation", "James", "Jude")):
        return "Epistle"
    if bare.startswith(_OT_BOOKS):
        return "Old Testament"
    return "Other"


def _group_readings(refs: list) -> dict:
    grouped = {}
    for ref in refs:
        grouped.setdefault(_classify_reading(ref), []).append(ref)
    # Stable, liturgical order.
    order = ["Old Testament", "Epistle", "Gospel", "Other"]
    return {k: grouped[k] for k in order if k in grouped}


# --------------------------------------------------------------------------- #
# Localization (English -> Armenian names)
# --------------------------------------------------------------------------- #

def _load_json_map(path):
    """Load a {str: str} name map, degrading to {} if the file is absent."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


_FEAST_NAMES_HY = _load_json_map(FEAST_NAMES_HY_PATH)
_BOOK_NAMES_HY = _load_json_map(BOOK_NAMES_HY_PATH)

# Split a reading citation into (book head, "chapter.verse" tail). The tail is
# language-independent, so translating a reading is just swapping the head.
_READING_SPLIT_RE = re.compile(r"^(.*?)(\d+[.:]\d.*)$")


def _translate_reading(ref: str, book_map: dict) -> str:
    """Return ``ref`` with its book name in the target language (unchanged if the
    book head is not in ``book_map`` or the ref carries no chapter.verse tail)."""
    m = _READING_SPLIT_RE.match(ref.strip())
    if not m:
        return ref
    head, tail = m.group(1).strip(), m.group(2).strip()
    hy = book_map.get(head)
    return f"{hy} {tail}" if hy else ref


def _translate_feast(label: str, feast_map: dict) -> str:
    """Return ``label`` (a possibly FEAST_SEP-composite feast name) in the target
    language. Try the whole string first; else translate each component individually,
    leaving any component with no known translation in English."""
    if not label:
        return label
    whole = feast_map.get(label)
    if whole is not None:
        return whole
    parts = label.split(_FEAST_SEP)
    if len(parts) > 1:
        return _FEAST_SEP.join(feast_map.get(p, p) for p in parts)
    return label


def _localize(result: dict, language: str) -> dict:
    """Translate the human-readable feast and reading names of ``result`` in place.

    Only the *scraped* values are localized -- the feast (``Liturgical Day``) and the
    book names inside ``Readings``/``ReadingsList``. Provenance/metadata fields
    (``Season``, ``Source``, ``Confidence``, ``Note``) stay in English; they are engine
    annotations, not source data, and have no scraped Armenian form. The result always
    carries a ``Language`` key naming the language its names are in.
    """
    result["Language"] = language
    if language == "en":
        return result
    result["Liturgical Day"] = _translate_feast(
        result.get("Liturgical Day", ""), _FEAST_NAMES_HY)
    result["ReadingsList"] = [
        _translate_reading(r, _BOOK_NAMES_HY) for r in result.get("ReadingsList", [])]
    # Translate within the existing groups: the OT/Epistle/Gospel classification was
    # already computed on the English heads in _group_readings, so we keep that grouping
    # and only localize each reading's text (the section keys stay English metadata).
    result["Readings"] = {
        section: [_translate_reading(r, _BOOK_NAMES_HY) for r in refs]
        for section, refs in result.get("Readings", {}).items()
    }
    return result


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

# The Remembrance of the Armenian Genocide (1915) is a fixed CIVIL-date
# commemoration kept on April 24. The cross-year-validated table keys days by their
# *liturgical* (Easter-offset) coordinate, so a genocide note baked into one key's
# label floats onto whatever civil date that coordinate hits in another year. Re-anchor
# it to April 24: strip it wherever it was baked, and append it iff the date is Apr 24.
_GENOCIDE_REMEMBRANCE = "Remembrance of the Armenian Genocide (1915)"


def _anchor_genocide_remembrance(label: str, d: datetime.date) -> str:
    """Return ``label`` with the Genocide Remembrance note anchored to April 24.

    The note is a distinct ``_FEAST_SEP``-delimited component; drop it wherever the
    Easter-keyed table baked it (it floats off April 24 in other years) and re-append it
    only on April 24."""
    parts = [p for p in label.split(_FEAST_SEP) if p != _GENOCIDE_REMEMBRANCE]
    if (d.month, d.day) == (4, 24):
        parts.append(_GENOCIDE_REMEMBRANCE)
    return _FEAST_SEP.join(parts)


def compute_armenian_lectionary(target_date: datetime.date,
                                language: str = "en") -> dict:
    """Return the liturgical day and readings for ``target_date``.

    Thin wrapper over :func:`_compute_lectionary` that re-anchors fixed civil-date
    commemorations (Genocide Remembrance -> April 24) which the Easter-keyed table
    would otherwise misplace.

    ``language`` selects the language of the human-readable names: ``"en"`` (default)
    or ``"hy"`` for Classical Armenian. In ``"hy"`` the feast (``Liturgical Day``) and
    the book names in ``Readings``/``ReadingsList`` come from sacredtradition.am
    (scraped offline into ``data/{feast,book}_names_hy.json``); any name with no known
    Armenian form is left in English. Provenance fields stay English (see
    :func:`_localize`).
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"unsupported language {language!r}; expected one of "
            f"{', '.join(SUPPORTED_LANGUAGES)}")
    result = _compute_lectionary(target_date)
    result["Liturgical Day"] = _anchor_genocide_remembrance(
        result["Liturgical Day"], target_date)
    return _localize(result, language)


def _compute_lectionary(target_date: datetime.date) -> dict:
    """Resolve the liturgical day and readings for ``target_date`` (pre-overlay)."""
    # Pre-Lent martyr cohort (Sargis/Atom/Sukias/Voskian/Ghevond): readings taken
    # directly from the Tōnats'oyts First Volume pp.464-465 (source-derived, verse ranges
    # per the source), placed by the fixed-Easter-offset laydown with rank-based
    # displacement. Checked first so the source proper is served consistently -- including
    # forward years with no cache -- rather than the cache-built table entry.
    pc = _prelent_cohort(target_date)
    if pc is not None:
        _sid, label, refs = pc
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": label,
            "Season": "Pre-Lent",
            "Readings": _group_readings(refs),
            "ReadingsList": refs,
            "Source": "first-volume-cohort",
            "Note": ("Readings from the Tōnats'oyts First Volume (pp.464-465); the "
                     "Second Volume names this feast per year-type and defers its "
                     "readings there. Verse ranges follow the source (a few differ from "
                     "sacredtradition.am by a versification convention; see "
                     "dev/source_corrections.py)."),
        }

    ks, key, entry = _lookup(target_date)
    if entry is not None:
        refs = entry["readings"]
        result = {
            "Date": target_date.isoformat(),
            "Liturgical Day": entry["feast"] or "(commemoration)",
            "Season": season_for(ks, key),
            "Readings": _group_readings(refs),
            "ReadingsList": refs,
            "Source": "validated-table",
        }
        if not refs:
            # A validated *aliturgical* day: the ground truth appoints no scripture
            # readings (the ferial Mon-Thu of the Fast of the Catechumens -- kept as a
            # penitential fast without a Divine Liturgy). The empty reading set is a
            # validated fact, not an unresolved gap, so flag it explicitly: consumers
            # must not read the emptiness as missing/not-yet-modeled data.
            result["Confidence"] = "validated"
            result["Note"] = ("No scripture readings are appointed for this day; it is "
                              "kept as a penitential fast without a Divine Liturgy (an "
                              "aliturgical day -- the ferial days of the Fast of the "
                              "Catechumens). The empty reading set is intentional and "
                              "validated against the Tōnats'oyts, not missing data.")
        return result

    # Embedded fixed-feast composite (proper readings combined with the movable
    # slot the feast lands on). Deterministic and validated; ships as a feast.
    if (target_date.month, target_date.day) in EMBEDDED_PROPER:
        refs = _embedded_composite(target_date, _TABLES)
        if refs is not None:
            feast = _EMBEDDED_FEAST.get((target_date.month, target_date.day),
                                        "Feast")
            return {
                "Date": target_date.isoformat(),
                "Liturgical Day": feast,
                "Season": "Feast",
                "Readings": _group_readings(refs),
                "ReadingsList": refs,
                "Source": "validated-composite",
            }

    # Second-Volume cycle tier: for a floating saint-weekday, read the authoritative
    # saint from the Tonatsoyts Second Volume calendar of this year's year-type
    # (selected by Gregorian Easter date) and ship that identity's readings. Directory-
    # derived and deterministic; it sits ABOVE the generative laydown because it is
    # correct where the laydown is systematically wrong (see docs/sources/
    # second_volume_index.md). Distinct Source so a consumer can still gate on it.
    cy = _cycle_saint(target_date)
    if cy is not None:
        zone, sid, label, refs = cy
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": label or "(commemoration)",
            "Season": season_for(zone + "Saint", sid),
            "Readings": _group_readings(refs),
            "ReadingsList": refs,
            "Source": "second-volume-cycle",
            "Confidence": "source-derived",
            "Note": ("Saint resolved from the Tonatsoyts Second Volume per-year-type "
                     "calendar (matched by this year's Easter date); readings are that "
                     "saint's proper. Source-derived, not cross-year cache-validated."),
        }

    # Generative best-guess tier (labeled, NEVER validated): a saint-weekday the
    # strict table can't cover (single-sample extreme-Easter year / floating
    # summer saint). The full laydown places the canonical saint and we ship its
    # intrinsic readings. Deterministic and offline, but unvalidated cross-year,
    # so it is tagged distinctly and a consumer can filter it out.
    gs = _generative_saint(target_date)
    if gs is not None:
        zone, sid, label, refs = gs
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": label or "(commemoration)",
            "Season": season_for(zone + "Saint", sid),
            "Readings": _group_readings(refs),
            "ReadingsList": refs,
            "Source": "generative-saint",
            "Confidence": "best-guess",
            "Note": ("Best-guess readings from the canonical saint laydown; not "
                     "cross-year validated (this saint-weekday is under-sampled "
                     "in the reference data). Filter on Source/Confidence if you "
                     "need only provably-validated readings."),
        }

    # Generative continua best-guess: the Fast-of-the-Assumption Wed/Fri continua
    # tail (a window no grid slot covers, whose deep positions carry long-summer
    # variants the strict filter cannot ship). Labeled, never validated.
    gc = _generative_continua(target_date)
    if gc is not None:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Fast day",
            "Season": "Fast of the Assumption",
            "Readings": _group_readings(gc),
            "ReadingsList": gc,
            "Source": "generative-continua",
            "Confidence": "best-guess",
            "Note": ("Best-guess readings from the Fast-of-the-Assumption "
                     "lectio-continua (modal reading for this fast-day position); "
                     "not cross-year validated. Filter on Source/Confidence if "
                     "you need only provably-validated readings."),
        }

    # Annunciation (Apr 7) collision composite best-guess: the validated AnnE
    # keyspace had no entry for this year's Easter offset (a single-sample or unseen
    # collision). The Tonatsooyts canon (pp. 486-488) prescribes the readings
    # deterministically by combining the fixed proper with the movable day it lands
    # on; we ship that, labeled best-guess. See _annunciation_composite.
    ac = _annunciation_composite(target_date)
    if ac is not None:
        # Name the day the way the source does: the movable Lent/Holy-Week/Eastertide day
        # it collides with, plus the Annunciation. In Lent/Holy Week the movable day
        # outranks and leads; in Eastertide the Annunciation leads.
        _annun = "Annunciation to the Virgin Mary"
        _base = _collision_base_feast(target_date) or ""
        _e_off = (target_date - calculate_gregorian_easter(target_date.year)).days
        if not _base:
            _name = _annun
        elif _e_off >= 1:
            # Eastertide: the Annunciation leads the commemorations, but the calendar
            # day-count stays at the front -- position, then Annunciation, then any saint.
            _parts = _base.split(_FEAST_SEP)
            _name = _FEAST_SEP.join([_parts[0], _annun] + _parts[1:])
        else:
            _name = _base + _FEAST_SEP + _annun   # Lent/Holy Week: the movable day leads
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": _name,
            "Season": "Annunciation",
            "Readings": _group_readings(ac),
            "ReadingsList": ac,
            "Source": "generative-composite",
            "Confidence": "best-guess",
            "Note": ("Best-guess readings from the Annunciation collision rule "
                     "(Tonatsooyts pp. 486-488): the fixed Annunciation proper "
                     "combined with the movable Lent/Holy-Week/Eastertide day it "
                     "falls on, ordered by that day's rank. The reading order is "
                     "rubric-deterministic but the day-portion may be liturgically "
                     "reduced, so this is not cross-year validated. Filter on "
                     "Source/Confidence if you need only validated readings."),
        }

    # Presentation-eve (Feb 13) collision composite best-guess: the validated PrLE
    # keyspace had no entry for this year's Easter offset (a single-sample near-Easter
    # year). Compose the day's base proper with the fixed Presentation-eve block
    # (Tonats'oyts First Vol p.464/467); labeled best-guess. See _presentation_eve_composite.
    pe = _presentation_eve_composite(target_date)
    if pe is not None:
        # Name the day by its movable/base commemoration (the pre-Lent cohort martyr, or
        # the Lenten day it falls on) the way the source does -- the Presentation eve is
        # a co-celebrated reading block, not the day's headline. Fall back to the eve name
        # only when no base commemoration resolves (an extreme-Easter ferial).
        _name = _collision_base_feast(target_date) or "Eve of the Presentation of the Lord"
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": _name,
            "Season": "Presentation",
            "Readings": _group_readings(pe),
            "ReadingsList": pe,
            "Source": "generative-composite",
            "Confidence": "best-guess",
            "Note": ("Best-guess readings for the eve of the Presentation of the Lord "
                     "(Feb 14): the day's own base proper combined with the fixed "
                     "Presentation-eve block (Tonats'oyts First Vol p.462). This "
                     "year's Easter offset is single-sample, so the strict PrLE keyspace "
                     "could not validate it; the composite errs toward a superset and is "
                     "not cross-year validated. Filter on Source/Confidence if you need "
                     "only validated readings."),
        }

    # First-Volume movable ordinary-time continua (winter arc): a single-sample
    # after-Theophany day (latest-Easter winters 2011/2022) the strict table can't cover.
    # Source-derived from the First Volume (pp.458-460/462/517-519); best-guess, never
    # validated. See _first_volume_continua.
    fv = _first_volume_continua(target_date)
    if fv is not None:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "(movable ordinary-time reading)",
            "Season": "After Theophany",
            "Readings": _group_readings(fv),
            "ReadingsList": fv,
            "Source": "first-volume-continua",
            "Confidence": "best-guess",
            "Note": ("Source-derived readings from the Tōnats'oyts First-Volume movable "
                     "ordinary-time continua (after-Theophany winter arc, pp.458-460, with "
                     "the p.460 bridge into the after-Vardavar continua pp.517-519). This "
                     "position is reached only in the latest-Easter winters, so it is "
                     "single-sample in the cache and not cross-year validated; the readings "
                     "are taken from the source directly. Filter on Source/Confidence if "
                     "you need only validated readings."),
        }

    # First-Volume movable ordinary-time continua (summer arc): the after-Transfiguration
    # Sundays reached as a blank only in the earliest-Easter years (2008). Source-derived
    # from the First Volume (winter 1-2 Timothy + John continua bridged forward per the
    # p.460/line-75 rubric); best-guess, never validated. See _first_volume_summer_continua.
    sv = _first_volume_summer_continua(target_date)
    if sv is not None:
        label, refs = sv
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": label,
            "Season": "After Transfiguration",
            "Readings": _group_readings(refs),
            "ReadingsList": refs,
            "Source": "first-volume-continua",
            "Confidence": "best-guess",
            "Note": ("Source-derived readings from the Tōnats'oyts First-Volume movable "
                     "ordinary-time continua (after-Transfiguration summer arc: the winter "
                     "1-2 Timothy + John continua bridged forward per the p.460/line-75 "
                     "rubric, pp.458-460). This position is reached only in the earliest-"
                     "Easter years (e.g. 2008), so it is single-sample in the cache and not "
                     "cross-year validated; the readings are taken from the source directly "
                     "and byte-match the ground truth. Filter on Source/Confidence if you "
                     "need only validated readings."),
        }

    # John the Forerunner (Jan 14) transferred into an extreme-early-Easter January by
    # the Fast of Catechumens encroachment: the winter grid's post-Nativity window is
    # empty that year, so its PnJohn slot never fires. Ship the same validated PnJohn
    # proper on the transferred date -- byte-exact, calendar-derived. See p. 464.
    jf = _john_forerunner_composite(target_date)
    if jf is not None:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Feast of the Birth of St. John the Forerunner (Baptist)",
            "Season": "Nativity Octave",
            "Readings": _group_readings(jf),
            "ReadingsList": jf,
            "Source": "validated-composite",
            "Note": ("Nativity of John the Forerunner (nominal Jan 14) transferred to "
                     "this saint-weekday because the Fast of Catechumens (Easter-70) "
                     "reaches Jan 14 in this extreme-early-Easter year; readings are the "
                     "cross-year-validated PnJohn proper (Tonats'oyts p. 464)."),
        }

    # Nativity octave (Jan 13) co-celebrating with the eve of the Fast of Catechumens
    # in an extreme-early-Easter year (Easter-70 falls on Jan 13). Best-guess superset
    # (never drops a GT reading); labeled generative, never validated.
    no = _nativity_octave_composite(target_date)
    if no is not None:
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": "Feast of Naming of Our Lord Jesus Christ",
            "Season": "Nativity Octave",
            "Readings": _group_readings(no),
            "ReadingsList": no,
            "Source": "generative-composite",
            "Confidence": "best-guess",
            "Note": ("Best-guess readings: in this extreme-early-Easter year the eighth-"
                     "day Nativity octave (Jan 13) coincides with the eve of the Fast of "
                     "Catechumens (Easter-70) and both are celebrated with Liturgy "
                     "(Tonats'oyts p. 464). The octave proper is combined with the eve's "
                     "validated Liturgy; the flat slots carry no Matins/Liturgy structure "
                     "so this errs toward a superset and is not cross-year validated. "
                     "Filter on Source/Confidence if you need only validated readings."),
        }

    # Fallback: no validated entry (chiefly the winter hinge). Name the season
    # algorithmically and flag the readings as not-yet-modeled.
    cs = coords_for(target_date)
    # Pick an in-window keyspace for a season label. Winter grid slots come first
    # (they carry the right Advent / after-Nativity label even when their
    # readings are withheld), then the Easter core, then the season counts.
    season = "Ordinary Time"
    for kspace in (["CF"] + WINTER_KS + HINGE_KS
                   + ["E", "AS", "EX", "TH", "HE", "HEp", "THp"]):
        if kspace not in cs:
            continue
        win = WINDOWS[kspace]
        if win is None or win[0] <= cs[kspace] <= win[1]:
            season = season_for(kspace, cs[kspace])
            break
    return {
        "Date": target_date.isoformat(),
        "Liturgical Day": f"{season} (day not yet in validated table)",
        "Season": season,
        "Readings": {},
        "ReadingsList": [],
        "Source": "algorithmic-estimate",
        "Note": ("This day falls in the winter ferial zone whose ordered "
                 "saint/fast tracks are not yet modeled; readings unavailable."),
    }


if __name__ == "__main__":
    from .cli import main
    main()
