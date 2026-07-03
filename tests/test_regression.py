"""Accuracy/coverage lock over all cached ground truth.

Mirrors dev/compare_app.py but as hard assertions: the runtime engine must never
emit a WRONG table hit, and coverage may only ratchet upward.
"""

import datetime
import json
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
COVERAGE_RATCHET = int(os.environ.get("COVERAGE_RATCHET", "9384"))


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
        # A non-collision Presentation-of-the-Theotokos (Nov 21) co-celebration:
        # shipped VALIDATED via the embedded proper ++ movable-slot composite.
        res = compute_armenian_lectionary(datetime.date(2005, 11, 21))
        self.assertEqual(res["Source"], "validated-composite")
        self.assertTrue(res["ReadingsList"])

    def test_nov21_advlen46_collision_recovered(self):
        # The three Heesnak-Sunday collision years (adv_len == 46, Nov 21 IS the
        # Advent Sunday) resolve via the Tonats'oyts co-celebration rule: the proper
        # ++ the "Eleventh Sunday after the Holy Cross" (band-47-validated) readings.
        # Exact-matches the ground-truth cache; see
        # docs/sources/tonatsooyts-presentation-theotokos.md.
        expected_tail = [
            "Isaiah 29.11-20",
            "St. Paul's Epistle to the Philippians 4.8-23",
            "Luke 11.1-13",
        ]
        ref_dir = os.path.join(os.path.dirname(__file__), os.pardir,
                               "dev", "reference_data")
        for year in (2004, 2010, 2021):
            res = compute_armenian_lectionary(datetime.date(year, 11, 21))
            self.assertEqual(res["Source"], "validated-composite",
                             f"{year}-11-21 should ship validated-composite")
            self.assertEqual(res["ReadingsList"][-3:], expected_tail,
                             f"{year}-11-21 tail should be the 11th Sunday readings")
            with open(os.path.join(ref_dir, f"{year}-11-21.json")) as fh:
                gt = json.load(fh)["readings"]
            self.assertEqual(res["ReadingsList"], gt,
                             f"{year}-11-21 should exact-match ground truth")


if __name__ == "__main__":
    unittest.main()
