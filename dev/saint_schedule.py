"""DEV-ONLY: mine the post-Nativity saint schedule into a static artifact.

The winter post-Nativity saint-weekdays (Mon/Tue/Thu/Sat between the Theophany
octave and the eve of the Fast of Catechumens) carry a CANONICAL ORDERED list of
saints that is laid onto whichever free weekdays a given year offers. A single
merge or drop shifts every downstream saint to a different weekday, so the
calendar-grid coordinate (PnSatL = "{pn_len}:{nsun}:{weekday}") splits one saint
across many grid keys -- the same reading-set lands on Thu one year and Tue the
next, each key seeing only one year of support and therefore dropped by the
strict cross-year filter.

This tool reverse-engineers the schedule so the runtime can key each physical
day by the SENIOR SAINT'S IDENTITY instead of its drifting grid position:

  1. Collect every post-Nativity free saint-weekday with non-empty readings.
  2. Cluster by readings_tuple -- the readings ARE the identity (label spellings
     are noisy: "Eugenios"/"Eugenius"/"Eugenia"). Each distinct reading-set is a
     candidate saint id; an alias map records every observed label -> id.
  3. Derive, per id: forward order (median ordinal), whether it pins to Saturday,
     its solar date window (for pins), and an optional flag (rare tail saints).
  4. Emit dev/postnat_schedule.json -- ordering / pins / aliases ONLY, never
     readings. Readings stay in lectionary_data.json under the PnSaint keyspace,
     learned by the existing strict pipeline (this keeps the 0-wrong guarantee).

Usage:
  python dev/saint_schedule.py          # regenerate artifact + print diagnostics
"""

import collections
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from dev.slot_model import _fixed_dates  # noqa: E402
from lectionary import (  # noqa: E402
    winter_window, _SAINT_WD, _next_saint_weekday, EMBEDDED_FIXED,
)

ARTIFACT = os.path.join(os.path.dirname(__file__), "postnat_schedule.json")

# Ids whose reading-set genuinely pins to a particular Saturday (high-rank
# fathers). Detected automatically (weekday==Sat in >= N-1 of N years) but a
# minimum support keeps two-year noise (Sahak, the 150 Fathers) out of the pin
# list -- those land on a pinned Saturday too but with their own readings, so
# they are left unassigned and contaminate nothing they would not already.
PIN_MIN_YEARS = 5


def _slug(label):
    """A short, stable id slug from a feast label."""
    label = label.lower()
    label = re.sub(r"^(the\s+|saints?\s+|holy\s+|commemoration of\s+)+", "", label)
    label = re.sub(r"[^a-z0-9]+", "_", label).strip("_")
    return "_".join(label.split("_")[:3]) or "saint"


def collect(days):
    """year-keyed list of (date, weekday, label, readings_tuple) for every
    post-Nativity free saint-weekday with readings (John/embedded/civil removed)."""
    fixed = _fixed_dates(days)
    years = sorted({iso[:4] for iso in days})
    per_year = {}
    for y in years:
        yr = int(y)
        start, end = winter_window(yr)["PN"]
        john = _next_saint_weekday(datetime.date(yr, 1, 14))
        rows = []
        d = start
        while d <= end:
            md = (d.month, d.day)
            if (d.weekday() in _SAINT_WD and d != john
                    and md not in EMBEDDED_FIXED and md not in fixed):
                day = days.get(d.isoformat())
                if day and day["readings"]:
                    rows.append((d, d.weekday(), day["feast"].strip(),
                                 tuple(day["readings"])))
            d += datetime.timedelta(days=1)
        per_year[y] = rows
    return per_year


