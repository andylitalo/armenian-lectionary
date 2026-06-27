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
COVERAGE_RATCHET = int(os.environ.get("COVERAGE_RATCHET", "9364"))


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


if __name__ == "__main__":
    unittest.main()
