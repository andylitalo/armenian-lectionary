"""DEV-ONLY: what the never-winning tiers actually serve, and whether it is attested.

Two of the thirteen adapters on ``engine._TIERS`` win on **no date** in
``MIN_YEAR``-``MAX_YEAR``: ``_tier_generative_saint`` (it applies on 1,904 days and is
shadowed on every one) and ``_tier_fallback`` (every day in range is claimed earlier).
Neither is dead code -- ``_compute_lectionary`` has no range guard and the range is
env-overridable by design -- but a green suite says nothing about either body, because
every reading test in the suite compares the **served** answer to ground truth and in
range these tiers never are it.

So this script asks the question those tests structurally cannot: over a long probe
window, which days does each tier actually serve, and is what it serves attested by the
validated data? Two independent routes, both computed rather than assumed:

  twin        another date IN RANGE carries the same zone-saint coordinate (identity x
              civil date) and is served from the validated table. The strongest evidence
              available: the same liturgical coordinate, resolved by the cross-year table
              rather than by the laydown. Compared on the SERVED output, so the
              ``_drop_owned_companions`` overlay is included -- the raw tier result can
              carry a packed companion the overlay correctly removes.

  attested    no twin exists, but the saint identity the tier places has a dominant
              reading set across its own validated-table days in range, and the tier
              serves that set. Weaker: it says the readings belong to that saint, not
              that the saint belongs to that day.

A day with neither is the finding worth having -- the tier serving a reading the validated
data attests nowhere.

Why ``_tier_generative_saint`` still exists, since ``_tier_cycle_saint`` took over its
original job of filling in-range blanks: its live territory is the complement of two
deliberate conservatism rules. ``dev/build_table.py`` harvests an anchored keyspace key
only via ``_consistent(items, 2)`` -- two distinct years must agree -- so a coordinate
occurring exactly once in range is dropped on purpose. And ``_CYCLE_SAINTS`` covers all 35
possible Gregorian Easter dates but carries only the days each year-type's Second Volume
page prints, and the pages truncate. See ``docs/generative-saint-tier.md``.

Needs no ``dev/reference_data/`` cache: it compares the engine to itself. That is what
lets it reach 2027 and every year past it.

Usage:
    python dev/audit_shadowed_tiers.py            # summary
    python dev/audit_shadowed_tiers.py --list     # every shadowed disagreement too
"""

import collections
import contextlib
import datetime
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                       # noqa: E402
from armenian_lectionary.engine import (                                     # noqa: E402
    MAX_YEAR, MIN_YEAR, coords_for,
)

# How far past MAX_YEAR to look for a date each tier actually wins on. 2130 is not
# arbitrary: ``_tier_generative_saint`` wins on one day by 2060 and on five by 2130, and
# five is what makes both of its live coordinates visible. Reaching past the supported
# range is legitimate -- the range is env-overridable (the deploy runbook widens it with
# one `gcloud run services update`) and ``_compute_lectionary`` has no range guard.
PROBE_TO = 2130

VALIDATED = "validated-table"


@dataclass(frozen=True)
class WinDay:
    """One date a tier is the ladder's winner on, with what it served and the verdict."""
    date: datetime.date
    tier: str
    keyspace: Optional[str]        # e.g. "TrSaintMD"
    coordinate: Optional[str]      # e.g. "cyricus_and_his:07-30"
    identity: Optional[str]        # e.g. "cyricus_and_his"
    name: str
    readings: tuple
    verdict: str                   # "twin" | "attested" | "unverified" | "no-claim"
    detail: str


@dataclass
class ShadowStats:
    """A tier that applies in range but never wins: who covers it, and does it agree?"""
    applies: int = 0
    shadowers: collections.Counter = field(default_factory=collections.Counter)
    readings_agree: int = 0
    label_agree: int = 0
    disagreements: list = field(default_factory=list)   # (date, shadower, served, shadowed)


@dataclass
class Report:
    min_year: int
    max_year: int
    probe_to: int
    applies: dict
    wins: dict
    win_days: dict          # tier name -> [WinDay], over min_year..probe_to
    shadowed: dict          # tier name -> ShadowStats, for tiers with wins == 0


@contextlib.contextmanager
def widened_range(probe_to):
    """Let ``compute_armenian_lectionary`` answer past ``MAX_YEAR``.

    The guard is a plain comparison against the module globals, which is exactly what a
    consumer relaxes with ``LECTIONARY_MAX_YEAR``; this is the in-process spelling of the
    same thing. Restored on exit so nothing downstream sees a widened engine.
    """
    saved = engine.MAX_YEAR
    engine.MAX_YEAR = max(saved, probe_to)
    try:
        yield
    finally:
        engine.MAX_YEAR = saved


