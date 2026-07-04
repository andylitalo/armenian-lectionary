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


class TestLeapSummerParity(unittest.TestCase):
    """Locks the Second-Volume leap-parity summer split: the same Easter date (03-27)
    ships a distinct saint on the shared civil date in a leap vs a non-leap year, per the
    documented ՍՌ rubric. Before the split the drop-guard had to withhold both, leaving the
    days best-effort; now each ships exact from the cycle tier."""

    def _readings(self, y, m, d):
        ref = os.path.join(os.path.dirname(__file__), os.pardir, "dev",
                           "reference_data", f"{y:04d}-{m:02d}-{d:02d}.json")
        with open(ref) as fh:
            return json.load(fh)["readings"]

    def test_2005_common_vs_2016_leap_diverge_and_match(self):
        # 2005 (common) and 2016 (leap) share Gregorian Easter 03-27.
        for y, iso_days in ((2005, ((7, 23), (7, 30))), (2016, ((7, 23), (7, 30)))):
            for m, d in iso_days:
                res = compute_armenian_lectionary(datetime.date(y, m, d))
                self.assertEqual(res["Source"], "second-volume-cycle",
                                 f"{y}-{m:02d}-{d:02d} should ship from the cycle tier")
                self.assertEqual(res["ReadingsList"], list(self._readings(y, m, d)),
                                 f"{y}-{m:02d}-{d:02d} should exact-match ground truth")
        # The first summer Saturday genuinely differs by leap parity (Peter vs Athanasius).
        self.assertNotEqual(
            compute_armenian_lectionary(datetime.date(2005, 7, 23))["ReadingsList"],
            compute_armenian_lectionary(datetime.date(2016, 7, 23))["ReadingsList"])


class TestWinterMarch(unittest.TestCase):
    """Locks the post-Nativity winter march: the long-window (2011) tail saints that the
    generative laydown mis-placed now ship exact from the cycle tier."""

    def _readings(self, y, m, d):
        ref = os.path.join(os.path.dirname(__file__), os.pardir, "dev",
                           "reference_data", f"{y:04d}-{m:02d}-{d:02d}.json")
        with open(ref) as fh:
            return json.load(fh)["readings"]

    def test_2011_winter_tail_saints_exact(self):
        # Cyprian / Athenogenes / Forefathers / Thaddeus, previously generative misses.
        for m, d in ((1, 31), (2, 1), (2, 3), (2, 12)):
            res = compute_armenian_lectionary(datetime.date(2011, m, d))
            self.assertEqual(res["Source"], "second-volume-cycle",
                             f"2011-{m:02d}-{d:02d} should ship from the cycle tier")
            self.assertEqual(res["ReadingsList"], list(self._readings(2011, m, d)),
                             f"2011-{m:02d}-{d:02d} should exact-match ground truth")


if __name__ == "__main__":
    unittest.main()
