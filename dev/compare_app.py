"""DEV-ONLY: compare the RUNTIME engine output to ground truth, day by day.

Exercises lectionary.compute_armenian_lectionary (exactly what the app serves)
against every cached reference day and reports a CONFIDENCE LADDER:

  * validated  (validated-table / validated-composite) -- structurally 0-wrong;
                a mismatch here is a HARD failure (the strict-shipping guarantee).
  * resolved   (holy-week-composite) -- the Annunciation Holy-Week resolver;
                aims to be validated, tracked separately until proven.
  * generative (generative-saint / generative-continua) -- labeled best-guess;
                a mismatch is NOT a failure, just an under-sampled day; its
                cache-accuracy is an explicit, tracked number.
  * blank      (algorithmic-estimate) -- no readings shipped at all.
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from armenian_lectionary.engine import compute_armenian_lectionary  # noqa: E402

VALIDATED = {"validated-table", "validated-composite"}
RESOLVED = {"holy-week-composite"}
GENERATIVE = {"generative-saint", "generative-continua"}


def tally(days):
    """Walk every cached day -> a per-tier {exact, mismatch} ledger + blanks."""
    t = collections.defaultdict(lambda: {"exact": 0, "mismatch": 0})
    blank = 0
    blank_by_month = collections.Counter()
    val_wrong_samples = []
    gen_mismatch_samples = []
    for iso, day in sorted(days.items()):
        if not day["readings"] and not day["feast"]:
            continue
        d = datetime.date.fromisoformat(iso)
        res = compute_armenian_lectionary(d)
        src = res["Source"]
        truth = list(day["readings"])
        if src == "algorithmic-estimate":
            blank += 1
            blank_by_month[d.month] += 1
            continue
        tier = ("validated" if src in VALIDATED else
                "resolved" if src in RESOLVED else
                "generative" if src in GENERATIVE else "other")
        if res["ReadingsList"] == truth:
            t[tier]["exact"] += 1
        else:
            t[tier]["mismatch"] += 1
            if tier == "validated" and len(val_wrong_samples) < 25:
                val_wrong_samples.append((iso, res["ReadingsList"], truth))
            elif tier == "generative" and len(gen_mismatch_samples) < 25:
                gen_mismatch_samples.append((iso, res["ReadingsList"], truth))
    return t, blank, blank_by_month, val_wrong_samples, gen_mismatch_samples


def main():
    days = load_all()
    t, blank, blank_by_month, val_wrong, gen_mismatch = tally(days)
    total = blank + sum(v["exact"] + v["mismatch"] for v in t.values())
    val = t["validated"]
    res = t["resolved"]
    gen = t["generative"]
    val_exact = val["exact"]
    overall_exact = sum(v["exact"] for v in t.values())
    print(f"Runtime engine vs ground truth over {total} days (2001-2026):")
    print(f"  VALIDATED   exact: {val_exact:5d}   WRONG: {val['mismatch']}  "
          f"(hard invariant: WRONG must be 0)")
    print(f"  RESOLVED    exact: {res['exact']:5d}   mismatch: {res['mismatch']}")
    print(f"  GENERATIVE  exact: {gen['exact']:5d}   mismatch: {gen['mismatch']}"
          + (f"   ({gen['exact']/(gen['exact']+gen['mismatch'])*100:.1f}% of "
             f"best-guess days correct)" if gen["exact"] + gen["mismatch"] else ""))
    print(f"  BLANK (no readings): {blank}")
    print(f"\n  overall exact match: {overall_exact}/{total} = "
          f"{overall_exact/total*100:.2f}%")
    print(f"  coverage (any readings shipped): {total-blank}/{total} = "
          f"{(total-blank)/total*100:.2f}%")
    if blank_by_month:
        print(f"  blank days by month: "
              f"{ {m: blank_by_month[m] for m in range(1,13) if blank_by_month[m]} }")
    if val["mismatch"]:
        print("\n  !!! VALIDATED-TIER WRONG (must be empty):")
        for iso, got, want in val_wrong:
            print(f"    {iso}\n      got : {got}\n      want: {want}")
    if gen["mismatch"]:
        print("\n  generative-tier mismatches (best-guess misses, informational):")
        for iso, got, want in gen_mismatch[:8]:
            print(f"    {iso}\n      got : {got}\n      want: {want}")


if __name__ == "__main__":
    main()
