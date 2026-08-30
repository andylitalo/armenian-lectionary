"""DEV-ONLY: what the tiers that never win in range actually serve, and whether it holds up.

``_tier_generative_saint`` and ``_tier_fallback`` win on no date in ``MIN_YEAR``-
``MAX_YEAR``, so every reading test in the suite -- all of which compare the SERVED answer
to ground truth -- says nothing about either body. Neither is dead code: the range is
env-overridable and ``_compute_lectionary`` has no range guard.

This walks past ``MAX_YEAR``, finds the days each of those tiers is the one that answers,
and classifies what it serves against the validated table:

  twin        another IN-RANGE date carries the same zone-saint coordinate (identity x
              civil date) and is served from the validated table with the same name and
              readings. Compared on the SERVED output, so the ``_drop_owned_companions``
              overlay is included.
  attested    no twin, but the saint identity the tier placed has a dominant reading set
              across its own validated-table days, and the tier serves that set.
  no-claim    no readings at all -- ``_tier_fallback``'s whole contract.
  unverified  none of the above: the tier serving a reading nothing attests.

Run this before widening ``LECTIONARY_MAX_YEAR``; ``--to`` the new bound must report
``Unverified win days: 0`` (which is also this script's exit status).

    python dev/audit_shadowed_tiers.py [--to YEAR]

Needs no ``dev/reference_data/`` cache: it compares the engine to itself.
"""

import collections
import contextlib
import datetime
import os
import sys
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                       # noqa: E402
from armenian_lectionary.engine import (                                     # noqa: E402
    MAX_YEAR, MIN_YEAR, coords_for,
)

# How far past MAX_YEAR the assertions reach. Both of _tier_generative_saint's live
# coordinates are visible by 2077, so this is slack, not tuning -- but it is NOT
# open-ended: 2152-02-01, -02-03 and -02-12 are genuine `unverified` days (the PN zone
# runs out of saint coordinates and the laydown marches on anyway), and raising PROBE_TO
# past them fails the attestation test for a real reason. Model those before widening.
PROBE_TO = 2130

VALIDATED = "validated-table"
ATTESTED = {"twin", "attested"}


@dataclass(frozen=True)
class WinDay:
    """One date a tier is the ladder's winner on, with what it served and the verdict."""
    date: datetime.date
    tier: str
    coordinate: Optional[str]      # e.g. "cyricus_and_his:07-30"
    name: str
    readings: tuple
    verdict: str
    detail: str


@dataclass
class Report:
    min_year: int
    max_year: int
    probe_to: int
    wins: dict              # tier name -> win count in range
    win_days: dict          # tier name -> [WinDay], for tiers that win nothing in range


