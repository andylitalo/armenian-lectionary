"""What the tiers that never win in range actually serve -- the one thing no other test sees.

Two of the thirteen adapters on ``engine._TIERS`` win on **no date** in ``MIN_YEAR``-
``MAX_YEAR``. ``_tier_generative_saint`` applies on 1,904 days and is shadowed on every
one, by ``_tier_validated_table`` (1,835) and ``_tier_cycle_saint`` (69);
``_tier_fallback`` applies on all 9,861 and is claimed earlier every time.

Neither is dead code. ``_compute_lectionary`` has no range guard, the supported range is
env-overridable by design -- the deploy runbook widens it with one
``gcloud run services update``, and the engine's own ``ValueError`` tells a library
consumer to do the same -- so both bodies run for real consumers. But every reading test in
this suite compares the **served** answer to ground truth, and in range these tiers never
are it. ``tests/test_tier_ladder.py`` asserts their PLACE on the ladder; nothing asserted
that either body produces anything, let alone anything right.

Two things are pinned here, and they are different in kind:

* **reachable** -- each of the thirteen wins on some date in the probe window, is a
  ``_TierResult`` there, and is what ``_compute_lectionary`` serves. A tier that can win
  nowhere at all is dead code the ladder test would still pass on.
* **attested** -- for every day ``_tier_generative_saint`` is the tier that answers, the
  readings it serves are ones the validated table independently attests: either an
  in-range day at the SAME zone-saint coordinate serves exactly this, or the saint identity
  it places has a dominant validated reading set and this is it. A day satisfying neither
  is the tier inventing a reading, which is the failure worth catching.

What is deliberately NOT asserted is the shadowing itself. That two tiers win nothing today
is a fact about the current data -- one more validated coordinate, or one more Second
Volume page transcribed, could change it -- and pinning it would make an improvement look
like a regression. The audit reports it; this file does not hold it.

Nor is the per-day march order asserted. ``gregory_of_theologian`` follows
``eugenios_makarios_valerian`` in 12 of the 15 in-range years where both appear, and in
2001, 2007 and 2019 ``fathers_saints_athanasius`` comes between them -- the trio's order is
itself year-type dependent, so pinning it would fail for a correct reason.

Needs no ``dev/reference_data/`` cache: the engine is compared to itself. Runs in CI, which
is the point -- the ground-truth tests that would notice a served-reading regression are
the ones CI skips.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.audit_shadowed_tiers import PROBE_TO, collect                       # noqa: E402
from armenian_lectionary import engine                                       # noqa: E402

# Verdicts that mean the validated data attests what was served. "no-claim" is the
# fallback's: it serves no readings and flags them not-yet-modeled, so there is nothing
# to attest -- which is why it is accepted here for that tier only, below.
ATTESTED = {"twin", "attested"}


_REPORT = None


def _scan():
    """One scan for the whole module. It walks 2001-PROBE_TO and costs a few seconds, so
    ``setUpClass`` per class would pay for it once per class rather than once."""
    global _REPORT
    if _REPORT is None:
        _REPORT = collect()
    return _REPORT


class TierScan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = _scan()


class TestEveryTierBodyIsReachable(TierScan):
    """A tier nothing can reach is dead code, and the ladder test cannot tell."""

    def _winning_dates(self, name):
        """Dates the tier is the ladder's answer on: in range if it wins there, else the
        probe window's."""
        if self.report.wins[name]:
            return None            # it wins in range; other tests reach it there
        return [day.date for day in self.report.win_days[name]]

    def test_every_tier_wins_on_some_date(self):
        """Winning nowhere in range is fine and true of two of them. Winning nowhere at
        ALL means the body never runs, anywhere, for anyone."""
        for tier in engine._TIERS:
            name = tier.__name__
            with self.subTest(tier=name):
                dates = self._winning_dates(name)
                self.assertTrue(
                    dates is None or dates,
                    f"{name} wins on no date in {self.report.min_year}-{PROBE_TO}: "
                    f"nothing reaches its body")

    def test_a_tier_that_never_wins_in_range_still_serves_what_it_returns(self):
        """End to end on a date it actually wins: the body returns a ``_TierResult`` and
        ``_compute_lectionary`` hands that tier's ``Source`` to the consumer. The ladder
        test can only check this on dates some tier wins in range."""
        for tier in engine._TIERS:
            name = tier.__name__
            dates = self._winning_dates(name)
            if not dates:
                continue
            d = dates[0]
            with self.subTest(tier=name, date=d.isoformat()):
                result = tier(d)
                self.assertIsInstance(result, engine._TierResult)
                self.assertEqual(engine._compute_lectionary(d)["Source"], result.source)

    def test_no_tier_applies_on_zero_dates(self):
        """Distinct from winning nowhere, and worse: a tier that never even applies is
        unreachable no matter how the ladder is ordered."""
        for tier in engine._TIERS:
            with self.subTest(tier=tier.__name__):
                self.assertGreater(self.report.applies[tier.__name__], 0)


class TestWhatTheGenerativeSaintTierServesIsAttested(TierScan):
    """Its readings must be ones the validated table attests -- on every day it serves.

    This tier's territory is the complement of two deliberate conservatism rules:
    ``dev/build_table.py`` harvests an anchored key only via ``_consistent(items, 2)``, so
    a coordinate occurring once in range is dropped on purpose, and ``_CYCLE_SAINTS``
    carries only the days each year-type's Second Volume page prints. What is left is a
    handful of days per century, and nothing else in the suite can look at them.
    """

    def test_every_win_day_is_twinned_or_attested(self):
        for day in self.report.win_days["_tier_generative_saint"]:
            with self.subTest(date=day.date.isoformat(), coordinate=day.coordinate):
                self.assertIn(
                    day.verdict, ATTESTED,
                    f"{day.date.isoformat()} ({day.coordinate}) serves {day.name!r} with "
                    f"readings the validated table does not attest: {day.detail}")

    def test_it_serves_something(self):
        """The guard on the test above: an empty win-day list would pass it vacuously,
        and that is exactly what a tier quietly ceasing to fire looks like."""
        self.assertTrue(self.report.win_days["_tier_generative_saint"])


class TestTheFallbackNeverInventsReadings(TierScan):
    """Its whole contract: name the season, serve nothing, say the day is not modeled.

    It cannot be wrong about readings because it claims none -- but only while that stays
    true. A future edit giving it a best guess would make the ladder's terminator into an
    unvalidated reading source with no tier below it to be filtered down to."""

    def test_every_fallback_win_serves_no_readings(self):
        days = self.report.win_days["_tier_fallback"]
        self.assertTrue(days, "the fallback wins on no date; see the reachability test")
        for day in days:
            with self.subTest(date=day.date.isoformat()):
                self.assertEqual(day.verdict, "no-claim")
                self.assertEqual(day.readings, ())


if __name__ == "__main__":
    unittest.main()
