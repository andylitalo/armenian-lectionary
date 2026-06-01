"""DEV-ONLY: reverse-engineer & validate the post-Nativity slot-consumption model.

Mechanism (see memory lectionary-winter-mechanism): in the window from the day
after the Nativity octave (Jan 14) up to where the Easter-anchored Fast of
Catechumens takes over (~Easter-70), days are filled as:
  - Sunday            -> "Nth Sunday after Nativity"  (numbered track)
  - Wednesday/Friday  -> "Fast day"                   (ferial fast track)
  - Mon/Tue/Thu/Sat   -> next entry of an ordered saint list

This script extracts the ordered saint list and the numbered-Sunday readings
from the years with the longest windows, then validates the consumption model
(saints + Sundays) against every year, reporting match accuracy.
"""

import collections
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from lectionary import calculate_gregorian_easter  # noqa: E402

SAINT_WEEKDAYS = {0, 1, 3, 5}   # Mon, Tue, Thu, Sat
FAST_WEEKDAYS = {2, 4}          # Wed, Fri


def window(year):
    """[start, end) of the post-Nativity ferial window for a civil year."""
    start = datetime.date(year, 1, 14)          # day after the Nativity octave
    end = calculate_gregorian_easter(year) + datetime.timedelta(days=-70)
    return start, end


def walk(days, year):
    """Yield (date, slot_kind, sunday_index, readings, feast) over the window."""
    start, end = window(year)
    d = start
    sun = 0
    while d < end:
        day = days.get(d.isoformat())
        wd = d.weekday()
        if wd == 6:
            sun += 1
            kind = ("SUN", sun)
        elif wd in FAST_WEEKDAYS:
            kind = ("FAST", None)
        else:
            kind = ("SAINT", None)
        if day and (day["readings"] or day["feast"]):
            yield d, kind, day
        d += datetime.timedelta(days=1)


def extract(days, years):
    """Build ordered saint list and numbered-Sunday table from given years."""
    # saint list: take the longest year's ordered saints.
    best_saints = []
    sundays = {}
    for year in years:
        saints = []
        for d, (kind, idx), day in walk(days, year):
            if kind == "SAINT":
                saints.append((day["feast"].strip(), tuple(day["readings"])))
            elif kind == "SUN":
                sundays.setdefault(idx, (day["feast"].strip(),
                                         tuple(day["readings"])))
        if len(saints) > len(best_saints):
            best_saints = saints
    return best_saints, sundays


def validate(days, years, saints, sundays):
    ok = miss = 0
    miss_kind = collections.Counter()
    samples = []
    for year in years:
        si = 0
        for d, (kind, idx), day in walk(days, year):
            truth = tuple(day["readings"])
            if kind == "SAINT":
                pred = saints[si][1] if si < len(saints) else None
                si += 1
            elif kind == "SUN":
                pred = sundays.get(idx, (None, None))[1]
            else:  # FAST -- not modeled here
                continue
            if pred == truth:
                ok += 1
            else:
                miss += 1
                miss_kind[kind[0]] += 1
                if len(samples) < 20:
                    samples.append((d.isoformat(), kind, day["feast"][:30],
                                    pred, truth))
    return ok, miss, miss_kind, samples


if __name__ == "__main__":
    days = load_all()
    years = list(range(2014, 2027))
    saints, sundays = extract(days, years)
    print(f"Ordered saint list length: {len(saints)}")
    for i, (f, r) in enumerate(saints):
        print(f"  {i:2} {f[:42]:42} {list(r)}")
    print(f"\nNumbered Sundays after Nativity: {sorted(sundays)}")
    for n in sorted(sundays):
        print(f"  Sun {n}: {sundays[n][0][:40]} {list(sundays[n][1])}")
    ok, miss, mk, samples = validate(days, years, saints, sundays)
    tot = ok + miss
    print(f"\nConsumption model (saints+Sundays) over {tot} days: "
          f"{ok} ok ({ok/tot*100:.1f}%), {miss} miss {dict(mk)}")
    for s in samples:
        print(f"  MISS {s[0]} {s[1]} {s[2]}\n     pred={s[3]}\n     true={s[4]}")
