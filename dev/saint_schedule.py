"""DEV-ONLY: mine the per-zone saint schedules into one static artifact.

Every variable-gap ferial zone lays a CANONICAL ORDERED list of saints onto
whichever free Mon/Tue/Thu/Sat weekdays a given year offers:

  * PN -- post-Nativity (Theophany octave -> eve of the Fast of Catechumens),
  * Tr -- summer (Transfiguration -> eve of the Fast of the Assumption),
  * As -- autumn (Assumption -> eve of the Fast of the Holy Cross),
  * Ex -- post-Exaltation (Exaltation -> eve of Advent / Heesnak).

A single merge or drop shifts every downstream saint to a different weekday, so
the calendar-grid coordinate ({Zone}SatL = "{span}:{week}:{weekday}") splits one
saint across many grid keys -- the same reading-set lands on Thu one year and Tue
the next, each key seeing only one year of support and dropped by the strict
cross-year filter.

This tool reverse-engineers each zone's schedule so the runtime can key each
physical day by the SENIOR SAINT'S IDENTITY instead of its drifting grid position:

  1. Collect every free saint-weekday in the zone with non-empty readings.
  2. Cluster by readings_tuple -- the readings ARE the identity (label spellings
     are noisy: "Eugenios"/"Eugenius"/"Eugenia"). Each distinct reading-set is a
     candidate saint id; an alias map records every observed label -> id.
  3. Derive, per id: forward order (median ordinal), whether it pins to Saturday,
     its solar date window (for pins), and an optional flag (rare tail saints).
     The head/tail order split is re-derived PER ZONE from that zone's own free-
     slot distribution (median slots + 1), not a winter-tuned constant.
  4. Emit dev/saint_schedule.json keyed by zone -- ordering / pins / aliases ONLY,
     never readings. Readings stay in lectionary_data.json under the {Zone}Saint
     keyspaces, learned by the existing strict pipeline (keeps the 0-wrong
     guarantee).

Usage:
  python dev/saint_schedule.py          # regenerate artifact + print diagnostics
"""

import collections
import datetime
import json
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from dev.slot_model import _fixed_dates  # noqa: E402
from lectionary import (  # noqa: E402
    _SAINT_ZONES, _SAINT_WD, _next_saint_weekday, EMBEDDED_FIXED,
)

ZONES = ("PN", "Tr", "As", "Ex")

ARTIFACT = os.path.join(os.path.dirname(__file__), os.pardir, "saint_schedule.json")  # shipped at repo root

# Sibling artifact carrying the readings the clustering already computes, keyed
# {zone: {saint_id: [readings]}}. Kept SEPARATE from saint_schedule.json so the
# schedule stays readings-free and the strict cross-year build path is untouched.
# Consumed only by the runtime's labeled generative best-guess tier (never the
# validated table), where a placed saint ships its intrinsic readings even when
# its coordinate has <2 cross-year support (extreme-Easter / floating saints).
READINGS_ARTIFACT = os.path.join(os.path.dirname(__file__), os.pardir, "saint_readings.json")  # shipped at repo root

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


def collect(days, zone):
    """year-keyed list of (date, weekday, label, readings_tuple) for every free
    saint-weekday with readings in `zone` (John/embedded/civil removed).

    Window and the John-the-Forerunner skip come from the runtime zone descriptor
    so the mined slots match the replay's slots exactly."""
    fixed = _fixed_dates(days)
    z = _SAINT_ZONES[zone]
    years = sorted({iso[:4] for iso in days})
    per_year = {}
    for y in years:
        yr = int(y)
        start, end = z["window"](yr)
        john = (_next_saint_weekday(datetime.date(yr, 1, 14))
                if z["skip_john"] else None)
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
            "readings": list(readings),   # the reading-set that DEFINES this id
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
TAIL_MIN_YEARS = 5      # support to trust a backward-anchored tail saint


def _zone_split(per_year):
    """The head/tail order boundary for a zone, re-derived from that zone's own
    free-slot distribution: head saints sit at order < split (laid forward from
    the window start), tail saints at order >= split (laid backward). The boundary
    is (median free-slots per year) + 1, which reproduces the winter-tuned 9 for
    PN (median 8) and scales to the wider summer/autumn/post-Exaltation zones.
    Falls back to 9 if the zone has no populated years."""
    counts = [len(r) for r in per_year.values() if r]
    return int(statistics.median(counts)) + 1 if counts else 9


def derive(ids, split):
    """Per id, derive order / anchor class / solar window / weekday, using the
    zone's own head/tail order `split`."""
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
        elif len(wds) == 1 and n >= TAIL_MIN_YEARS and order >= split:
            entry["anchor"] = "tail"
            entry["weekday"] = _WDNAME[next(iter(wds))]
        elif n >= HEAD_MIN_YEARS and order < split:
            entry["anchor"] = "head"
        else:
            entry["anchor"] = "skip"
        sched.append(entry)
    sched.sort(key=lambda e: (e["order"], -e["support_years"]))
    return sched


_ZONE_DESC = {
    "PN": "post-Nativity (Theophany octave -> eve of Fast of Catechumens)",
    "Tr": "summer (Transfiguration -> eve of Fast of the Assumption)",
    "As": "autumn (Assumption -> eve of Fast of the Holy Cross)",
    "Ex": "post-Exaltation (Exaltation -> eve of Advent / Heesnak)",
}


def build_zone(days, zone):
    """Mine one zone -> its artifact section {meta, aliases, sequence}."""
    per_year = collect(days, zone)
    ids, aliases = canonicalize(per_year)
    split = _zone_split(per_year)
    sched = derive(ids, split)
    section = {
        "meta": {
            "source": "Mined from sacredtradition.am %s saint-weekdays "
                      "(ordering/pins/aliases only; readings live in "
                      "lectionary_data.json under the zone's Saint keyspace)."
                      % _ZONE_DESC[zone],
            "years_mined": sorted(per_year),
            "head_tail_split": split,
        },
        "aliases": aliases,
        "sequence": sched,
    }
    return section, per_year, ids


def emit(combined):
    with open(ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=1)
    return ARTIFACT


def emit_readings(readings_combined):
    with open(READINGS_ARTIFACT, "w", encoding="utf-8") as f:
        json.dump(readings_combined, f, ensure_ascii=False, indent=1)
    return READINGS_ARTIFACT


def _report(zone, per_year, ids, sched, split):
    print(f"\n========== zone {zone}: {_ZONE_DESC[zone]} ==========")
    print(f"Mined {sum(len(r) for r in per_year.values())} saint-days over "
          f"{len([y for y in per_year if per_year[y]])} populated years -> "
          f"{len(ids)} reading-set identities (head/tail split = {split}).\n")
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
    combined = {}
    readings_combined = {}
    for zone in ZONES:
        section, per_year, ids = build_zone(days, zone)
        combined[zone] = section
        readings_combined[zone] = {sid: info["readings"]
                                   for sid, info in ids.items()}
        _report(zone, per_year, ids, section["sequence"],
                section["meta"]["head_tail_split"])
    path = emit(combined)
    rpath = emit_readings(readings_combined)
    n_anchored = sum(1 for z in combined.values() for e in z["sequence"]
                     if e["anchor"] != "skip")
    n_ids = sum(len(z) for z in readings_combined.values())
    print(f"\nEmitted combined artifact ({n_anchored} anchored ids across "
          f"{len(ZONES)} zones) -> {path}")
    print(f"Emitted saint-readings artifact ({n_ids} reading-sets) -> {rpath}")
