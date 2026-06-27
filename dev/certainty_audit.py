"""DEV-ONLY: grade the *certainty* of the engine's predictions for a FUTURE year.

The shipped engine is empirically 0-wrong over the 2001-2026 ground-truth cache
because it ships a reading only when every cached year that hit the same
liturgical coordinate agreed (strict cross-year validation). This tool answers the
next question: for a year whose Easter date was *never observed* (e.g. 2027, Easter
Mar 28), which per-day predictions are **provably correct** and which **may be wrong
or unavailable**?

The decisive idea is INTERPOLATION vs EXTRAPOLATION of the target year's Easter /
`pn_len` against the observed cache (Easter range Mar 23 2008 .. Apr 24 2011). A
reading whose coordinate does not depend on Easter at all (civil/solar feasts), or a
plain Easter-offset reading that is invariant across the *entire* observed Easter
span that brackets the target, transfers with certainty. A banded/grid coordinate
whose band the target merely shares with observed years is high-confidence by
interpolation but not proven. Everything else (single-sample bands, generative
best-guess, estimate) is explicitly uncertain.

This refines -- it does not replace -- the engine's own `Source` tag. `Source`
says whether a coordinate was validated *in the cache*; this tool says whether that
validation *transfers* to the unseen target year, which depends on WHICH coordinate
matched (keyspaces differ in year-type sensitivity).

Run:  python dev/certainty_audit.py 2027          # one year, JSON to stdout
      python dev/certainty_audit.py 2027 2040      # a horizon, summary table to stderr
      python dev/certainty_audit.py --summary 2027  # only the stderr summary
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from dev.predictability_audit import _occurrences  # noqa: E402
from lectionary import (  # noqa: E402
    compute_armenian_lectionary, _lookup, calculate_gregorian_easter,
    _pn_len, _easter_band,
)

# --------------------------------------------------------------------------- #
# Keyspace year-type-sensitivity classes (see module docstring + plan).
# --------------------------------------------------------------------------- #

# Coordinates that do NOT depend on the date of Easter: civil immovable feasts
# ("C", "PnOct" = the Jan-13 Naming octave) and the solar-anchored season counts
# ("Sunday closest to" a fixed civil date, or a fixed date itself). Their readings
# cannot be perturbed by an unseen Easter, so a validated hit transfers as-is.
EASTER_INDEP_KS = {"C", "PnOct", "AS", "EX", "HE", "HEp", "TH", "THp"}

# Coordinates built *because* the reading varies by year-type band: the Easter-band
# core sub-key, the Advent-length sub-keys, and the Annunciation Easter-offset key.
BANDED_KS = {"EB", "HEB", "HEpB", "AnnE"}

# Tiers, strongest first.
TIERS = ["GUARANTEED", "HIGH", "MODERATE", "BEST-GUESS", "NONE"]

# Observed cache span (years with ground truth). Used only for the report banner;
# the per-coordinate interpolation test uses each coordinate's own supporters.
CACHE_YEARS = range(2001, 2027)


def _easter_md(year):
    """Easter as a (month, day) tuple -- a year-free ordering (Easter is always in
    March/April), so the interpolation bracket never mixes civil years."""
    e = calculate_gregorian_easter(year)
    return (e.month, e.day)


def _support_years(occ, ks, key):
    """Sorted observed years that produced this exact coordinate."""
    return sorted({y for y, _, _ in occ.get(ks, {}).get(key, [])})


def classify_day(d, occ):
    """Grade one date. Returns a record dict (see module docstring for fields)."""
    res = compute_armenian_lectionary(d)
    src = res["Source"]
    rec = {
        "date": d.isoformat(),
        "season": res["Season"],
        "feast": res["Liturgical Day"],
        "source": src,
        "matched_ks": None,
        "matched_key": None,
        "n_support_years": 0,
        "easter_interpolated": None,
        "extrapolation": False,
        "tier": None,
        "why": "",
    }

    if src == "algorithmic-estimate":
        rec.update(tier="NONE", why="no cross-year-consistent coordinate; readings withheld")
        return rec
    if src in ("generative-saint", "generative-continua", "generative-composite"):
        rec.update(tier="BEST-GUESS",
                   why="labeled best-guess (%s); unvalidated by construction" % src)
        return rec
    if src == "validated-composite":
        rec.update(tier="GUARANTEED", matched_ks="composite",
                   why="Easter-independent embedded fixed-feast composite (civil-date proper)")
        return rec

    # validated-table: the transfer depends on which coordinate(s) justify the
    # shipped reading. We assess the *strongest* available justification, not just
    # the precedence-winning coordinate (a banded EB hit can shadow a plain-E
    # coordinate that is in fact unanimous across all observed years).
    ks, key, entry = _lookup(d)
    rec["matched_ks"], rec["matched_key"] = ks, key
    R = tuple(entry["readings"])
    y_easter = calculate_gregorian_easter(d.year)
    e_off = (d - y_easter).days

    # (1) Easter-independent winning coordinate -> civil/solar, cannot be perturbed
    #     by an unseen Easter.
    if ks in EASTER_INDEP_KS:
        rec.update(tier="GUARANTEED", easter_interpolated=True,
                   why="Easter-independent coordinate (%s); civil/solar-anchored, "
                       "cannot be perturbed by an unseen Easter" % ks)
        return rec

    # (2) Plain Easter-offset invariance: if the bare E=offset reading is unanimous
    #     across EVERY observed year hitting it AND equals the shipped reading, the
    #     reading does not vary with Easter date at all. It transfers with certainty
    #     iff the target's Easter falls within that observed span (interpolation).
    items_E = occ.get("E", {}).get(e_off, [])
    sigs_E = {s for _, _, s in items_E}
    years_E = sorted({y for y, _, _ in items_E})
    # Easter falls only in March/April, so (month, day) is a valid year-free
    # ordering for the bracket test (comparing full dates would mix civil years).
    emds = sorted(_easter_md(y) for y in years_E)
    y_md = _easter_md(d.year)
    if sigs_E == {R} and emds and emds[0] <= y_md <= emds[-1]:
        rec["n_support_years"] = len(years_E)
        rec.update(tier="GUARANTEED", easter_interpolated=True,
                   why="plain Easter-offset reading unanimous across %d years "
                       "(observed Easter %02d-%02d..%02d-%02d) bracketing the "
                       "target -> interpolation"
                       % (len(years_E), emds[0][0], emds[0][1],
                          emds[-1][0], emds[-1][1]))
        return rec

    # (3) Rely on the matched banded/grid coordinate. A matched key means the
    #     target shares that band / grid slot with the observed supporters (in-band
    #     interpolation); the raw Easter date is a within-band detail the band
    #     deliberately abstracts away. Strong only with >=2 agreeing supporters.
    n = len(_support_years(occ, ks, key))
    rec["n_support_years"] = n

    if ks == "E":
        # Plain-E winner that failed (2): the target's Easter extrapolates beyond
        # the observed span over which this reading was invariant.
        rec["extrapolation"] = True
        rec.update(tier="HIGH",
                   why="plain Easter-offset reading, but target Easter %s lies "
                       "outside the observed span -> extrapolation"
                       % y_easter.isoformat())
        return rec

    kind = "band" if ks in BANDED_KS else "grid"
    rec["easter_interpolated"] = True   # the band/grid slot itself matched
    if n >= 2:
        rec.update(tier="HIGH",
                   why="%s coordinate (%s) shared with %d agreeing observed years; "
                       "target is in-band -> interpolation within the band" % (kind, ks, n))
    else:
        rec.update(tier="MODERATE",
                   why="%s coordinate (%s) with a single observed supporter; "
                       "not cross-validated for the target year" % (kind, ks))
    return rec


def audit_year(year, occ):
    d = datetime.date(year, 1, 1)
    end = datetime.date(year, 12, 31)
    recs = []
    while d <= end:
        recs.append(classify_day(d, occ))
        d += datetime.timedelta(days=1)
    return recs


def _tier_counts(recs):
    c = collections.Counter(r["tier"] for r in recs)
    return {t: c.get(t, 0) for t in TIERS}


def _summary(year, recs, out):
    e = calculate_gregorian_easter(year)
    tc = _tier_counts(recs)
    n_extrap = sum(1 for r in recs if r["extrapolation"])
    print("\n=== %d: Easter %s  pn_len=%d  band=%d  (%d days) ==="
          % (year, e.isoformat(), _pn_len(year), _easter_band(year), len(recs)),
          file=out)
    for t in TIERS:
        print("  %-11s %4d" % (t, tc[t]), file=out)
    print("  %-11s %4d  (days whose Easter-sensitive coordinate extrapolates "
          "beyond observed support)" % ("extrapolate", n_extrap), file=out)
    # Enumerate the not-certain days (everything below HIGH).
    uncertain = [r for r in recs if r["tier"] in ("MODERATE", "BEST-GUESS", "NONE")]
    if uncertain:
        print("  -- not-certain days (%d):" % len(uncertain), file=out)
        for r in uncertain:
            print("     %s  %-9s %s  [%s]"
                  % (r["date"], r["tier"], r["feast"][:48], r["source"]), file=out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    summary_only = "--summary" in sys.argv
    if not args:
        years = [datetime.date.today().year + 1]
    elif len(args) == 1:
        years = [int(args[0])]
    else:
        years = list(range(int(args[0]), int(args[1]) + 1))

    occ = _occurrences(load_all())
    out = sys.stderr

    all_recs = {}
    for y in years:
        recs = audit_year(y, occ)
        all_recs[y] = recs
        _summary(y, recs, out)

    # Horizon table across years (always to stderr when >1 year).
    if len(years) > 1:
        print("\n=== Horizon table ===", file=out)
        hdr = "year easter     band  " + " ".join("%-10s" % t for t in TIERS) + " extrap"
        print(hdr, file=out)
        for y in years:
            tc = _tier_counts(all_recs[y])
            e = calculate_gregorian_easter(y)
            n_ex = sum(1 for r in all_recs[y] if r["extrapolation"])
            print("%d %s %4d  %s %d"
                  % (y, e.isoformat(), _easter_band(y),
                     " ".join("%-10d" % tc[t] for t in TIERS), n_ex), file=out)

    if not summary_only:
        # Per-day JSON for the single-year (or first-year) case, to stdout.
        json.dump(all_recs[years[0]], sys.stdout, indent=1)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
