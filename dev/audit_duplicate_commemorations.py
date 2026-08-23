"""DEV-ONLY: find canons the engine commemorates twice in one liturgical year.

The Tonats'oyts lays each saint's canon down **once** per annual cycle. So an observance
id served on two days of the same liturgical year is a duplicate commemoration, and every
one of them is a name the engine puts on a day the book does not.

Nothing else looks for this, and the reason is specific. Both discrepancy reports compare
the engine to the source **one day at a time**, and on a single day these are not visible:
the packed day is classified ``EXPANSION`` -- the engine naming companion canons the
Second Volume abbreviated away, which its preface (Sixth) instructs -- and the companion's
own day matches the source exactly. Neither day is wrong on its own. The pair is. The
EXPANSION warrant holds only when the taregir left the companion no day of its own, and
nothing checked that until this script.

That framing is also what lets this cover **2027**, the one year in range with no ground
truth: the invariant is a statement about the engine's own output across a year, so it
needs no oracle. Both 2027-only findings were invisible to every other check.

The liturgical year runs Heesnak to Heesnak (``engine._liturgical_year``, cut at the Sunday
closest to Nov 18 -- the start of the Fast of Advent, and so of the Armenian church year).
That cut drifts by up to a week, which can land a September- or December-anchored
observance in one window twice; the two ids where that happens are declared in
``observance_ids._RECURRING_OBSERVANCES`` alongside the five that recur by design, each
with its reason. Nothing else is exempt.

Where the cache has ground truth, each occurrence is annotated with what the source
actually printed that day, so a finding can be read without cross-referencing by hand.
2027 findings carry no such annotation and are marked accordingly.

Usage:
    python dev/audit_duplicate_commemorations.py          # summary
    python dev/audit_duplicate_commemorations.py --list   # every finding, with source text
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.observance_ids import ids_for_text, recurs_by_design                # noqa: E402
from armenian_lectionary.engine import (                                     # noqa: E402
    MAX_YEAR, MIN_YEAR, _liturgical_year, compute_armenian_lectionary,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(REPO_ROOT, "dev", "reference_data")


def source_feast(d):
    """What sacredtradition.am printed for ``d``, or None if the cache has no entry.

    An empty string is a real answer -- 2027 is cached with 365 blank days -- and is
    reported as such rather than folded into "no cache".
    """
    path = os.path.join(CACHE_DIR, f"{d.isoformat()}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return (json.load(fh).get("feast") or "").strip()


def occurrences():
    """``{id: [date, ...]}`` over the whole supported range, in date order."""
    by_id = collections.defaultdict(list)
    d = datetime.date(MIN_YEAR, 1, 1)
    end = datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        for sid in ids_for_text(compute_armenian_lectionary(d)["Liturgical Day"]):
            by_id[sid].append(d)
        d += datetime.timedelta(days=1)
    return by_id


def findings():
    """Every ``(liturgical_year, id, [dates])`` where one canon is kept more than once."""
    found = []
    for sid, dates in sorted(occurrences().items()):
        if recurs_by_design(sid):
            continue
        per_year = collections.defaultdict(list)
        for d in dates:
            per_year[_liturgical_year(d)].append(d)
        for ly, days in sorted(per_year.items()):
            if len(days) > 1:
                found.append((ly, sid, days))
    return found


def main():
    found = findings()
    by_id = collections.Counter(sid for _, sid, _ in found)
    unverifiable = sum(1 for _, _, days in found
                       if all(source_feast(d) == "" for d in days))

    print(f"{len(found)} duplicate commemoration(s) over liturgical years "
          f"{MIN_YEAR}-{MAX_YEAR}   (must be 0)")
    print(f"  {len(by_id)} distinct canon(s); {unverifiable} in years with no ground truth")
    print()
    for sid, n in by_id.most_common():
        print(f"  {n:3} liturgical year(s)   {sid}")

    if "--list" not in sys.argv:
        return 1 if found else 0

    for ly, sid, days in found:
        span = (days[-1] - days[0]).days
        print(f"\n--- LY{ly}  {sid}   ({len(days)} days, {span}d apart)")
        for d in days:
            served = compute_armenian_lectionary(d)
            src = source_feast(d)
            shown = "(no ground truth)" if src == "" else repr(src)
            print(f"  {d} {d.strftime('%a')} [{served['Source']}]")
            print(f"      served: {served['Liturgical Day']}")
            print(f"      source: {shown}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
