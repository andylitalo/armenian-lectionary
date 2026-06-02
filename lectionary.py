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

import datetime
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "lectionary_data.json")


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

# Embedded fixed-date Marian feasts that float across the winter weekdays. Their
# readings entangle with whatever ferial/Sunday slot they land on (so they can't
# be shipped as a clean civil feast), but they MUST be excluded from the grid so
# they don't pollute the fast/saint slots they happen to overlap.
_EMBEDDED_FIXED = {(11, 21), (12, 9)}   # Presentation of Mary; Conception of Mary


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


def _advent_slot(d, he, out):
    """Stable winter coordinates for an Advent day (he < d <= Jan 5)."""
    wd = d.weekday()
    days_from_he = (d - he).days          # >= 1
    week = days_from_he // 7              # week 0 == the opening Fast-of-Advent week
    nat = datetime.date(he.year + 1, 1, 6)
    if wd == 6:                           # numbered Sunday of Advent
        out["AdvSun"] = str(days_from_he // 7)
        return
    if week == 0 and wd in (0, 1, 2, 3, 4):   # opening Fast of Advent (Mon-Fri)
        out["AoF"] = str(days_from_he)
        return
    if wd in (2, 4):                      # ferial Wed/Fri fast (lectio continua)
        s1 = he + datetime.timedelta(days=7)   # 1st Sunday of Advent
        out["AdvFer"] = str(_count_wf(s1, d))
        return
    # saint weekday (Mon/Tue/Thu/Sat): forward grid + backward grid
    out["AdvSat"] = f"{week}:{_WD[wd]}"
    out["AdvSatB"] = f"{(nat - d).days // 7}:{_WD[wd]}"


def _postnat_slot(d, start, end, out):
    """Stable winter coordinates for a post-Nativity day (Jan 14 .. eve of Fast)."""
    wd = d.weekday()
    nsun = sum(1 for k in range((d - start).days + 1)
               if (start + datetime.timedelta(days=k)).weekday() == 6)
    # John the Forerunner: Jan 14, transferred to the next saint weekday when
    # Jan 14 is penitential (Wed/Fri) or a Sunday.
    john = _next_saint_weekday(datetime.date(d.year, 1, 14))
    if d == john:
        out["PnJohn"] = "John"
        return
    if wd == 6:
        if d == end:
            out["PnEve"] = "0"            # eve of Fast of Catechumens (backward)
        else:
            out["PnSun"] = str(nsun)      # numbered Sunday after Nativity
        return
    if wd in (2, 4):                      # ferial Wed/Fri
        out["PnFer"] = f"{nsun}:{_WD[wd]}"
        return
    # saint weekday: forward grid (week-from-Nativity). The post-Nativity window
    # length swings from 1 to 4 weeks, so a backward saint grid never stabilises;
    # only the forward grid is registered here.
    out["PnSat"] = f"{nsun}:{_WD[wd]}"


def winter_coords(d: datetime.date) -> dict:
    """Winter-zone slot coordinates for a date (empty if outside both windows)."""
    out = {}
    if (d.month, d.day) in _EMBEDDED_FIXED:
        return out                        # don't let floating feasts pollute the grid
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


# Winter keyspaces, most specific first (forward grids before backward grids).
WINTER_KS = ["PnJohn", "PnEve", "AdvSun", "PnSun", "AoF", "AdvFer", "PnFer",
             "AdvSat", "PnSat", "AdvSatB"]


def coords_for(d: datetime.date) -> dict:
    """All candidate (keyspace -> key) liturgical coordinates for a date."""
    y = d.year
    a = anchors(y)
    a_prev = anchors(y - 1)
    cs = {
        "C": (d.month, d.day),                  # civil date (immovable feasts)
        "E": (d - a["E"]).days,                 # Easter-anchored core
        "AS": (d - a["AS"]).days,               # Assumption period
        "EX": (d - a["EX"]).days,               # Exaltation period
        "HE": (d - a["HE"]).days,               # Advent (this year)
        "HEp": (d - a_prev["HE"]).days,         # Advent tail into early January
        "TH": (d - a["TH"]).days,               # weeks after Nativity
        "THp": (d - a_prev["TH"]).days,
    }
    cs.update(winter_coords(d))                 # winter grid slots (string keys)
    return cs


# Date windows (days relative to anchor) where each keyspace may apply, to keep
# far-away dates from matching an anchor by coincidence. Winter keyspaces use
# string grid keys and are self-guarded (only emitted inside their window), so
# they carry no numeric guard (None).
WINDOWS = {
    "C": None,
    "E": (-72, 116),
    "AS": (-14, 27),
    "EX": (-9, 60),
    "HE": (0, 60),
    "HEp": (40, 75),
    "TH": (-46, 40),
    "THp": (320, 380),
}
WINDOWS.update({ks: None for ks in WINTER_KS})

# Resolution precedence (first match wins): immovable feasts, then the
# solar/Easter anchored cycles, then the winter grid slots, then the generic
# Theophany/Heesnak season counts.
PRECEDENCE = ["C", "AS", "EX", "E"] + WINTER_KS + ["HE", "HEp", "TH", "THp"]

# Keyspaces whose keys are integers (day-offsets); all others are string keys.
INT_KEYSPACES = {"E", "AS", "EX", "HE", "HEp", "TH", "THp"}

# Human-readable season label per keyspace, refined by offset for the Easter core.
_KS_SEASON = {
    "C": "Immovable Feast",
    "AS": "Assumption Cycle",
    "EX": "Exaltation of the Cross Cycle",
    "HE": "Advent (Heesnak)",
    "HEp": "Advent (Heesnak)",
    "TH": "Season after Nativity",
    "THp": "Advent / Nativity Fast",
    # Winter grid slots:
    "AdvSun": "Advent (Heesnak)",
    "AoF": "Fast of Advent",
    "AdvFer": "Advent (Heesnak)",
    "AdvSat": "Advent (Heesnak)",
    "AdvSatB": "Advent (Heesnak)",
    "PnJohn": "Season after Nativity",
    "PnEve": "Eve of the Fast of Catechumens",
    "PnSun": "Season after Nativity",
    "PnFer": "Season after Nativity",
    "PnSat": "Season after Nativity",
    "PnSatB": "Season after Nativity",
}


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


def _lookup(d: datetime.date):
    cs = coords_for(d)
    for ks in PRECEDENCE:
        if ks not in _TABLES:
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
        entry = _TABLES[ks].get(key)
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
# Public API
# --------------------------------------------------------------------------- #

def compute_armenian_lectionary(target_date: datetime.date) -> dict:
    """Return the liturgical day and readings for ``target_date``."""
    ks, key, entry = _lookup(target_date)
    if entry is not None:
        refs = entry["readings"]
        return {
            "Date": target_date.isoformat(),
            "Liturgical Day": entry["feast"] or "(commemoration)",
            "Season": season_for(ks, key),
            "Readings": _group_readings(refs),
            "ReadingsList": refs,
            "Source": "validated-table",
        }

    # Fallback: no validated entry (chiefly the winter hinge). Name the season
    # algorithmically and flag the readings as not-yet-modeled.
    cs = coords_for(target_date)
    # Pick an in-window keyspace for a season label. Winter grid slots come first
    # (they carry the right Advent / after-Nativity label even when their
    # readings are withheld), then the Easter core, then the season counts.
    season = "Ordinary Time"
    for kspace in WINTER_KS + ["E", "AS", "EX", "TH", "HE", "HEp", "THp"]:
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
    import sys
    d = (datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1
         else datetime.date.today())
    import pprint
    pprint.pprint(compute_armenian_lectionary(d))
