"""DEV-ONLY: winter-hinge slot extractor & miss-diagnostic.

The winter ferial zone (Advent -> Nativity/Theophany -> pre-Lent) is keyed by a
stable grid coordinate produced by the runtime scheduler in lectionary.py
(winter_coords): numbered Sundays, forward/backward fast tracks, and a
(week, weekday) saint grid. The dev build pipeline keeps only the coordinates
whose readings agree across every supporting year; the rest stay "unavailable".

This tool bins every historical winter day by its winter coordinate and reports,
per keyspace, which slots are cross-year consistent (would be shipped) and which
are dropped -- and for the dropped ones, the disagreeing occupants -- so the
scheduler's merge/anchor/exclusion rules can be refined.

Usage:
  python dev/slot_model.py            # summary table of kept/dropped per keyspace
  python dev/slot_model.py AdvSat     # detail the dropped buckets of one keyspace
  python dev/slot_model.py all        # detail every dropped bucket
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from lectionary import winter_coords, WINTER_KS  # noqa: E402


def _fixed_dates(days):
    """The civil (month,day) immovable feasts that build() claims (and so removes
    from the winter buckets); mirror that here for an accurate diagnostic."""
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "lectionary_data.json")
    with open(path, encoding="utf-8") as f:
        civ = json.load(f)["tables"]["C"]
    return {(int(k[:2]), int(k[3:])) for k in civ}


def bin_winter(days):
    """keyspace -> {key -> list[(iso, feast, readings_tuple)]} over winter days."""
    fixed = _fixed_dates(days)
    bins = {ks: collections.defaultdict(list) for ks in WINTER_KS}
    for iso, day in days.items():
        if not (day["readings"] or day["feast"]):
            continue
        d = datetime.date.fromisoformat(iso)
        if (d.month, d.day) in fixed:        # claimed by an immovable feast
            continue
        for ks, key in winter_coords(d).items():
            bins[ks][key].append((iso, day["feast"].strip()[:34],
                                  tuple(day["readings"])))
    return bins


def summary(bins):
    print(f"{'keyspace':9} {'kept':>5} {'dropped':>8} {'days_kept':>10}")
    tot_kept = tot_days = 0
    for ks in WINTER_KS:
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


def detail(bins, which):
    for ks in WINTER_KS:
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
    bins = bin_winter(days)
    summary(bins)
    if len(sys.argv) > 1:
        detail(bins, sys.argv[1])
