"""DEV-ONLY: classify each `algorithmic-estimate` day by RULE-RECOVERABILITY.

`reports/unpredictable_days.md` classifies the 407 estimate days by *failure
mechanism* (Class A single-outlier / B continua / C year-band / D embedded). This
tool re-cuts the SAME 407 days along a different axis the project actually cares
about: *can a rule ever predict this day, and what kind of rule?* Every estimate
day is assigned exactly one bucket:

  1 COMPLEX-RULE-RECOVERABLE  - a computable feature cleanly partitions the
        conflicting reading-sets and this day sits in a >=2-year variant (incl.
        the trivial "consensus + outliers" case: ship the consensus, route the
        outlier). Predictable with a finer/outlier-aware STATIC rule.
  2 RULE-SHAPED, SINGLE-SUPPORT - this day IS the lone outlier, but its year is an
        extreme-Easter / known-collision year and the deviation is a deterministic
        consequence of a computable condition. Predictable in principle; shippable
        only by trusting 1 sample or pinning the condition.
  3 MODEL-GAP - not separable by a static feature because the right coordinate is a
        running index (Fast-of-Assumption / Fast-of-Nativity continua) or a
        saint merge/replay. Predictable with a different MODEL, not a date hardcode.
  4 TRULY DATE-BESPOKE / UNPREDICTABLE - lone outlier in an ORDINARY year, in a
        statically-anchored zone, with no computable condition and no known
        mechanism. Candidate year-specific editorial judgment call OR source error;
        must be specified per date.  <-- the bucket the user most wants isolated.
  5 EMBEDDED IRREGULAR FEAST - the 5 floating fixed-date feasts; out of scope under
        exact-match.

The unit of analysis is the DAY (its dominant in-window coordinate), so bucket
counts sum to 407. Emits JSON to stdout and a human sanity summary to stderr.

Run:  python dev/predictability_audit.py            # JSON to stdout, summary to stderr
      python dev/predictability_audit.py --summary  # only the stderr summary
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dev.analyze import load_all  # noqa: E402
from dev.build_table import rsig, _consistent, CIVIL_MIN_YEARS  # noqa: E402
from dev.estimate_report import _is_leap  # noqa: E402
from armenian_lectionary.engine import (  # noqa: E402
    compute_armenian_lectionary, coords_for, WINDOWS, PRECEDENCE,
    EMBEDDED_FIXED, calculate_gregorian_easter,
)

# Zones whose coordinate is directly Easter/Advent-anchored, where a STATIC
# secondary feature is expected to separate variants. Everything else is a
# continua/saint-merge zone whose true coordinate is a running index.
STATIC_ZONES = {"E", "HE"}
_MERGE_NUM = {"AS", "EX", "HEp", "THp", "TH"}
_MERGE_PREFIX = ("Pn", "Adv", "Tr", "As", "Ex", "Ao")


def _zone_needs_model(ks):
    return ks in _MERGE_NUM or ks.startswith(_MERGE_PREFIX)


def _easter_band(e):
    """Coarse Easter band (edges reused from reports/unpredictable_days.md)."""
    md = (e.month, e.day)
    if md <= (3, 24):
        return "Earliest(<=Mar24)"
    if md <= (3, 29):
        return "VeryEarly(Mar25-29)"
    if md <= (4, 12):
        return "EarlyMid(Mar30-Apr12)"
    if md <= (4, 20):
        return "Central(Apr13-20)"
    if md <= (4, 22):
        return "Late(Apr21-22)"
    return "Latest(>=Apr23)"


def _extreme_easter(e):
    """The genuinely extreme Easters in 2001-2026: Mar23, Mar27x2, Apr24."""
    if e.month == 3 and e.day <= 27:
        return "earliest-Easter(%s)" % e.strftime("%b%d")
    if (e.month == 4 and e.day >= 23) or e.month > 4:
        return "latest-Easter(%s)" % e.strftime("%b%d")
    return None


# --------------------------------------------------------------------------- #
# Substrate: per-coordinate occurrences and the immovable-feast date set.
# --------------------------------------------------------------------------- #

def _fixed_dates(days):
    """Civil (month,day) that the builder treats as immovable feasts."""
    civ = collections.defaultdict(list)
    for iso, day in days.items():
        if not (day["readings"] or day["feast"]):
            continue
        d = datetime.date.fromisoformat(iso)
        civ[(d.month, d.day)].append((iso[:4], day))
    return {md for md, items in civ.items() if _consistent(items, CIVIL_MIN_YEARS)}


def _occurrences(days):
    """occ[ks][key] = list of (year:int, date, sig) for every in-window day,
    mirroring build_table's bucket filtering so coordinates match the shipped
    table exactly."""
    occ = collections.defaultdict(lambda: collections.defaultdict(list))
    for iso, day in days.items():
        if not (day["readings"] or day["feast"]):
            continue
        d = datetime.date.fromisoformat(iso)
        for ks, key in coords_for(d).items():
            if ks in ("C", "CF"):
                continue
            win = WINDOWS.get(ks)
            if win is not None and not (win[0] <= key <= win[1]):
                continue
            occ[ks][key].append((d.year, d, rsig(day)))
    return occ


def _dominant_coord(d, occ):
    """The day's dominant in-window coordinate (ks, key), replaying the
    estimate_report._classify precedence walk: first in-window keyspace, upgraded
    to the first real cross-year conflict (>=2 sigs and >=2 years)."""
    cs = coords_for(d)
    best = None
    for ks in PRECEDENCE:
        if ks in ("C", "CF") or ks not in cs:
            continue
        key = cs[ks]
        win = WINDOWS.get(ks)
        if win is not None and not (win[0] <= key <= win[1]):
            continue
        items = occ.get(ks, {}).get(key, [])
        sigs = {s for _, _, s in items}
        years = {y for y, _, _ in items}
        if best is None:
            best = (ks, key)
        if len(sigs) >= 2 and len(years) >= 2:
            return (ks, key)
    return best


# --------------------------------------------------------------------------- #
# Feature-separability test.
# --------------------------------------------------------------------------- #

def _feature_vector(dt):
    """Computable features of an occurrence date that can VARY across the years
    sharing one coordinate (so they can separate that coordinate's variants).
    Keyed by feature name -> value."""
    y = dt.year
    e = calculate_gregorian_easter(y)
    # Length of the post-Nativity window (Jan14 .. Easter-70): Easter-correlated
    # AND leap-sensitive -> the candidate separator for the E=-70/-72 boundary.
    pn_len = (e - datetime.timedelta(days=70) - datetime.date(y, 1, 14)).days
    # Summer span Transfiguration(Easter+98) -> Assumption(closest Sun to Aug15):
    # the continua driver for the Fast-of-Assumption block.
    from armenian_lectionary.engine import anchors
    a = anchors(y)
    as_span = (a["AS"] - a["TR"]).days
    return {
        "band": _easter_band(e),
        "leap": _is_leap(y),
        "pn_len": pn_len,
        "as_span": as_span,
        "civ_md": (dt.month, dt.day),
    }


_FEATURES = ("band", "leap", "pn_len", "as_span", "civ_md")


def _partition_pure(occ_list, featfn):
    """occ_list: [(year, date, sig)]. Partition by featfn(date); return True iff
    no feature-value group mixes two distinct sigs."""
    groups = collections.defaultdict(set)
    for _, dt, sig in occ_list:
        groups[featfn(dt)].add(sig)
    return all(len(s) == 1 for s in groups.values())


def _best_separator(occ_list):
    """Find the minimal feature (or feature pair) that cleanly partitions the
    occurrences AND leaves every variant-sig backed by >=2 years. Returns the
    feature label or None."""
    sig_support = collections.Counter(sig for _, _, sig in occ_list)
    if min(sig_support.values()) < 2:
        return None  # a singleton sig remains -> not fully static-recoverable
    fv = {dt: _feature_vector(dt) for _, dt, _ in occ_list}
    for f in _FEATURES:
        if _partition_pure(occ_list, lambda dt, f=f: fv[dt][f]):
            return f
    for i, f1 in enumerate(_FEATURES):
        for f2 in _FEATURES[i + 1:]:
            if _partition_pure(occ_list, lambda dt, a=f1, b=f2: (fv[dt][a], fv[dt][b])):
                return "%s+%s" % (f1, f2)
    return None


# --------------------------------------------------------------------------- #
# Source-error / artifact heuristic for bucket-4 candidates.
# --------------------------------------------------------------------------- #

def _book_prefix(ref):
    """Drop the trailing chapter.verse range, keeping the book(+chapter) stem."""
    return ref.rsplit(" ", 1)[0] if " " in ref else ref


def _artifact_flag(d, day, days, consensus_sig):
    iso = d.isoformat()
    this = rsig(day)
    for delta in (-1, 1):
        nb = days.get((d + datetime.timedelta(days=delta)).isoformat())
        if nb and rsig(nb) == this:
            return ("possible source artifact",
                    "readings identical to the %s calendar day (off-by-one scrape?)"
                    % ("previous" if delta < 0 else "next"))
    if consensus_sig and len(this) == len(consensus_sig):
        diffs = [i for i in range(len(this)) if this[i] != consensus_sig[i]]
        if diffs and all(_book_prefix(this[i]) == _book_prefix(consensus_sig[i])
                         for i in diffs) and len(diffs) <= 1:
            return ("possible source artifact",
                    "differs from consensus only by a verse range (%s vs %s)"
                    % (this[diffs[0]], consensus_sig[diffs[0]]))
    return ("genuine editorial variant", "no scrape-artifact signal")


# --------------------------------------------------------------------------- #
# Per-day classifier.
# --------------------------------------------------------------------------- #

def _consensus_sig(occ_list):
    c = collections.Counter(sig for _, _, sig in occ_list)
    return c.most_common(1)[0][0]


# Major fixed dominical feasts (UPPER-CASED in the corpus) that DISPLACE an
# adjacent movable saint, transferring it onto the next free day where it merges.
_DISPLACING_FEAST = ("PRESENTATION OF OUR LORD", "TRANSFIGURATION", "ASSUMPTION",
                     "EXALTATION", "NATIVITY AND THEOPHANY", "ANNUNCIATION")


def _displaced_by_fixed(d, day, days):
    """If this outlier day FOLDS IN an extra saint group ('... and Saints ...')
    and an adjacent day carries a major fixed feast occupying that saint's normal
    movable slot, the deviation is a deterministic feast-displacement transfer."""
    fe = day["feast"]
    if " and Saint" not in fe and ", and Saint" not in fe:
        return None  # not a merged/folded commemoration
    for delta in (-2, -1, 1, 2):
        nb = days.get((d + datetime.timedelta(days=delta)).isoformat())
        if nb and any(m in nb["feast"] for m in _DISPLACING_FEAST):
            nd = d + datetime.timedelta(days=delta)
            return "%02d-%02d %s" % (nd.month, nd.day, nb["feast"].strip()[:40])
    return None


def classify_day(d, day, days, occ, fixed_dates):
    md = (d.month, d.day)
    rec = {"iso": d.isoformat(), "year": d.year, "month": d.month,
           "weekday": d.strftime("%a"),
           "easter": calculate_gregorian_easter(d.year).strftime("%m-%d"),
           "leap": _is_leap(d.year), "feast": (day["feast"] or "").strip()[:60]}

    if md in EMBEDDED_FIXED:
        rec.update(bucket=5, bucket_name="embedded irregular feast",
                   coord="CF=%02d-%02d" % md, mechanism="floating fixed-date feast",
                   feature=None, artifact=None)
        return rec

    dom = _dominant_coord(d, occ)
    if dom is None:
        rec.update(bucket=3, bucket_name="model-gap", coord="-",
                   mechanism="no anchored coordinate (unmodeled slot)",
                   feature=None, artifact=None)
        return rec

    ks, key = dom
    occ_list = occ[ks][key]
    rec["coord"] = "%s=%s" % (ks, key)
    sig_support = collections.Counter(sig for _, _, sig in occ_list)
    this_sig = rsig(day)
    this_support = sig_support.get(this_sig, 1)
    n_sigs = len(sig_support)

    # --- This day sits in a >=2-year variant: recoverable or model-gap. --------
    if this_support >= 2:
        majority = [s for s, n in sig_support.items() if n >= 2]
        if len(majority) == 1:
            rec.update(bucket=1, bucket_name="complex-rule-recoverable",
                       mechanism="outlier-isolation (consensus of %d yrs, %d singleton outlier(s))"
                       % (this_support, sum(1 for n in sig_support.values() if n == 1)),
                       feature="outlier-aware key", artifact=None)
            return rec
        # Multiple multi-year variants. Zone-gating: a STATIC zone (E/HE) may be
        # split by a static secondary feature (e.g. E=-70 by the leap-sensitive
        # post-Nativity span); a continua/merge zone must NOT be "separated" by an
        # Easter-proxy feature (band/as_span/pn_len) -- that is the confound, the
        # real coordinate is a running index, so it is a model-gap.
        if _zone_needs_model(ks):
            rec.update(bucket=3, bucket_name="model-gap",
                       mechanism="%d competing variants in continua/merge zone %s "
                       "(key on running fast-day index)" % (len(majority), ks),
                       feature=None, artifact=None)
            return rec
        core = [(y, dt, s) for (y, dt, s) in occ_list if sig_support[s] >= 2]
        sep = _best_separator(core)
        if sep:
            rec.update(bucket=1, bucket_name="complex-rule-recoverable",
                       mechanism="%d multi-year variants, separable" % len(majority),
                       feature=sep, artifact=None)
        else:
            rec.update(bucket=3, bucket_name="model-gap",
                       mechanism="%d multi-year variants, no static separator in zone %s"
                       % (len(majority), ks), feature=None, artifact=None)
        return rec

    # --- This day IS the lone outlier (single-support variant). ----------------
    e = calculate_gregorian_easter(d.year)
    extreme = _extreme_easter(e)
    feats = _feature_vector(d)
    if extreme:
        rec.update(bucket=2, bucket_name="rule-shaped, single-support",
                   mechanism="extreme year: %s" % extreme, feature="Easter-band/extremity",
                   artifact=None)
    elif md == (4, 24):
        rec.update(bucket=2, bucket_name="rule-shaped, single-support",
                   mechanism="Apr-24 Genocide-Remembrance collision", feature="civil-collision",
                   artifact=None)
    elif feats["civ_md"] in fixed_dates:
        rec.update(bucket=2, bucket_name="rule-shaped, single-support",
                   mechanism="lands on immovable feast %02d-%02d" % md, feature="civil-collision",
                   artifact=None)
    elif _zone_needs_model(ks):
        rec.update(bucket=3, bucket_name="model-gap",
                   mechanism="%s zone continua/saint-merge (running-index recovers)" % ks,
                   feature=None, artifact=None)
    elif _displaced_by_fixed(d, day, days):
        rec.update(bucket=3, bucket_name="model-gap",
                   mechanism="fixed-feast displacement: adjacent %s bumped a saint onto this day"
                   % _displaced_by_fixed(d, day, days),
                   feature="feast-displacement/transfer", artifact=None)
    else:
        flag, detail = _artifact_flag(d, day, days, _consensus_sig(occ_list))
        rec.update(bucket=4, bucket_name="truly date-bespoke",
                   mechanism="lone outlier in ordinary year, static zone %s, no computable condition" % ks,
                   feature=None, artifact={"flag": flag, "detail": detail,
                                           "consensus": list(_consensus_sig(occ_list)),
                                           "this": list(this_sig)})
    return rec


# --------------------------------------------------------------------------- #

def audit():
    days = load_all()
    occ = _occurrences(days)
    fixed = _fixed_dates(days)
    recs = []
    for iso, day in sorted(days.items()):
        if not (day["readings"] or day["feast"]):
            continue
        d = datetime.date.fromisoformat(iso)
        if compute_armenian_lectionary(d)["Source"] != "algorithmic-estimate":
            continue
        recs.append(classify_day(d, day, days, occ, fixed))
    return recs


def _summary(recs):
    out = sys.stderr
    by_bucket = collections.Counter(r["bucket"] for r in recs)
    names = {1: "complex-rule-recoverable", 2: "rule-shaped single-support",
             3: "model-gap (continua/merge)", 4: "TRULY date-bespoke",
             5: "embedded irregular feast"}
    print("\n=== Predictability audit over %d estimate days ===" % len(recs), file=out)
    for b in (1, 2, 3, 4, 5):
        print("  bucket %d  %-32s %4d" % (b, names[b], by_bucket.get(b, 0)), file=out)
    print("  %-43s %4d" % ("TOTAL", sum(by_bucket.values())), file=out)
    assert sum(by_bucket.values()) == len(recs)
    assert len({r["iso"] for r in recs}) == len(recs), "duplicate ISO dates"
    print("\n  predictable-in-principle (buckets 1-3): %d" %
          sum(by_bucket.get(b, 0) for b in (1, 2, 3)), file=out)
    print("  must hardcode per-date    (bucket 4):    %d" % by_bucket.get(4, 0), file=out)
    print("  out of scope              (bucket 5):    %d" % by_bucket.get(5, 0), file=out)

    # Bucket-4 detail (the headline list).
    print("\n  --- bucket 4: truly date-bespoke days ---", file=out)
    for r in sorted(recs, key=lambda r: r["iso"]):
        if r["bucket"] == 4:
            print("    %s  %-26s %-10s [%s]" %
                  (r["iso"], r["coord"], r["feast"][:26], r["artifact"]["flag"]), file=out)

    # Bucket-2 detail keyed by condition.
    print("\n  --- bucket 2: rule-shaped single-support (sample) ---", file=out)
    seen = collections.Counter()
    for r in sorted(recs, key=lambda r: r["iso"]):
        if r["bucket"] == 2 and seen[r["mechanism"]] < 3:
            seen[r["mechanism"]] += 1
            print("    %s  %-14s %s" % (r["iso"], r["coord"], r["mechanism"]), file=out)

    # Mechanism cross-cut for singletons.
    sing = [r for r in recs if r["bucket"] in (2, 4)]
    print("\n  singleton-outlier days: bucket2(rule-shaped)=%d  bucket4(bespoke)=%d" %
          (sum(r["bucket"] == 2 for r in sing), sum(r["bucket"] == 4 for r in sing)), file=out)

    # Canonical spot-checks.
    print("\n  --- spot-checks ---", file=out)
    idx = {(r["iso"]): r for r in recs}
    checks = []
    def find(ks_key, year):
        for r in recs:
            if r["coord"] == ks_key and r["year"] == year:
                return r
        return None
    for label, r, want in [
        ("E=0/2011", find("E=0", 2011), 2),
        ("E=-64/2008", find("E=-64", 2008), 2),
    ]:
        got = r["bucket"] if r else None
        ok = got == want
        checks.append(ok)
        print("    %-12s bucket=%s want=%s %s %s" %
              (label, got, want, "OK" if ok else "??", r["mechanism"] if r else "(not estimate)"), file=out)
    e70 = [r for r in recs if r["coord"] == "E=-70"]
    e70_bad = [r for r in e70 if r["bucket"] == 4]
    print("    E=-70 days: %d (buckets %s); none truly-bespoke: %s" %
          (len(e70), sorted({r["bucket"] for r in e70}), "OK" if not e70_bad else "??"), file=out)
    as_fast = [r for r in recs if r["coord"].startswith("AS=-") and r["month"] == 8]
    print("    AS=-* August days: %d, all model-gap: %s" %
          (len(as_fast), "OK" if all(r["bucket"] == 3 for r in as_fast) else "??"), file=out)


def main():
    recs = audit()
    if "--summary" not in sys.argv:
        json.dump({"records": recs}, sys.stdout, ensure_ascii=False)
    _summary(recs)


if __name__ == "__main__":
    main()
