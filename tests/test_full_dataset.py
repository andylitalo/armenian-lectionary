"""Comprehensive accuracy lock over the ENTIRE cached ground truth.

Unlike test_regression.py (an absolute-count ratchet, kept backwards-compatible
with pre-backfill checkouts), this is the canonical lock over the whole
dev/reference_data/ cache:

  * the runtime engine must NEVER emit a wrong table hit (0-wrong contract),
  * exact-match coverage must stay at/above a PERCENTAGE floor (raised per
    chunk as the engine improves), and
  * the total reference-day count must not silently shrink (data-loss guard).

The percentage floor and expected total are env-overridable so a thinner
checkout can run the same test with adjusted thresholds.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all  # noqa: E402
from lectionary import compute_armenian_lectionary  # noqa: E402

# Raised per chunk as coverage climbs toward 100%. Chunk 4 (length-classed
# summer/autumn/post-Exaltation hinge grids) reaches 9046/9495 = 95.3%.
COVERAGE_PCT_FLOOR = float(os.environ.get("COVERAGE_PCT_FLOOR", "95.1"))
# Lower bound on processed reference days; guards against silent data loss.
EXPECTED_TOTAL_DAYS = int(os.environ.get("EXPECTED_TOTAL_DAYS", "9495"))


class TestFullDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_no_wrong_and_coverage_floor(self):
        ok = wrong = est = 0
        for iso, day in self.days.items():
            if not day["readings"] and not day["feast"]:
                continue
            res = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
            if res["Source"] == "algorithmic-estimate":
                est += 1
            elif res["ReadingsList"] == list(day["readings"]):
                ok += 1
            else:
                wrong += 1

        total = ok + wrong + est
        pct = ok / total * 100 if total else 0.0

        # 0-wrong contract: every shipped reading matches truth.
        self.assertEqual(wrong, 0, "engine produced a wrong table hit")
        # No silent data loss.
        self.assertGreaterEqual(
            total, EXPECTED_TOTAL_DAYS,
            f"only {total} reference days processed (< {EXPECTED_TOTAL_DAYS})")
        # Coverage percentage floor (monotonic upward).
        self.assertGreaterEqual(
            pct, COVERAGE_PCT_FLOOR,
            f"exact-match {pct:.2f}% fell below floor {COVERAGE_PCT_FLOOR}%")


if __name__ == "__main__":
    unittest.main()
