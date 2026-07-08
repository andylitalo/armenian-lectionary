"""DEV-ONLY: learn a validated, multi-keyspace lectionary table from ground truth.

Idea: every day has several candidate liturgical coordinates (civil date,
Easter-offset, days-since-solar-anchor, days-since-Theophany). For each
coordinate we keep an entry ONLY if every historical year that hit that
coordinate agrees on the readings (cross-year consistent). At runtime we
compute a date's coordinates and resolve by precedence + a date window,
returning the first reliable hit.

This script:
  1. builds the validated entries per keyspace,
  2. defines lookup(date) over them,
  3. self-validates against all historical days and prints accuracy + misses.

The resulting tables get exported to ../lectionary_data.json by export_table().
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
# Reuse the runtime calendar math (and key-resolution) so the table is built and
# keyed exactly as the app reads it.
from armenian_lectionary.engine import coords_for, WINDOWS, PRECEDENCE, _lookup, DATA_PATH  # noqa: E402


def rsig(day):
    """Readings-only signature (the app cares about scripture refs, not the
    exact feast label, which sometimes gets a movable suffix like Remembrance)."""
    return tuple(day["readings"])


def modal_feast(items):
    """Most common feast label among items (list of (year, day))."""
    c = collections.Counter(day["feast"].strip() for _, day in items)
    return c.most_common(1)[0][0]


def _consistent(items, min_years):
    """True if all years agree on the readings and >= min_years support it."""
    sigs = {rsig(day) for _, day in items}
    years = {yr for yr, _ in items}
    return len(sigs) == 1 and len(years) >= min_years


CIVIL_MIN_YEARS = 5  # support needed to declare a civil date an immovable feast


def build(days):
    """Two-pass build.

    Pass 1: discover immovable feasts = civil (month,day) whose READINGS are
            consistent across >= CIVIL_MIN_YEARS years. These outrank everything.
    Pass 2: build the movable/anchored keyspaces from the REMAINING days
            (days not claimed by an immovable feast), keyed by readings.
    """
    valid = {iso: day for iso, day in days.items()
             if day["readings"] or day["feast"]}

    # ---- Pass 1: civil-fixed feasts ----
    civ = collections.defaultdict(list)
    for iso, day in valid.items():
        d = datetime.date.fromisoformat(iso)
        civ[(d.month, d.day)].append((iso[:4], day))
    civil_table = {}
    fixed_dates = set()  # (month,day) that are immovable feasts
    for md, items in civ.items():
        if _consistent(items, CIVIL_MIN_YEARS):
            day0 = items[0][1]
            civil_table[md] = {
                "feast": modal_feast(items),
                "readings": list(day0["readings"]),
                "support_years": sorted({yr for yr, _ in items}),
            }
            fixed_dates.add(md)

    # ---- Pass 2: anchored keyspaces over unclaimed days ----
    anchored = [ks for ks in PRECEDENCE if ks != "C"]
    buckets = {ks: collections.defaultdict(list) for ks in anchored}
    for iso, day in valid.items():
        d = datetime.date.fromisoformat(iso)
        if (d.month, d.day) in fixed_dates:
            continue  # claimed by an immovable feast
        cs = coords_for(d)
        for ks in anchored:
            if ks not in cs:        # winter keyspace not applicable to this date
                continue
            key = cs[ks]
            win = WINDOWS[ks]
            if win is not None and not (win[0] <= key <= win[1]):
                continue
            buckets[ks][key].append((iso[:4], day))

    tables = {"C": {f"{m:02d}-{dd:02d}": v for (m, dd), v in civil_table.items()}}
    stats = {"C": (len(civil_table), len(civ) - len(civil_table))}
    for ks in anchored:
        kept = dropped = 0
        tables[ks] = {}
        for key, items in buckets[ks].items():
            if _consistent(items, 2):
                day0 = items[0][1]
                tables[ks][key] = {
                    "feast": modal_feast(items),
                    "readings": list(day0["readings"]),
                    "support_years": sorted({yr for yr, _ in items}),
                }
                kept += 1
            else:
                dropped += 1
        stats[ks] = (kept, dropped)
    return tables, stats


def validate(days, tables):
    ok = miss = nodata = 0
    misses = []
    for iso, day in sorted(days.items()):
        if not day["readings"] and not day["feast"]:
            continue
        d = datetime.date.fromisoformat(iso)
        ks, key, entry = _lookup(d, tables)
        if entry is None:
            nodata += 1
            misses.append((iso, "NO-ENTRY", day["feast"][:40], day["readings"]))
        elif tuple(entry["readings"]) == rsig(day):
            ok += 1
        else:
            miss += 1
            misses.append((iso, f"WRONG via {ks}:{key}", day["feast"][:40],
                           f"got={entry['readings']} want={day['readings']}"))
    total = ok + miss + nodata
    return ok, miss, nodata, total, misses


def export_table(tables, stats, path=None):
    """Write the validated tables to the runtime's shipped data file
    (armenian_lectionary/data/lectionary_data.json)."""
    if path is None:
        path = DATA_PATH
    # Strip support_years from shipped entries to keep the file lean.
    slim = {}
    for ks, entries in tables.items():
        slim[ks] = {}
        for key, v in entries.items():
            keystr = key if isinstance(key, str) else str(key)
            slim[ks][keystr] = {"feast": v["feast"], "readings": v["readings"]}
    meta = {
        "source": "Distilled & cross-year-validated from sacredtradition.am "
                  "(Tonatsooyts), 2014-2026. Offline; no runtime network use.",
        "entries_per_keyspace": {ks: stats[ks][0] for ks in stats},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "tables": slim}, f, ensure_ascii=False, indent=1)
    return path


if __name__ == "__main__":
    days = load_all()
    tables, stats = build(days)
    print("Validated entries kept per keyspace (kept/dropped):")
    for ks in PRECEDENCE:
        print(f"  {ks:4}: {stats[ks][0]:4} kept, {stats[ks][1]:4} dropped")
    ok, miss, nodata, total, misses = validate(days, tables)
    print(f"\nSelf-validation over {total} historical days:")
    print(f"  correct:  {ok}  ({ok/total*100:.1f}%)")
    print(f"  wrong:    {miss}")
    print(f"  no-entry: {nodata}")
    path = export_table(tables, stats)
    print(f"\nExported validated table -> {path}")
    show = sys.argv[1] if len(sys.argv) > 1 else None
    if show:
        print("\nSample misses:")
        n = 0
        for iso, kind, feast, detail in misses:
            if show != "all" and not iso.startswith(show):
                continue
            print(f"  {iso} [{kind}] {feast}")
            n += 1
            if n >= 50:
                break
