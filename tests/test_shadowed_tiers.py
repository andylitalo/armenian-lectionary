"""The two tiers that never win in range: that their bodies run, and what they serve.

``_tier_generative_saint`` and ``_tier_fallback`` win on no date in ``MIN_YEAR``-
``MAX_YEAR``, so every reading test here -- all of which compare the SERVED answer to
ground truth -- says nothing about either body. ``tests/test_tier_ladder.py`` asserts their
PLACE on the ladder, not that either produces anything. Neither is dead code: the range is
env-overridable and ``_compute_lectionary`` has no range guard, so both run for real
consumers.

Pinned here: every tier is reachable and is what ``_compute_lectionary`` serves; every
reading ``_tier_generative_saint`` serves is attested by the validated table; and
``_tier_fallback`` serves none. NOT pinned: the shadowing itself, which is a fact about the
current data -- one more validated coordinate would change it, and an improvement should
not read as a regression. ``dev/audit_shadowed_tiers.py`` reports that.

Needs no ``dev/reference_data/`` cache, so it runs in CI -- which is the point, since the
ground-truth tests that would notice a served-reading regression are the ones CI skips.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.audit_shadowed_tiers import ATTESTED, PROBE_TO, collect             # noqa: E402
from armenian_lectionary import engine                                       # noqa: E402

_REPORT = None


def _scan():
    """One scan for the module: it walks 2001-PROBE_TO and costs a few seconds."""
    global _REPORT
    if _REPORT is None:
        _REPORT = collect()
    return _REPORT


class TierScan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = _scan()

    def _win_dates(self, name):
        """Dates the tier is the ladder's answer on, or None if it wins in range (where
        the rest of the suite already reaches it)."""
        if self.report.wins[name]:
            return None
        return [day.date for day in self.report.win_days[name]]


class TestEveryTierBodyIsReachable(TierScan):

    def test_every_tier_wins_on_some_date(self):
        """Winning nowhere in range is fine and true of two of them. Winning nowhere at
        ALL means the body never runs, anywhere, for anyone -- and the ladder test passes
        on it regardless."""
        for tier in engine._TIERS:
            with self.subTest(tier=tier.__name__):
                dates = self._win_dates(tier.__name__)
                self.assertTrue(dates is None or dates,
                                f"{tier.__name__} wins on no date in "
                                f"{self.report.min_year}-{PROBE_TO}")

    def test_a_tier_that_never_wins_in_range_still_serves_what_it_returns(self):
        """End to end on a date it wins: the body returns a ``_TierResult`` and
        ``_compute_lectionary`` hands that tier's ``Source`` to the consumer."""
        for tier in engine._TIERS:
            dates = self._win_dates(tier.__name__)
            if not dates:
                continue
            d = dates[0]
            with self.subTest(tier=tier.__name__, date=d.isoformat()):
                result = tier(d)
                self.assertIsInstance(result, engine._TierResult)
                self.assertEqual(engine._compute_lectionary(d)["Source"], result.source)


class TestWhatTheGenerativeSaintTierServesIsAttested(TierScan):
    """Its readings must be ones the validated table attests, on every day it serves.

    Its territory is the complement of two deliberate conservatism rules --
    ``build_table``'s ``_consistent(items, 2)`` drops a coordinate seen in only one year,
    and ``_CYCLE_SAINTS`` carries only the days each year-type's Second Volume page prints
    -- so what is left is a handful of days per century that nothing else can look at.
    """

    def test_every_win_day_is_twinned_or_attested(self):
        days = self.report.win_days["_tier_generative_saint"]
        # Not vacuous: an empty list is what a tier quietly ceasing to fire looks like.
        self.assertTrue(days, "it wins on no date; see the reachability test")
        for day in days:
            with self.subTest(date=day.date.isoformat(), coordinate=day.coordinate):
                self.assertIn(day.verdict, ATTESTED,
                              f"{day.date.isoformat()} ({day.coordinate}) serves "
                              f"{day.name!r} with readings the validated table does not "
                              f"attest: {day.detail}")


class TestTheFallbackNeverInventsReadings(TierScan):
    """Its whole contract: name the season, serve nothing, flag the day as not modeled.

    It cannot be wrong about readings because it claims none -- but only while that stays
    true. A future edit giving it a best guess would make the ladder's terminator an
    unvalidated reading source with no tier below it to be filtered down to."""

    def test_every_fallback_win_serves_no_readings(self):
        days = self.report.win_days["_tier_fallback"]
        self.assertTrue(days, "it wins on no date; see the reachability test")
        for day in days:
            with self.subTest(date=day.date.isoformat()):
                self.assertEqual(day.verdict, "no-claim")
                self.assertEqual(day.readings, ())


if __name__ == "__main__":
    unittest.main()