def _days(first_year, last_year):
    d = datetime.date(first_year, 1, 1)
    end = datetime.date(last_year, 12, 31)
    while d <= end:
        yield d
        d += datetime.timedelta(days=1)


def _winner(d):
    """The tier the ladder serves ``d`` from, and its ``_TierResult``."""
    for tier in engine._TIERS:
        result = tier(d)
        if result is not None:
            return tier.__name__, result
    raise RuntimeError(f"no tier resolved {d.isoformat()}")     # _tier_fallback prevents this


def saint_coordinate(d):
    """``d``'s zone-saint coordinate as ``(keyspace, value, identity)``, or three Nones.

    The ``*SaintMD`` keyspaces are identity x civil date -- the finest zone-saint
    coordinate the engine keys on, and the one a cross-year twin has to share to be
    evidence about this day rather than about this saint.
    """
    for keyspace, value in sorted(coords_for(d).items()):
        if keyspace.endswith("SaintMD"):
            return keyspace, value, value.split(":", 1)[0]
    return None, None, None


def validated_index(min_year, max_year):
    """Everything in range the validated table serves, indexed the two ways we verify by.

    ``twins``  coordinate -> [(date, name, readings)] for validated-table days
    ``attest`` saint identity -> Counter of reading sets, over validated-table days whose
               zone-saint coordinate names that identity
    """
    twins = collections.defaultdict(list)
    attest = collections.defaultdict(collections.Counter)
    for d in _days(min_year, max_year):
        served = engine.compute_armenian_lectionary(d)
        if served["Source"] != VALIDATED:
            continue
        readings = tuple(served["ReadingsList"])
        keyspace, coordinate, _identity = saint_coordinate(d)
        if coordinate is not None:
            twins[coordinate].append((d, served["Liturgical Day"], readings))
        for key, value in coords_for(d).items():
            if key.endswith("Saint"):
                attest[value][readings] += 1
    return twins, attest


def _verify(d, tier_name, twins, attest, probe_to):
    """Classify what ``tier_name`` serves on ``d``. See the module docstring for the routes."""
    keyspace, coordinate, identity = saint_coordinate(d)
    with widened_range(probe_to):
        served = engine.compute_armenian_lectionary(d)
    name, readings = served["Liturgical Day"], tuple(served["ReadingsList"])

    def win(verdict, detail):
        return WinDay(d, tier_name, keyspace, coordinate, identity, name, readings,
                      verdict, detail)

    if not readings:
        # _tier_fallback: an explicit "not yet modeled", with no readings to be wrong about.
        return win("no-claim", "serves no readings and says so")

    candidates = twins.get(coordinate, ())
    for twin_date, twin_name, twin_readings in candidates:
        if (twin_name, twin_readings) == (name, readings):
            return win("twin", f"byte-identical to {twin_date.isoformat()} "
                               f"({VALIDATED}, same {keyspace})")
    if candidates:
        # Every twin at this coordinate disagrees. Report the first; a coordinate whose
        # twins disagree with EACH OTHER would already have failed the table's own
        # cross-year consistency rule, so there is nothing subtler to say here.
        twin_date, twin_name, twin_readings = candidates[0]
        return win("unverified",
                   f"twin {twin_date.isoformat()} at the same {keyspace} serves "
                   f"{twin_name!r} / {len(twin_readings)} readings, not this")

    counts = attest.get(identity)
    if counts:
        (modal, modal_n), = counts.most_common(1)
        if modal == readings:
            return win("attested", f"{identity}'s dominant reading set across "
                                   f"{modal_n} {VALIDATED} days in range")
        return win("unverified",
                   f"{identity} is attested {modal_n}x in range with a different set")
    return win("unverified", f"no twin at {keyspace or 'any saint coordinate'} and no "
                             f"validated attestation for {identity!r}")


