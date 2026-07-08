"""DEV-ONLY: mine the Fast-of-the-Assumption Wed/Fri lectio-continua.

The post-Transfiguration Wed/Fri fast carries a sequential Pauline-epistle +
Matthew/Mark-gospel continua that marches by FAST-DAY position. It is clean (one
reading-set per position) for the early indices -- which already ship validated
via the summer TrFer/TrFerL grid -- but its tail runs THROUGH the Fast of the
Assumption (a window no grid slot covers), where the long-summer years insert
extra continua days. There a plain forward index carries 2-3 variants, so the
strict pipeline cannot ship it AND forcing it into the validated TrFer bucket
pollutes the clean summer positions (verified: a net loss).

Instead we mine the MODAL reading-set per (summer-span, forward-Wed/Fri-index,
weekday) bucket into a separate artifact consumed only by the runtime's labeled
generative-continua best-guess tier (never the validated table). Span-banding
the index lifts the guess to ~85% correct on the otherwise-blank fast days.

Usage:
  python dev/build_continua.py        # regenerate artifact + print diagnostics
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from armenian_lectionary.engine import anchors, _count_wf, CONTINUA_PATH  # noqa: E402

ARTIFACT = CONTINUA_PATH  # shipped package data (armenian_lectionary/data/)


def _summer_span(year):
    """Summer length class = (summer eve - Transfiguration).days, matching the
    runtime TrFerL span (eve = Assumption Sunday - 7)."""
    a = anchors(year)
    tr = a["E"] + datetime.timedelta(days=98)
    asun = a["AS"]
    return ((asun - datetime.timedelta(days=7)) - tr).days


def collect(days):
    """{ (easter_md, span, idx, wd): Counter(readings_tuple) } over every
    Transfiguration->Assumption Wed/Fri day (summer grid + the Fast-of-Assumption tail).

    The bucket is banded by the year's Gregorian Easter date as well as the summer span:
    at a few tail indices the continua carries a genuine per-year-type variant that the
    same (span, idx) conflates -- e.g. idx 7 of span 28 splits 2Tim 2.20-26 (Easter 04-05,
    the Թ type) from 1Tim 5.17-6.5 (Easter 04-04), where a span-only modal shipped the
    wrong one to 2015/2026. Easter-md banding separates them; unambiguous buckets are
    unaffected (they just carry the Easter tag too)."""
    grp = collections.defaultdict(collections.Counter)
    for y in sorted({int(iso[:4]) for iso in days}):
        a = anchors(y)
        tr = a["E"] + datetime.timedelta(days=98)
        asun = a["AS"]
        span = _summer_span(y)
        emd = f"{a['E'].month:02d}-{a['E'].day:02d}"
        d = tr + datetime.timedelta(days=1)
        while d < asun:
            day = days.get(d.isoformat())
            if day and day["readings"] and d.weekday() in (2, 4):
                idx = _count_wf(tr, d)
                grp[(emd, span, idx, d.weekday())][tuple(day["readings"])] += 1
            d += datetime.timedelta(days=1)
    return grp


def build(days):
    grp = collect(days)
    buckets = {}
    multi = 0
    for (emd, span, idx, wd), counter in grp.items():
        if len(counter) > 1:
            multi += 1
        readings, _ = counter.most_common(1)[0]
        buckets[f"{emd}:{span}:{idx}:{wd}"] = list(readings)
    section = {
        "meta": {
            "source": "Mined from sacredtradition.am Transfiguration->Assumption "
                      "Wed/Fri continua; MODAL reading per (summer-span, forward "
                      "Wed/Fri index, weekday). Best-guess only -- consumed by the "
                      "generative-continua tier, never the validated table.",
            "buckets": len(buckets),
            "ambiguous_buckets": multi,
        },
        "buckets": buckets,
    }
    return section


def emit(combined):
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=1)
    return ARTIFACT


if __name__ == "__main__":
    days = load_all()
    section = build(days)
    path = emit({"TrFast": section})
    print(f"Mined {section['meta']['buckets']} (span,idx,wd) continua buckets "
          f"({section['meta']['ambiguous_buckets']} ambiguous -> modal) -> {path}")
