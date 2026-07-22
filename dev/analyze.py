"""DEV-ONLY analysis harness for reverse-engineering the lectionary keying.

Loads every cached reference day (dev/reference_data/*.json) and tests
hypotheses about how the Armenian sanctoral/lectionary is keyed across years:
the same *liturgical coordinate* should yield identical readings in different
civil years. NOT used by the app at runtime.
"""

import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from armenian_lectionary.engine import calculate_gregorian_easter, sunday_closest_to  # noqa: E402

REF_DIR = os.path.join(os.path.dirname(__file__), "reference_data")


def load_all():
    from dev.source_corrections import apply_reading_order, normalize_confusables
    days = {}
    for path in glob.glob(os.path.join(REF_DIR, "*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        d["readings"] = apply_reading_order(d["date"], d["readings"])
        # Fold the source's Cyrillic homoglyphs (Cyrillic Е/о) in the English feast text
        # to Latin, so the built table matches the cleaned shipped one regardless of
        # whether the local cache predates the fix at the fetch step.
        d["feast"] = normalize_confusables(d.get("feast", ""))
        days[d["date"]] = d
    return days


def easter_offset(date_iso):
    d = datetime.date.fromisoformat(date_iso)
    return (d - calculate_gregorian_easter(d.year)).days


def readings_key(day):
    """Normalized tuple of (feast, readings) for equality comparison."""
    return (day["feast"].strip(), tuple(day["readings"]))


def test_easter_offset_keying(days):
    """Group days by Easter offset; report cross-year consistency."""
    by_offset = {}
    for iso, day in days.items():
        if not day["readings"] and not day["feast"]:
            continue  # skip empty (unavailable) days
        off = easter_offset(iso)
        by_offset.setdefault(off, []).append((iso, day))

    consistent = inconsistent = 0
    mismatches = []
    for off, items in sorted(by_offset.items()):
        if len(items) < 2:
            continue
        keys = {readings_key(d): iso for iso, d in items}
        if len(keys) == 1:
            consistent += 1
        else:
            inconsistent += 1
            mismatches.append((off, items))
    return consistent, inconsistent, mismatches


def consistency_map(days, keyfn):
    """For a keying function date_iso->coord, return per-coord cross-year status."""
    groups = {}
    for iso, day in days.items():
        if not day["readings"] and not day["feast"]:
            continue
        years = {iso[:4]}
        coord = keyfn(iso)
        if coord is None:
            continue
        groups.setdefault(coord, []).append((iso, day))
    status = {}  # coord -> (is_consistent, items)
    for coord, items in groups.items():
        if len({iso[:4] for iso, _ in items}) < 2:
            continue  # need >=2 years to judge
        keys = {readings_key(d) for _, d in items}
        status[coord] = (len(keys) == 1, items)
    return status


def civil_key(iso):
    return ("CIVIL", iso[5:])  # month-day


FIXED_FEASTS = {  # civil (month,day) that are always the same Lord's feast
    (1, 5), (1, 6),          # Eve of Theophany, Theophany/Nativity
    (2, 14),                 # Presentation (Tyarnndaraj)
    (4, 7),                  # Annunciation
}


def nearest_feast_coord(iso):
    """Key by signed day-offset to the nearest feast in the movable+solar chain.

    Negative offset = the feast's preparatory fast / run-up; positive = after.
    Fixed-date Lord's feasts override as civil-date keys."""
    d = datetime.date.fromisoformat(iso)
    if (d.month, d.day) in FIXED_FEASTS:
        return ("FIX", f"{d.month:02d}-{d.day:02d}")
    y = d.year
    feasts = []
    for yy in (y - 1, y, y + 1):
        e = calculate_gregorian_easter(yy)
        feasts += [
            ("TH", datetime.date(yy, 1, 6)),
            ("EA", e),
            ("TR", e + datetime.timedelta(days=98)),
            ("AS", sunday_closest_to(yy, 8, 15)),
            ("EX", sunday_closest_to(yy, 9, 14)),
            ("HE", sunday_closest_to(yy, 11, 18)),
        ]
    tag, fd = min(feasts, key=lambda tf: abs((d - tf[1]).days))
    return (tag, (d - fd).days)


def composite_coord(iso, core_lo=-64, core_hi=112):
    """Best-guess unified liturgical coordinate.

    Easter-offset within the core span; otherwise the number of days since the
    most recent solar/Theophany anchor (each anchor is a fixed point or a
    'closest Sunday', so day-counts are stable across years)."""
    d = datetime.date.fromisoformat(iso)
    y = d.year
    e = calculate_gregorian_easter(y)
    off = (d - e).days
    if core_lo <= off <= core_hi:
        return ("E", off)
    anchors = [
        ("TH", datetime.date(y, 1, 6)),
        ("AS", sunday_closest_to(y, 8, 15)),
        ("EX", sunday_closest_to(y, 9, 14)),
        ("HE", sunday_closest_to(y, 11, 18)),
        ("HEp", sunday_closest_to(y - 1, 11, 18)),
        ("THp", datetime.date(y - 1, 1, 6)),
        # Transfiguration (Easter+98) anchors the gap before Assumption:
        ("TR", e + datetime.timedelta(days=98)),
    ]
    passed = [(tag, ad) for tag, ad in anchors if ad <= d]
    tag, ad = max(passed, key=lambda x: x[1])
    return (tag, (d - ad).days)


if __name__ == "__main__":
    days = load_all()
    print(f"Loaded {len(days)} cached days "
          f"({sum(1 for d in days.values() if d['readings'])} with readings)\n")
    print(f"Date range: {min(days)} .. {max(days)}\n")

    # 1) Easter-offset keying: map consistency by offset to find the anchored span.
    estatus = consistency_map(days, lambda iso: ("E", easter_offset(iso)))
    off_ok = {off: ok for (tag, off), (ok, items) in estatus.items()}
    offs = sorted(off_ok)
    print("=== Easter-offset keying: consistent (.) vs inconsistent (X) by offset ===")
    line = []
    for off in offs:
        line.append(f"{off}{'.' if off_ok[off] else 'X'}")
    # Print contiguous consistent ranges
    cons = [off for off in offs if off_ok[off]]
    incons = [off for off in offs if not off_ok[off]]
    def ranges(nums):
        out = []
        for n in sorted(nums):
            if out and n == out[-1][1] + 1:
                out[-1][1] = n
            else:
                out.append([n, n])
        return [f"{a}..{b}" if a != b else f"{a}" for a, b in out]
    print(f"  consistent offset ranges:   {', '.join(ranges(cons))}")
    print(f"  inconsistent offset ranges: {', '.join(ranges(incons))}\n")

    # 2) Composite coordinate across the WHOLE year.
    comp = consistency_map(days, nearest_feast_coord)
    cc = sum(1 for ok, _ in comp.values() if ok)
    ci = sum(1 for ok, _ in comp.values() if not ok)
    print(f"=== Composite liturgical-coordinate keying (whole year) ===")
    print(f"  consistent coords:   {cc}")
    print(f"  inconsistent coords: {ci}")
    print(f"  consistency: {cc/(cc+ci)*100:.1f}%\n")
    print("  remaining inconsistent coords (anchor, offset):")
    for coord, (ok, items) in sorted(comp.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if not ok:
            isos = [i for i, _ in items]
            feasts = [d['feast'][:32] for _, d in items]
            print(f"    {coord}: {list(zip(isos, feasts))}")