def collect(min_year=MIN_YEAR, max_year=MAX_YEAR, probe_to=PROBE_TO):
    """Applies/wins per tier in range, plus every win day out to ``probe_to``, verified."""
    names = [tier.__name__ for tier in engine._TIERS]
    applies = dict.fromkeys(names, 0)
    wins = dict.fromkeys(names, 0)
    shadowed = {}

    # Pass 1, in range: applies and wins for every tier, and -- for a tier that applies
    # here -- how its answer compares with the one actually served.
    for d in _days(min_year, max_year):
        winner = None
        for tier in engine._TIERS:
            result = tier(d)
            if result is None:
                continue
            applies[tier.__name__] += 1
            if winner is None:
                winner = (tier.__name__, result)
                wins[tier.__name__] += 1
                continue
            stats = shadowed.setdefault(tier.__name__, ShadowStats())
            stats.applies += 1
            served_name, served = winner
            same_readings = list(served.readings) == list(result.readings)
            stats.shadowers[(served_name, same_readings)] += 1
            stats.readings_agree += same_readings
            stats.label_agree += served.label == result.label
            if not same_readings:
                stats.disagreements.append((d, served_name, served.label, result.label))

    # A tier that wins somewhere in range is not shadowed in the sense this asks about.
    shadowed = {name: stats for name, stats in shadowed.items() if not wins[name]}

    # Pass 2, out to probe_to: the days each never-winning tier is the one that answers.
    twins, attest = validated_index(min_year, max_year)
    win_days = {name: [] for name in names}
    for d in _days(min_year, probe_to):
        tier_name, _result = _winner(d)
        if wins[tier_name]:
            continue        # it already wins in range; the suite reaches it there
        # Keyed on wins rather than on `shadowed` deliberately: a tier that applies on no
        # date in range is in neither dict, and its win days out of range are exactly what
        # would tell you whether it is dead or merely out of season.
        win_days[tier_name].append(_verify(d, tier_name, twins, attest, probe_to))

    return Report(min_year, max_year, probe_to, applies, wins, win_days, shadowed)


def main():
    show_list = "--list" in sys.argv[1:]
    report = collect()
    span = f"{report.min_year}-{report.max_year}"
    probe = f"{report.min_year}-{report.probe_to}"

    print(f"Tier ladder over {span} ({sum(report.wins.values())} days)\n")
    print(f"  {'tier':<42} {'applies':>8} {'wins':>8}")
    for tier in engine._TIERS:
        name = tier.__name__
        print(f"  {name:<42} {report.applies[name]:>8} {report.wins[name]:>8}")

    for name, stats in report.shadowed.items():
        print(f"\n{name}: applies on {stats.applies} days in {span}, wins on none.")
        days = report.win_days[name]

        if name == engine._TIERS[-1].__name__:
            # The unconditional terminator. It is shadowed on every day it does not win
            # BY CONSTRUCTION, so a per-shadower breakdown says only that the ladder
            # works; and its answer -- no readings, flagged not-yet-modeled -- competes
            # with nothing, so there is no agreement rate to report.
            print("  unconditional by construction: shadowed wherever any tier above it "
                  "answers.")
            print("  It claims no readings, so there is nothing for a shadower to "
                  "disagree with.")
            print(f"\n  wins on {len(days)} day(s) in {probe}, all serving no readings:")
            by_year = collections.defaultdict(list)
            for day in days:
                by_year[day.date.year].append(f"{day.date:%m-%d}")
            for year, dates in sorted(by_year.items()):
                print(f"    {year}  {', '.join(dates)}")
            print("    (unmodeled gaps: the Easter-Apr-25 winter hinge, and the "
                  "after-Transfiguration")
            print("     weekly fasts in the earliest-Easter years -- out of scope here)")
            continue

        print("  shadowed by:")
        for (shadower, agree), n in sorted(stats.shadowers.items()):
            verb = "same readings" if agree else "DIFFERENT readings"
            print(f"    {shadower:<40} {n:>6}  ({verb})")
        print(f"  agrees on readings {stats.readings_agree}/{stats.applies}, "
              f"on label {stats.label_agree}/{stats.applies}")
        print("  -- all days it does NOT serve. What it does serve is below; these rates "
              "are not")
        print("     evidence about those days, and the win days are not sampled from "
              "this set.")

        print(f"\n  wins on {len(days)} day(s) in {probe}:")
        for day in days:
            print(f"    {day.date.isoformat()} {day.date:%a}  [{day.verdict}] "
                  f"{day.coordinate or '-'}")
            print(f"        {day.name}")
            print(f"        {day.detail}")

        if show_list and stats.disagreements:
            print(f"\n  every shadowed disagreement ({len(stats.disagreements)}):")
            for d, shadower, served_label, shadowed_label in stats.disagreements:
                print(f"    {d.isoformat()} via {shadower[6:]:<26} "
                      f"served {served_label[:44]!r}")
                print(f"{'':>16}{'':<26}   would {shadowed_label[:44]!r}")

    unverified = [day for days in report.win_days.values() for day in days
                  if day.verdict == "unverified"]
    print(f"\nUnverified win days: {len(unverified)}")
    for day in unverified:
        print(f"  {day.date.isoformat()} {day.tier}: {day.detail}")


if __name__ == "__main__":
    main()
