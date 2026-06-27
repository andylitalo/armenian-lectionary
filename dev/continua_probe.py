"""DEV-ONLY: test the Advent->Theophany lectio-continua hypothesis.

Walks each winter (Heesnak -> Theophany) and extracts, in calendar order, the
Hebrews epistle + Luke gospel of every day that bears a continua reading. If the
ordered sequence is identical across years, the continua can be keyed by a
position index (count of continua-bearing days from the start).
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from lectionary import sunday_closest_to  # noqa: E402


def heb(refs):
    for r in refs:
        if "Hebrews" in r:
            return r.split("Hebrews")[1].strip()
    return None


def luke(refs):
    for r in refs:
        if r.startswith("Luke"):
            return r.replace("Luke", "").strip()
    return None


def main():
    days = load_all()
    seqs = {}
    for y in range(2001, 2026):
        he = sunday_closest_to(y, 11, 18)
        th = datetime.date(y + 1, 1, 6)
        seq = []
        d = he + datetime.timedelta(days=1)
        while d < th:
            day = days.get(d.isoformat())
            if day and (day["readings"] or day["feast"]):
                h = heb(day["readings"])
                if h:
                    seq.append((d.strftime("%m-%d"), d.strftime("%a"), h,
                                luke(day["readings"]), day["feast"].strip()[:22]))
            d += datetime.timedelta(days=1)
        seqs[y] = seq

    # Print the Hebrews-only ordered sequence per year to eyeball alignment.
    for y in [2005, 2014, 2016, 2019, 2024]:
        print(f"\n=== {y} (Heb sequence, {len(seqs[y])} continua days) ===")
        for i, (md, wd, h, lk, f) in enumerate(seqs[y]):
            print(f"  [{i:2}] {md} {wd} Heb {h:14} Luke {str(lk):12} {f}")


if __name__ == "__main__":
    main()
