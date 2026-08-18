"""DEV-ONLY: verify ``engine._position_label`` against every position label in the cache.

The engine regenerates the source's calendar-position label per date rather than storing
it in the validated table (a table key is shared by civil years whose ordinals differ; see
``build_table.unanimous_feast``). This script is the evidence for that generator: for every
cached day it compares the regenerated label against the position component the source
actually printed, and reports

  * MISMATCH -- the engine emits a label the source contradicts. Must be 0: a wrong label
    is worse than none, since bahk persists it into ``Feast.name``.
  * MISSING  -- the source has a position label this GENERATOR does not produce. NOT data
    loss: the label may still be served from the validated table, which keeps a
    calendar-derived component whenever every year sharing the key states it identically
    (build_table.unanimous_feast). The whole residue is currently of that kind -- the
    "Fast day" marker on Mon/Tue/Thu/Sat/Sun -- so every source position label still
    reaches the served name. The end-to-end check is at the bottom of this report.
  * EXTRA    -- the engine emits a label where the source printed none. Also a defect.

Usage:
    python dev/verify_position_labels.py            # summary + residue by family
    python dev/verify_position_labels.py -v         # every mismatch
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                       # noqa: E402
from dev.feast_names import is_position                                # noqa: E402
from dev.source_corrections import expected_fast_marker_components     # noqa: E402
from armenian_lectionary.engine import (                               # noqa: E402
    _FEAST_SEP, _position_label, compute_armenian_lectionary,
)

_BARE_FAST_MARKERS = ("Fast day", "Feast day")


def source_position(feast_str):
    """The position component the source printed for a day, or None."""
    for c in [x.strip() for x in (feast_str or "").split(_FEAST_SEP) if x.strip()]:
        if is_position(c):
            return c
    return None


def family_of(label):
    """Strip the ordinal word so labels group by family."""
    for sep in (" day of ", " Sunday"):
        if sep in label:
            return sep.strip() + " " + label.split(sep, 1)[1]
    return label


def main():
    days = load_all()
    mismatch, missing, extra = [], [], []
    matched = reclassified = 0

    for iso in sorted(days):
        feast = (days[iso].get("feast") or "").strip()
        if not feast:
            continue          # no ground truth for this day (2027) -- nothing to check
        d = datetime.date.fromisoformat(iso)
        src = source_position(feast)
        got = _position_label(d)
        if src in _BARE_FAST_MARKERS:
            # A bare "Fast day"/"Feast day" marker is now deliberately reclassified into
            # a weekday split, a named-fast day-count label, or nothing at all -- see
            # engine._POSITION_FAMILIES and docs/feast-name-corrections.md. Not a
            # mismatch to report; counted separately, and checked end-to-end below.
            reclassified += 1
            continue
        if src and got:
            if src == got:
                matched += 1
            elif src.endswith("day of Pentecost") and got.endswith(
                    "day of the Fast of Prophet Elijah"):
                # Deliberate rename (same ordinal, different wording) -- the week after
                # Pentecost is the Fast of Prophet Elijah; see docs/feast-name-
                # corrections.md. Not a mismatch to report.
                reclassified += 1
            else:
                mismatch.append((iso, src, got))
        elif src and not got:
            missing.append((iso, src))
        elif got and not src:
            extra.append((iso, got))

    # The question that actually matters downstream: does the SERVED name carry every
    # position label the source states? The generator is only one of its two sources; the
    # validated table supplies the rest. Anything counted here as "missing" above may
    # still be served, so report the end-to-end number too -- reading the generator's
    # residue as data loss is the obvious misreading of this tool.
    served_ok = served_lost = 0
    for iso in sorted(days):
        feast = (days[iso].get("feast") or "").strip()
        src = source_position(feast) if feast else None
        if not src:
            continue
        served = compute_armenian_lectionary(
            datetime.date.fromisoformat(iso))["Liturgical Day"]
        served_parts = [c.strip() for c in served.split(_FEAST_SEP)]
        if src in _BARE_FAST_MARKERS:
            full_src = [c.strip() for c in feast.split(_FEAST_SEP) if c.strip()]
            expected = expected_fast_marker_components(iso, full_src)
            ok = all(e in served_parts for e in expected)
        elif src.endswith("day of Pentecost"):
            renamed = src.replace("day of Pentecost", "day of the Fast of Prophet Elijah")
            ok = renamed in served_parts
        else:
            ok = src in served_parts
        if ok:
            served_ok += 1
        else:
            served_lost += 1

    print(f"matched  {matched}")
    print(f"reclassified {reclassified}   (bare fast marker; see docs/feast-name-corrections.md)")
    print(f"MISMATCH {len(mismatch)}   (must be 0 -- engine contradicts the source)")
    print(f"EXTRA    {len(extra)}   (must be 0 -- engine labels a day the source does not)")
    print(f"missing  {len(missing)}   (generator does not produce it; may still be served "
          f"from the table -- see below)")
    print()
    print(f"END-TO-END: {served_ok}/{served_ok + served_lost} source position labels reach "
          f"the served name; {served_lost} LOST (must be 0)")

    if missing:
        print("\nmissing by family:")
        for fam, n in collections.Counter(
                family_of(s) for _, s in missing).most_common():
            print(f"  {n:5d}  {fam}")
    if mismatch:
        print("\nmismatches by family:")
        for fam, n in collections.Counter(
                family_of(s) for _, s, _ in mismatch).most_common():
            print(f"  {n:5d}  {fam}")
        show = mismatch if "-v" in sys.argv else mismatch[:15]
        for iso, src, got in show:
            print(f"  {iso}  src={src!r}  eng={got!r}")
    if extra:
        for iso, got in (extra if "-v" in sys.argv else extra[:15]):
            print(f"  EXTRA {iso}  eng={got!r}  src=(none)")

    return 1 if (mismatch or extra) else 0


if __name__ == "__main__":
    sys.exit(main())
