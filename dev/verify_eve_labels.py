"""DEV-ONLY: verify ``engine._eve_label`` against every eve component in the cache.

The sibling of ``dev/verify_position_labels.py``, for the other component a shared table
key cannot hold. An eve is a fixed offset from a movable anchor, so when it lands on a
fixed-date feast the key is that feast's civil date and the eve is not unanimous across
the years sharing it -- ``build_table.unanimous_feast`` drops it and the day loses its
fast marker. ``engine._eve_label`` regenerates it per date; this is its evidence.

  * MISMATCH -- the engine emits an eve the source contradicts. Must be 0.
  * MISSING  -- the source has an eve the GENERATOR does not produce. Must be 0 too:
    unlike the position label, every eve family here is implemented, so a gap is a bug.
  * EXTRA    -- the engine calls a day an eve where the source does not. Must be 0.

The END-TO-END line is the one that matters downstream: it asks whether the SERVED name
carries every eve the source states, counting the table and the generator together.

Usage:
    python dev/verify_eve_labels.py            # summary
    python dev/verify_eve_labels.py -v         # every discrepancy
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                       # noqa: E402
from armenian_lectionary.engine import (                               # noqa: E402
    _OBSERVANCE_SEP, _eve_label, compute_armenian_lectionary,
)


def source_eve(feast_str):
    """The eve component the source printed for a day, or None."""
    for c in [x.strip() for x in (feast_str or "").split(_OBSERVANCE_SEP) if x.strip()]:
        if c.startswith("Eve of "):
            return c
    return None


def main():
    days = load_all()
    mismatch, missing, extra = [], [], []
    matched = 0

    for iso in sorted(days):
        feast = (days[iso].get("feast") or "").strip()
        if not feast:
            continue          # no ground truth for this day (2027) -- nothing to check
        d = datetime.date.fromisoformat(iso)
        src = source_eve(feast)
        got = _eve_label(d)
        if src and got:
            if src == got:
                matched += 1
            else:
                mismatch.append((iso, src, got))
        elif src and not got:
            missing.append((iso, src))
        elif got and not src:
            extra.append((iso, got))

    served_ok, served_lost = 0, []
    for iso in sorted(days):
        feast = (days[iso].get("feast") or "").strip()
        src = source_eve(feast) if feast else None
        if not src:
            continue
        served = compute_armenian_lectionary(
            datetime.date.fromisoformat(iso))["Liturgical Day"]
        if src in [c.strip() for c in served.split(_OBSERVANCE_SEP)]:
            served_ok += 1
        else:
            served_lost.append((iso, src, served))

    print(f"matched  {matched}")
    print(f"MISMATCH {len(mismatch)}   (must be 0 -- engine contradicts the source)")
    print(f"MISSING  {len(missing)}   (must be 0 -- every eve family is implemented)")
    print(f"EXTRA    {len(extra)}   (must be 0 -- engine calls a day an eve, source does not)")
    print()
    print(f"END-TO-END: {served_ok}/{served_ok + len(served_lost)} source eve components "
          f"reach the served name; {len(served_lost)} LOST (must be 0)")

    for title, rows in (("mismatches", mismatch), ("missing", missing),
                        ("extras", extra)):
        if not rows:
            continue
        print(f"\n{title} by label:")
        for lab, n in collections.Counter(r[1] for r in rows).most_common():
            print(f"  {n:5d}  {lab}")
        for row in (rows if "-v" in sys.argv else rows[:15]):
            print("  ", *row)
    for row in (served_lost if "-v" in sys.argv else served_lost[:15]):
        print("  LOST", *row)

    return 1 if (mismatch or missing or extra or served_lost) else 0


if __name__ == "__main__":
    sys.exit(main())
