"""DEV-ONLY: characterize the days the engine still CANNOT predict (estimates).

For every cached ground-truth day the runtime flags `algorithmic-estimate`, this
tool records:
  * the liturgical zone + a human class for WHY it is unpredictable,
  * the failure MODE against the build buckets (conflict / low-support / no-coord
    / embedded-irregular),
  * the year-type (Easter date, leap year, Easter-offset),
and cross-tabulates so we can see year-type clustering and tell one-off misses
from coordinates that fail consistently.

Emits machine-readable JSON to stdout (consumed when writing reports/).
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from dev.build_table import build, rsig  # noqa: E402
from armenian_lectionary.engine import (  # noqa: E402
    compute_armenian_lectionary, coords_for, WINDOWS, PRECEDENCE,
    calculate_gregorian_easter, EMBEDDED_FIXED,
)

# Most-specific keyspace -> (zone, class) for the dominant failing coordinate.
_ZONE = {
    "E": "Easter core", "AS": "Assumption cycle", "EX": "Exaltation cycle",
    "HE": "Advent", "HEp": "Advent", "TH": "After Nativity", "THp": "Nativity fast",
}


def _easter_offset(d):
    return (d - calculate_gregorian_easter(d.year)).days


def _is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _bucket_diag(days):
    """Rebuild the learning buckets and return key->(n_sigs, n_years) per keyspace
    plus the set of immovable civil dates, so each estimate day's coordinates can
    be explained the same way build_table judged them."""
    valid = {iso: day for iso, day in days.items()
             if day["readings"] or day["feast"]}
    civ = collections.defaultdict(list)
    for iso, day in valid.items():
        d = datetime.date.fromisoformat(iso)
        civ[(d.month, d.day)].append((iso[:4], day))
    diag = {ks: {} for ks in PRECEDENCE}
    fill = collections.defaultdict(lambda: collections.defaultdict(list))
    for iso, day in valid.items():
        d = datetime.date.fromisoformat(iso)
        cs = coords_for(d)
        for ks, key in cs.items():
            if ks not in diag:
                continue
            win = WINDOWS.get(ks)
            if win is not None and not (win[0] <= key <= win[1]):
                continue
            fill[ks][key].append((iso[:4], rsig(day)))
    for ks, keys in fill.items():
        for key, items in keys.items():
            sigs = {s for _, s in items}
            yrs = {y for y, _ in items}
            diag[ks][key] = (len(sigs), len(yrs))
    return diag


def _classify(d, day, diag):
    """Return (zone, klass, mode, coord_label) for an estimate day."""
    md = (d.month, d.day)
    if md in EMBEDDED_FIXED:
        return ("Embedded feast", "Annunciation/eve (irregular)",
                "embedded-irregular", f"{md[0]:02d}-{md[1]:02d}")
    cs = coords_for(d)
    # Walk by precedence; the first in-window coordinate is the dominant slot.
    best = None
    for ks in PRECEDENCE:
        if ks in ("C", "CF") or ks not in cs:
            continue
        key = cs[ks]
        win = WINDOWS.get(ks)
        if win is not None and not (win[0] <= key <= win[1]):
            continue
        nsig, nyear = diag.get(ks, {}).get(key, (0, 0))
        if best is None:
            best = (ks, key, nsig, nyear)
        if nsig >= 2 and nyear >= 2:           # a real cross-year conflict
            best = (ks, key, nsig, nyear)
            break
    if best is None:
        return ("Unanchored", "No applicable coordinate", "no-coord", "-")
    ks, key, nsig, nyear = best
    zone = _ZONE.get(ks)
    if zone is None:
        if ks.startswith("Adv"):
            zone = "Advent"
        elif ks.startswith("Pn"):
            zone = "After Nativity"
        elif ks.startswith("Tr"):
            zone = "Summer (Transfiguration->Assumption)"
        elif ks.startswith("As"):
            zone = "Autumn (Assumption->Exaltation)"
        elif ks.startswith("Ex"):
            zone = "Post-Exaltation->Advent"
        else:
            zone = ks
    if nsig >= 2:
        mode = "conflict"
        klass = f"{zone}: cross-year disagreement"
    elif nyear < 2:
        mode = "low-support"
        klass = f"{zone}: single-year (low support)"
    else:
        mode = "no-coord"
        klass = f"{zone}: no shipped coordinate"
    return (zone, klass, mode, f"{ks}={key}")


def main():
    days = load_all()
    diag = _bucket_diag(days)
    recs = []
    # Per civil-date, tally ok/wrong/estimate across years for the consistency view.
    by_civil = collections.defaultdict(lambda: {"ok": [], "wrong": [], "est": []})
    for iso, day in sorted(days.items()):
        if not day["readings"] and not day["feast"]:
            continue
        d = datetime.date.fromisoformat(iso)
        res = compute_armenian_lectionary(d)
        status = ("est" if res["Source"] == "algorithmic-estimate"
                  else "ok" if res["ReadingsList"] == list(day["readings"])
                  else "wrong")
        by_civil[(d.month, d.day)][status].append(iso[:4])
        if status != "est":
            continue
        e = calculate_gregorian_easter(d.year)
        zone, klass, mode, coord = _classify(d, day, diag)
        recs.append({
            "iso": iso, "year": d.year, "month": d.month,
            "weekday": d.strftime("%a"),
            "feast": (day["feast"] or res["Liturgical Day"]).strip()[:60],
            "season": res["Season"],
            "zone": zone, "class": klass, "mode": mode, "coord": coord,
            "easter": e.strftime("%m-%d"), "easter_offset": _easter_offset(d),
            "leap": _is_leap(d.year),
        })
    out = {"records": recs,
           "civil": {f"{m:02d}-{dd:02d}": v for (m, dd), v in by_civil.items()}}
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