@contextlib.contextmanager
def widened_range(probe_to):
    """Let ``compute_armenian_lectionary`` answer past ``MAX_YEAR``.

    The guard is a plain comparison against the module global, which is exactly what
    ``LECTIONARY_MAX_YEAR`` sets. Restored on exit.
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
    """The name of the tier the ladder serves ``d`` from."""
    for tier in engine._TIERS:
        if tier(d) is not None:
            return tier.__name__
    raise RuntimeError(f"no tier resolved {d.isoformat()}")   # _tier_fallback prevents this


def _saint_coordinate(d):
    """``d``'s ``*SaintMD`` coordinate as ``(keyspace, value)``, or ``(None, None)``.

    Identity x civil date: the finest zone-saint coordinate the engine keys on, and the
    one a cross-year twin must share to be evidence about this DAY rather than this saint.
    """
    for keyspace, value in sorted(coords_for(d).items()):
        if keyspace.endswith("SaintMD"):
            return keyspace, value
    return None, None


def validated_index(min_year, max_year):
    """What the validated table serves in range, indexed the two ways we verify by.

    ``twins``  ``*SaintMD`` coordinate -> [(date, name, readings)]
    ``attest`` saint identity -> Counter of reading sets
    """
    twins = collections.defaultdict(list)
    attest = collections.defaultdict(collections.Counter)
    for d in _days(min_year, max_year):
        served = engine.compute_armenian_lectionary(d)
        if served["Source"] != VALIDATED:
            continue
        readings = tuple(served["ReadingsList"])
        keyspace, coordinate = _saint_coordinate(d)
        if coordinate is not None:
            twins[coordinate].append((d, served["Liturgical Day"], readings))
        for key, value in coords_for(d).items():
            if key.endswith("Saint"):
                attest[value][readings] += 1
    return twins, attest


def _verify(d, tier_name, twins, attest, probe_to):
    """Classify what ``tier_name`` serves on ``d``. Routes are in the module docstring."""
    keyspace, coordinate = _saint_coordinate(d)
    # The identity comes from the tier, not from coords_for: the tier is what placed the
    # saint, and the zone coordinate can be absent on exactly the days worth checking.
    placed = engine._generative_saint(d)
    identity = placed[1] if placed else None
    with widened_range(probe_to):
        served = engine.compute_armenian_lectionary(d)
    name, readings = served["Liturgical Day"], tuple(served["ReadingsList"])

    def win(verdict, detail):
        return WinDay(d, tier_name, coordinate, name, readings, verdict, detail)

    if not readings:
        # _tier_fallback: an explicit "not yet modeled", with no readings to be wrong about.
        return win("no-claim", "serves no readings and says so")

    candidates = twins.get(coordinate, ())
    for twin_date, twin_name, twin_readings in candidates:
        if (twin_name, twin_readings) == (name, readings):
            return win("twin", f"byte-identical to {twin_date.isoformat()} "
                               f"({VALIDATED}, same {keyspace})")
    if candidates:
        # A coordinate whose twins disagreed with EACH OTHER would already have failed the
        # table's cross-year consistency rule, so reporting the first says all there is.
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
    """Wins per tier in range, plus every verified win day past it for tiers with none."""
    wins = collections.Counter(_winner(d) for d in _days(min_year, max_year))
    wins = {tier.__name__: wins[tier.__name__] for tier in engine._TIERS}

    twins, attest = validated_index(min_year, max_year)
    win_days = {name: [] for name in wins}
    for d in _days(max_year + 1, probe_to):
        name = _winner(d)
        if wins[name]:
            continue        # it wins in range too; the rest of the suite reaches it there
        win_days[name].append(_verify(d, name, twins, attest, probe_to))

    return Report(min_year, max_year, probe_to, wins, win_days)


def _applies_counts(min_year, max_year):
    """How many days each tier CLAIMS, whether or not it is reached. Report-only: it costs
    a full 13-tiers-per-day pass, and nothing is asserted about it."""
    counts = collections.Counter()
    for d in _days(min_year, max_year):
        for tier in engine._TIERS:
            if tier(d) is not None:
                counts[tier.__name__] += 1
    return counts


def main():
    args = sys.argv[1:]
    probe_to = int(args[args.index("--to") + 1]) if "--to" in args else PROBE_TO
    report = collect(probe_to=probe_to)
    applies = _applies_counts(report.min_year, report.max_year)

    print(f"Tier ladder over {report.min_year}-{report.max_year}\n")
    print(f"  {'tier':<42} {'applies':>8} {'wins':>8}")
    for tier in engine._TIERS:
        name = tier.__name__
        print(f"  {name:<42} {applies[name]:>8} {report.wins[name]:>8}")

    for name, days in report.win_days.items():
        if report.wins[name]:
            continue
        print(f"\n{name}: wins on no date in range; "
              f"{len(days)} day(s) in {report.max_year + 1}-{report.probe_to}")
        for day in days:
            if day.verdict == "no-claim":       # the fallback: one line, it claims nothing
                print(f"    {day.date.isoformat()} [no-claim]")
                continue
            print(f"    {day.date.isoformat()} {day.date:%a}  [{day.verdict}] "
                  f"{day.coordinate or '-'}\n"
                  f"        {day.name}\n        {day.detail}")

    unverified = [day for days in report.win_days.values() for day in days
                  if day.verdict not in ATTESTED and day.verdict != "no-claim"]
    print(f"\nUnverified win days: {len(unverified)}")
    for day in unverified:
        print(f"  {day.date.isoformat()} {day.tier}: {day.detail}")
    return 1 if unverified else 0


if __name__ == "__main__":
    sys.exit(main())
