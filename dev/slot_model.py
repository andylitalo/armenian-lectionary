"""DEV-ONLY: winter & hinge slot extractor & miss-diagnostic.

The variable-gap ferial zones (winter Advent->Nativity->pre-Lent, and the summer/
autumn/post-Exaltation hinges) are keyed by a stable grid coordinate produced by
the runtime scheduler in lectionary.py (winter_coords / hinge_coords): numbered
Sundays, forward/backward fast tracks, a (week, weekday) saint grid, and the
saint-IDENTITY coordinate ({Zone}Saint). The dev build pipeline keeps only the
coordinates whose readings agree across every supporting year; the rest stay
"unavailable".

This tool bins every historical winter/hinge day by its coordinate and reports,
per keyspace, which slots are cross-year consistent (would be shipped) and which
are dropped -- and for the dropped ones, the disagreeing occupants -- so the
scheduler's merge/anchor/exclusion rules can be refined.

Usage:
  python dev/slot_model.py            # winter summary (default)
  python dev/slot_model.py hinge      # summer/autumn/post-Exaltation summary
  python dev/slot_model.py AdvSat     # detail the dropped buckets of one keyspace
  python dev/slot_model.py TrSaint    # ditto for a hinge keyspace
  python dev/slot_model.py all        # detail every dropped bucket (both zones)
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from armenian_lectionary.engine import winter_coords, WINTER_KS, hinge_coords, HINGE_KS  # noqa: E402


def _fixed_dates(days):
    """The civil (month,day) immovable feasts that build() claims (and so removes
    from the winter buckets); mirror that here for an accurate diagnostic."""
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "lectionary_data.json")
    with open(path, encoding="utf-8") as f:
        civ = json.load(f)["tables"]["C"]
    return {(int(k[:2]), int(k[3:])) for k in civ}


def _bin(days, coords_fn, kslist):
    """keyspace -> {key -> list[(iso, feast, readings_tuple)]} over the days a
    coordinate function (winter_coords / hinge_coords) classifies."""
    fixed = _fixed_dates(days)
    bins = {ks: collections.defaultdict(list) for ks in kslist}
    for iso, day in days.items():
        if not (day["readings"] or day["feast"]):
            continue
        d = datetime.date.fromisoformat(iso)
        if (d.month, d.day) in fixed:        # claimed by an immovable feast
            continue
        for ks, key in coords_fn(d).items():
            if ks not in bins:               # other-zone coordinate; skip
                continue
            bins[ks][key].append((iso, day["feast"].strip()[:34],
                                  tuple(day["readings"])))
    return bins


def bin_winter(days):
    """Winter (Advent / post-Nativity) grid bins."""
    return _bin(days, winter_coords, WINTER_KS)


def bin_hinge(days):
    """Summer / autumn / post-Exaltation grid bins."""
    return _bin(days, hinge_coords, HINGE_KS)


def summary(bins, kslist):
    print(f"{'keyspace':9} {'kept':>5} {'dropped':>8} {'days_kept':>10}")
    tot_kept = tot_days = 0
    for ks in kslist:
        kept = dropped = days_kept = 0
        for key, items in bins[ks].items():
            sigs = {r for _, _, r in items}
            years = {iso[:4] for iso, _, _ in items}
            if len(sigs) == 1 and len(years) >= 2:
                kept += 1
                days_kept += len(items)
            else:
                dropped += 1
        tot_kept += kept
        tot_days += days_kept
        print(f"{ks:9} {kept:5} {dropped:8} {days_kept:10}")
    print(f"{'TOTAL':9} {tot_kept:5} {'':8} {tot_days:10}")


def detail(bins, kslist, which):
    for ks in kslist:
        if which != "all" and ks != which:
            continue
        print(f"\n=== {ks}: dropped buckets ===")
        for key in sorted(bins[ks]):
            items = bins[ks][key]
            sigs = {r for _, _, r in items}
            if len(sigs) == 1:
                continue
            print(f"  key={key!r}  ({len(items)} days, {len(sigs)} distinct)")
            for iso, feast, r in sorted(items):
                print(f"      {iso} {feast:34} :: {list(r)[:2]}")


if __name__ == "__main__":
    days = load_all()
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    # Dispatch: "hinge" -> hinge summary; a hinge keyspace -> hinge detail;
    # otherwise winter summary (+ optional winter/all detail).
    if arg == "hinge":
        summary(bin_hinge(days), HINGE_KS)
    elif arg in HINGE_KS:
        bins = bin_hinge(days)
        summary(bins, HINGE_KS)
        detail(bins, HINGE_KS, arg)
    else:
        wbins = bin_winter(days)
        summary(wbins, WINTER_KS)
        if arg == "all":
            detail(wbins, WINTER_KS, "all")
            detail(bin_hinge(days), HINGE_KS, "all")
        elif arg:
            detail(wbins, WINTER_KS, arg)
