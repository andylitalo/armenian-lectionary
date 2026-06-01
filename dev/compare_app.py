"""DEV-ONLY: compare the RUNTIME engine output to ground truth, day by day.

Exercises lectionary.compute_armenian_lectionary (exactly what the app serves)
against every cached reference day and reports exact reading-match accuracy,
broken down by source (validated-table vs algorithmic-estimate) and by month.
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from lectionary import compute_armenian_lectionary  # noqa: E402


def main():
    days = load_all()
    ok = wrong = est = 0
    wrong_by_month = collections.Counter()
    est_by_month = collections.Counter()
    wrong_samples = []
    for iso, day in sorted(days.items()):
        if not day["readings"] and not day["feast"]:
            continue
        d = datetime.date.fromisoformat(iso)
        res = compute_armenian_lectionary(d)
        truth = list(day["readings"])
        if res["Source"] == "algorithmic-estimate":
            est += 1
            est_by_month[d.month] += 1
        elif res["ReadingsList"] == truth:
            ok += 1
        else:
            wrong += 1
            wrong_by_month[d.month] += 1
            if len(wrong_samples) < 25:
                wrong_samples.append((iso, res["ReadingsList"], truth))
    total = ok + wrong + est
    covered = ok + wrong
    print(f"Runtime engine vs ground truth over {total} days (2014-2026):")
    print(f"  exact match:          {ok}  ({ok/total*100:.1f}% of all days)")
    print(f"  wrong (table hit):    {wrong}")
    print(f"  estimate (no data):   {est}  ({est/total*100:.1f}%)")
    if covered:
        print(f"  accuracy WHERE COVERED: {ok}/{covered} = {ok/covered*100:.2f}%")
    print(f"\n  estimate days by month: "
          f"{ {m: est_by_month[m] for m in range(1,13) if est_by_month[m]} }")
    if wrong:
        print(f"  wrong days by month: {dict(wrong_by_month)}")
        print("  wrong samples:")
        for iso, got, want in wrong_samples:
            print(f"    {iso}\n      got : {got}\n      want: {want}")


if __name__ == "__main__":
    main()
