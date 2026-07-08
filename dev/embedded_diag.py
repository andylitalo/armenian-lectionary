"""DEV-ONLY: find embedded fixed-date feasts that contaminate anchored buckets.

A fixed-date feast (e.g. Annunciation Apr 7, Presentation Feb 14) floats across
the movable ferial slots: in the one year it lands on a given Easter/Assumption/
Exaltation offset it injects its *proper* readings into that bucket, breaking the
otherwise-unanimous ferial consensus so the whole bucket is dropped (estimate).

This tool bins every day exactly like build_table pass-2 (skipping the civil
immovable feasts), then for every INCONSISTENT bucket checks whether removing a
single civil (month,day) would make it unanimous. It ranks (month,day) by how
many buckets they break -> the EMBEDDED_FIXED candidate set.

Usage: python dev/embedded_diag.py [keyspace ...]   (default: E AS EX)
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from dev.build_table import build  # noqa: E402
from armenian_lectionary.engine import coords_for, WINDOWS  # noqa: E402


def fixed_dates(days):
    """The civil immovable (month,day) that build() claims (and removes)."""
    _, _ = None, None
    tables, _stats = build(days)
    return {(int(k[:2]), int(k[3:])) for k in tables["C"]}


def rsig(day):
    return tuple(day["readings"])


def main(argv):
    keyspaces = argv or ["E", "AS", "EX"]
    days = load_all()
    fixed = fixed_dates(days)

    # Bin like build pass-2.
    buckets = {ks: collections.defaultdict(list) for ks in keyspaces}
    for iso, day in days.items():
        if not (day["readings"] or day["feast"]):
            continue
        d = datetime.date.fromisoformat(iso)
        if (d.month, d.day) in fixed:
            continue
        cs = coords_for(d)
        for ks in keyspaces:
            if ks not in cs:
                continue
            key = cs[ks]
            win = WINDOWS.get(ks)
            if win is not None and not (win[0] <= key <= win[1]):
                continue
            buckets[ks][key].append((d, day))

    breaker = collections.Counter()      # (m,d) -> buckets it solely breaks
    breaker_detail = collections.defaultdict(list)
    for ks in keyspaces:
        for key, items in buckets[ks].items():
            sigs = {rsig(day) for _, day in items}
            years = {d.year for d, _ in items}
            if len(sigs) == 1 or len(years) < 2:
                continue  # already consistent (or unjudgeable)
            # Which (m,d) dates, if all removed, leave a unanimous bucket?
            by_md = collections.defaultdict(list)
            for d, day in items:
                by_md[(d.month, d.day)].append(rsig(day))
            # Try removing each single (m,d): does the remainder become unanimous
            # with >=2 surviving years?
            for md in by_md:
                rest = [(d, day) for d, day in items if (d.month, d.day) != md]
                rsigs = {rsig(day) for _, day in rest}
                ryears = {d.year for d, _ in rest}
                if len(rsigs) == 1 and len(ryears) >= 2:
                    breaker[md] += 1
                    breaker_detail[md].append((ks, key, len(items)))

    print(f"Loaded {len(days)} days; {len(fixed)} civil immovable feasts.\n")
    print("Embedded-fixed candidates (single (month,day) whose removal makes an")
    print("inconsistent anchored bucket unanimous), ranked by buckets recovered:\n")
    for md, n in breaker.most_common(40):
        sample = days.get(f"2014-{md[0]:02d}-{md[1]:02d}") or {}
        # find any year's feast label for this md
        label = ""
        for iso, day in days.items():
            dd = datetime.date.fromisoformat(iso)
            if (dd.month, dd.day) == md and day["feast"]:
                label = day["feast"].strip()[:40]
                break
        print(f"  {md[0]:02d}-{md[1]:02d}  recovers {n:3} buckets   {label}")
        for ks, key, sz in sorted(breaker_detail[md])[:0]:
            pass


if __name__ == "__main__":
    main(sys.argv[1:])