def canonicalize(per_year):
    """Cluster occurrences by readings_tuple into saint ids.

    Returns (ids, aliases) where ids maps id -> {label, occurrences:[(year,date,
    weekday,ordinal)], ...} and aliases maps observed label -> id."""
    clusters = collections.defaultdict(list)   # readings -> [(year, date, wd, label, ordinal)]
    for y, rows in per_year.items():
        for ordinal, (d, wd, label, readings) in enumerate(rows):
            clusters[readings].append((y, d, wd, label, ordinal))

    # Stable id assignment: order clusters by median date, slug the modal label,
    # disambiguate collisions with a numeric suffix.
    def median_date(occ):
        ds = sorted(d for _, d, _, _, _ in occ)
        return ds[len(ds) // 2]

    ids = {}
    aliases = {}
    used = set()
    for readings, occ in sorted(clusters.items(), key=lambda kv: median_date(kv[1])):
        labels = collections.Counter(l for _, _, _, l, _ in occ)
        modal = labels.most_common(1)[0][0]
        base = _slug(modal)
        sid = base
        n = 2
        while sid in used:
            sid = f"{base}_{n}"
            n += 1
        used.add(sid)
        ids[sid] = {
            "label": modal,
            "occ": [(y, d, wd, ordinal) for y, d, wd, _, ordinal in occ],
            "labels": dict(labels),
        }
        for lab in labels:
            aliases.setdefault(lab, sid)
    return ids, aliases


_WDNAME = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# Classification thresholds. The schedule has three robust anchor classes plus an
# unassigned remainder:
#   pin:Sat  high-rank Fathers locked to a particular Saturday (solar window).
#   head     the opening flow block laid forward from the window start; stable
#            because the optional minor saints only ever appear AFTER it.
#   tail     the closing block, each locked to a single weekday and laid BACKWARD
#            (last free <weekday>) because its forward ordinal drifts with the
#            count of optional middle saints.
#   skip     low-support / middle saints (Andrew, Adrian, one-offs) -- left
#            unassigned for now (they stay on the grid keys / estimate).
HEAD_MIN_YEARS = 7      # support to trust a saint in the forward head block
HEAD_MAX_ORDER = 9      # head saints sit before the first pinned Saturday tail
TAIL_MIN_YEARS = 5      # support to trust a backward-anchored tail saint
TAIL_MIN_ORDER = 9      # tail saints come after the mid-window pinned Saturday


def derive(ids):
    """Per id, derive order / anchor class / solar window / weekday."""
    sched = []
    for sid, info in ids.items():
        occ = info["occ"]
        n = len({y for y, _, _, _ in occ})
        ords = sorted(o for _, _, _, o in occ)
        order = ords[len(ords) // 2]                 # median forward ordinal
        wds = {wd for _, _, wd, _ in occ}
        sats = sum(1 for _, _, wd, _ in occ if wd == 5)
        dates = sorted((d.month, d.day) for _, d, _, _ in occ)
        lo, hi = dates[0], dates[-1]
        entry = {"id": sid, "label": info["label"], "order": order,
                 "support_years": n}
        if sats >= len(occ) - 1 and n >= PIN_MIN_YEARS:
            entry["anchor"] = "pin:Sat"
            entry["date_lo"] = f"{lo[0]:02d}-{lo[1]:02d}"
            entry["date_hi"] = f"{hi[0]:02d}-{hi[1]:02d}"
        elif len(wds) == 1 and n >= TAIL_MIN_YEARS and order >= TAIL_MIN_ORDER:
            entry["anchor"] = "tail"
            entry["weekday"] = _WDNAME[next(iter(wds))]
        elif n >= HEAD_MIN_YEARS and order < HEAD_MAX_ORDER:
            entry["anchor"] = "head"
        else:
            entry["anchor"] = "skip"
        sched.append(entry)
    sched.sort(key=lambda e: (e["order"], -e["support_years"]))
    return sched


def emit(per_year, ids, aliases, sched):
    years = sorted(per_year)
    artifact = {
        "meta": {
            "source": "Mined from sacredtradition.am post-Nativity saint-weekdays "
                      "(ordering/pins/aliases only; readings live in "
                      "lectionary_data.json under PnSaint).",
            "years_mined": years,
        },
        "aliases": aliases,
        "sequence": sched,
    }
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=1)
    return ARTIFACT


def _report(per_year, ids, sched):
    print(f"Mined {sum(len(r) for r in per_year.values())} saint-days over "
          f"{len(per_year)} years -> {len(ids)} reading-set identities.\n")
    print(f"{'id':28} {'ord':>3} {'yrs':>3} {'anchor':9} detail")
    for e in sched:
        if e["anchor"] == "pin:Sat":
            det = f"{e['date_lo']}..{e['date_hi']}"
        elif e["anchor"] == "tail":
            det = e["weekday"]
        else:
            det = ""
        print(f"  {e['id']:26} {e['order']:>3} {e['support_years']:>3} "
              f"{e['anchor']:9} {det}")
    # Cross-year order inconsistency: ids whose forward ordinal spreads widely.
    print("\nForward-ordinal spread per id (min..max; wide = drift / merges):")
    for e in sched:
        info = ids[e["id"]]
        ords = [o for _, _, _, o in info["occ"]]
        if max(ords) - min(ords) >= 2:
            print(f"  {e['id']:26} {min(ords)}..{max(ords)}  "
                  f"({e['support_years']}y, {e['anchor']})")


if __name__ == "__main__":
    days = load_all()
    per_year = collect(days)
    ids, aliases = canonicalize(per_year)
    sched = derive(ids)
    path = emit(per_year, ids, aliases, sched)
    _report(per_year, ids, sched)
    print(f"\nEmitted artifact -> {path}")
