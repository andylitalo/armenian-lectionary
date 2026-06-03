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

# Current baseline; regressions below this fail. Overridable via env so a
# pre-backfill checkout (smaller cache) can lower it without editing source.
COVERAGE_RATCHET = int(os.environ.get("COVERAGE_RATCHET", "9199"))


class TestRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_no_wrong_full_accuracy_and_coverage(self):
        ok = wrong = est = 0
        reference = 0
        for iso, day in self.days.items():
            if not day["readings"] and not day["feast"]:
                continue
            reference += 1
            res = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
            if res["Source"] == "algorithmic-estimate":
                est += 1
            elif res["ReadingsList"] == list(day["readings"]):
                ok += 1
            else:
                wrong += 1

        covered = ok + wrong
        # Hard invariant: every table hit matches truth.
        self.assertEqual(wrong, 0, "engine produced a wrong table hit")
        # Accuracy where covered must be exactly 100%.
        self.assertEqual(ok, covered)
        # Coverage ratchet: legitimate gains pass, regressions fail.
        self.assertGreaterEqual(covered, COVERAGE_RATCHET)
        # No silent data loss: every reference day was processed.
        self.assertEqual(ok + wrong + est, reference)


if __name__ == "__main__":
    unittest.main()
