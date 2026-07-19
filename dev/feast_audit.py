"""DEV-ONLY audit of the engine's feast/fast NAME against the sacredtradition.am scrape.

Drives the TDD loop behind tests/test_feast.py. For every cached day (2001-2026) it
compares the commemoration component (dev/feast_names.commemoration_of, canonicalized
by dev/source_corrections.canonical_commem) of the engine's "Liturgical Day" against the
scraped feast, and prints any residual mismatches grouped by Source tier. Not used by
the app at runtime.

    python dev/feast_audit.py
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                        # noqa: E402
from dev.feast_names import commemoration_of                            # noqa: E402
from dev.source_corrections import canonical_commem                     # noqa: E402
from armenian_lectionary.engine import compute_armenian_lectionary      # noqa: E402


def _commem(feast_str):
    """Canonical, casefolded commemoration used for comparison (both sides)."""
    return canonical_commem(commemoration_of(feast_str)).casefold()


def audit():
    days = load_all()
    by_tier = collections.defaultdict(list)
    unrecognized = []
    exact = total = 0
    for iso in sorted(days):
        feast = (days[iso].get("feast") or "").strip()
        if not feast:
            continue
        total += 1
        src_commem = canonical_commem(commemoration_of(feast))
        if "\x00" in src_commem:
            unrecognized.append((iso, feast))
        res = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
        got = res["Liturgical Day"]
        if _commem(feast) == _commem(got):
            exact += 1
        else:
            by_tier[res["Source"]].append(
                (iso, src_commem, canonical_commem(commemoration_of(got))))

    residual = sum(len(v) for v in by_tier.values())
    print(f"days with a scraped feast : {total}")
    print(f"commemoration exact match : {exact} ({100*exact/total:.2f}%)")
    print(f"residual mismatches       : {residual}")
    if unrecognized:
        print(f"\n!! {len(unrecognized)} feast strings the extractor could not segment:")
        for iso, f in unrecognized[:20]:
            print(f"   {iso}  {f!r}")
    for tier in sorted(by_tier, key=lambda t: -len(by_tier[t])):
        print(f"\n===== {tier}: {len(by_tier[tier])} =====")
        for iso, s, g in by_tier[tier]:
            print(f"  {iso}\n       src={s[:80]!r}\n       got={g[:80]!r}")


if __name__ == "__main__":
    audit()
