"""DEV-ONLY: derive the composite rule for EMBEDDED_FIXED feast-days.

Each embedded feast is (proper readings) combined with the readings of the
movable ferial/Sunday slot it lands on. This probe, for every occurrence:
  * computes the UNDERLYING slot readings (look the date up as if it were not a
    feast, via the normal anchored keyspaces), and
  * checks whether  proper ++ slot  or  slot ++ proper  reproduces the truth,
where `proper` is the contiguous block common to all years of that date.

It prints, per embedded date, the derived proper block and how every occurrence
composes, so we can encode a deterministic runtime rule.
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
import lectionary as L  # noqa: E402


def base_coords(d):
    """coords_for WITHOUT the embedded-fixed suppression (the movable slot)."""
    saved = L.EMBEDDED_FIXED
    L.EMBEDDED_FIXED = set()
    try:
        cs = L.coords_for(d)
    finally:
        L.EMBEDDED_FIXED = saved
    cs.pop("C", None)        # ignore civil (it's the feast itself)
    return cs


def slot_readings(d, tables):
    """Readings of the underlying movable slot for date d (or None)."""
    saved = L.EMBEDDED_FIXED
    L.EMBEDDED_FIXED = set()
    try:
        ks, key, entry = L._lookup(d, tables)
    finally:
        L.EMBEDDED_FIXED = saved
    if entry is None or ks == "C":
        return ks, None
    return ks, tuple(entry["readings"])


def common_block(seqs):
    """Longest contiguous block common to (and identically placed in) all seqs.

    Returns the block that appears as a contiguous sublist in every sequence."""
    if not seqs:
        return ()
    shortest = min(seqs, key=len)
    n = len(shortest)
    for length in range(n, 0, -1):
        for start in range(0, n - length + 1):
            cand = tuple(shortest[start:start + length])
            if all(_contains(s, cand) for s in seqs):
                return cand
    return ()


def _contains(seq, sub):
    n, m = len(seq), len(sub)
    return any(tuple(seq[i:i + m]) == sub for i in range(n - m + 1))


def main():
    days = load_all()
    tables = L._TABLES
    by_md = collections.defaultdict(list)
    for iso, day in days.items():
        if not (day["readings"] or day["feast"]):
            continue
        d = datetime.date.fromisoformat(iso)
        if (d.month, d.day) in L.EMBEDDED_FIXED:
            by_md[(d.month, d.day)].append((d, day))

    for md in sorted(by_md):
        items = sorted(by_md[md])
        seqs = [tuple(day["readings"]) for _, day in items]
        proper = common_block(seqs)
        print(f"\n===== {md[0]:02d}-{md[1]:02d}  ({len(items)} occurrences) =====")
        print(f"  proper block ({len(proper)} refs): {list(proper)}")
        modes = collections.Counter()
        for (d, day), seq in zip(items, seqs):
            ks, slot = slot_readings(d, tables)
            full = tuple(day["readings"])
            # residual after removing the proper block (first occurrence)
            comp = None
            if proper and _contains(full, proper):
                idx = next(i for i in range(len(full) - len(proper) + 1)
                           if tuple(full[i:i + len(proper)]) == proper)
                residual = tuple(full[:idx]) + tuple(full[idx + len(proper):])
            else:
                residual = full
            if slot is None:
                slot = ()
            if proper + slot == full:
                comp = "proper+slot"
            elif slot + proper == full:
                comp = "slot+proper"
            elif full == proper:
                comp = "proper-only"
            elif residual == slot:
                comp = f"residual==slot({'?'})"
            else:
                comp = "OTHER"
            modes[comp] += 1
            flag = "" if comp not in ("OTHER",) else "  <<<"
            print(f"  {d} {d.strftime('%a')} slot={ks}:{len(slot)} "
                  f"full={len(full)} resid={len(residual)} -> {comp}{flag}")
        print(f"  modes: {dict(modes)}")


if __name__ == "__main__":
    main()
