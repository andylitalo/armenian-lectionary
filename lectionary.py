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


def coords_for(d: datetime.date) -> dict:
    """All candidate (keyspace -> key) liturgical coordinates for a date."""
    y = d.year
    a = anchors(y)
    a_prev = anchors(y - 1)
    return {
        "C": (d.month, d.day),                  # civil date (immovable feasts)
        "E": (d - a["E"]).days,                 # Easter-anchored core
        "AS": (d - a["AS"]).days,               # Assumption period
        "EX": (d - a["EX"]).days,               # Exaltation period
        "HE": (d - a["HE"]).days,               # Advent (this year)
        "HEp": (d - a_prev["HE"]).days,         # Advent tail into early January
        "TH": (d - a["TH"]).days,               # weeks after Nativity
        "THp": (d - a_prev["TH"]).days,
    }


# Date windows (days relative to anchor) where each keyspace may apply, to keep
# far-away dates from matching an anchor by coincidence.
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

# Resolution precedence (first match wins): immovable feasts, then the
# solar/Easter anchored cycles, then the Theophany-season counts.
PRECEDENCE = ["C", "AS", "EX", "E", "HE", "HEp", "TH", "THp"]

# Human-readable season label per keyspace, refined by offset for the Easter core.
_KS_SEASON = {
    "C": "Immovable Feast",
    "AS": "Assumption Cycle",
    "EX": "Exaltation of the Cross Cycle",
    "HE": "Advent (Heesnak)",
    "HEp": "Advent (Heesnak)",
    "TH": "Season after Nativity",
    "THp": "Advent / Nativity Fast",
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
    # JSON object keys are strings; integer-keyed keyspaces need int keys.
    out = {}
    for ks, entries in tables.items():
        if ks == "C":
            out[ks] = entries
        else:
            out[ks] = {int(k): v for k, v in entries.items()}
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
    # Pick an in-window keyspace for a season label (post-Nativity before the
    # previous year's Advent, so January reads as "after Nativity").
    season = "Ordinary Time"
    for kspace in ["E", "AS", "EX", "TH", "HE", "HEp", "THp"]:
        win = WINDOWS[kspace]
        if win is not None and win[0] <= cs[kspace] <= win[1]:
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
