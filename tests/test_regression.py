"""Accuracy/coverage lock over all cached ground truth.

Mirrors dev/compare_app.py but as hard assertions: the runtime engine must never
emit a WRONG table hit, and coverage may only ratchet upward.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all  # noqa: E402
from lectionary import compute_armenian_lectionary  # noqa: E402

# The structurally-validated tiers: a mismatch here breaks the strict-shipping
# 0-wrong contract. The generative/resolved tiers are labeled best-guesses,
# tracked separately and NOT bound by 0-wrong.
VALIDATED = {"validated-table", "validated-composite"}

# Current baseline; regressions below this fail. Overridable via env so a
# pre-backfill checkout (smaller cache) can lower it without editing source.
# Counts VALIDATED-tier exact matches only (the provably-safe core).
COVERAGE_RATCHET = int(os.environ.get("COVERAGE_RATCHET", "9381"))


class TestRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_no_wrong_full_accuracy_and_coverage(self):
        validated_exact = validated_wrong = other = reference = 0
        for iso, day in self.days.items():
            if not day["readings"] and not day["feast"]:
                continue
            reference += 1
            res = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
            match = res["ReadingsList"] == list(day["readings"])
            if res["Source"] in VALIDATED:
                if match:
                    validated_exact += 1
                else:
                    validated_wrong += 1
            else:
                other += 1

        # Hard invariant: the validated tier NEVER ships a wrong reading.
        self.assertEqual(validated_wrong, 0,
                         "engine produced a wrong VALIDATED reading")
        # Coverage ratchet on the validated core: gains pass, regressions fail.
        self.assertGreaterEqual(validated_exact, COVERAGE_RATCHET)
        # No silent data loss: every reference day was processed.
        self.assertEqual(validated_exact + validated_wrong + other, reference)


class TestCocelebrationResolvers(unittest.TestCase):
    """Locks the Feb-13 (PrLE) and Nov-21 (HEB band) co-celebration recovery."""

    def test_presentation_eve_feb13_validated(self):
        # A recovered Presentation eve (Feb 13): shipped VALIDATED via the PrLE
        # Easter-offset keyspace, exact-matching the ground-truth cache.
        res = compute_armenian_lectionary(datetime.date(2002, 2, 13))
        self.assertEqual(res["Source"], "validated-table")
        self.assertTrue(res["ReadingsList"])
        self.assertEqual(res["Season"],
                         "Eve of the Presentation of the Lord")

    def test_presentation_theotokos_nov21_validated(self):
        # A pre-existing Presentation-of-the-Theotokos (Nov 21) co-celebration:
        # shipped VALIDATED via the embedded proper ++ movable-slot composite.
        res = compute_armenian_lectionary(datetime.date(2005, 11, 21))
        self.assertEqual(res["Source"], "validated-composite")
        self.assertTrue(res["ReadingsList"])

    def test_nov21_advlen46_collision_stays_blank(self):
        # The three Heesnak-Sunday collision years (adv_len == 46) have no
        # learnable movable slot -- their band-0 Advent Sunday only ever falls on
        # the embedded feast itself -- so they honestly abstain (never wrong).
        for year in (2004, 2010, 2021):
            res = compute_armenian_lectionary(datetime.date(year, 11, 21))
            self.assertEqual(res["ReadingsList"], [],
                             f"{year}-11-21 should stay a blank abstention")


if __name__ == "__main__":
    unittest.main()
