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
# summer/autumn/post-Exaltation hinge grids) reached 9046/9495 = 95.3%; chunk 5
# (post-Nativity saint-identity replay, PnSaint keyspace) reaches 9088/9495 = 95.7%;
# chunk 6 (Easter-band sub-key EB, pn_len-banded Easter core) reaches 9199/9495 = 96.9%;
# chunk 7 (Advent-length-banded Heesnak keys HEB/HEpB) reaches 9252/9495 = 97.4%;
# chunk 8 (post-Nativity Wed/Fri forward continua index PnFerF) reaches 9271/9495 = 97.6%;
# chunk 9 (Stage A: hinge saint-identity replay TrSaint/AsSaint/ExSaint) reaches 9273/9495 = 97.7%;
# chunk 10 (Stage B: Easter-band saint sub-keys {Zone}SaintB) reaches 9310/9495 = 98.0%;
# chunk 11 (Stage C: saint-identity x civil-date sub-keys {Zone}SaintMD) reaches 9329/9495 = 98.25%;
# chunk 12 (residual-tail quick wins: 2011 Easter order, PnOct Naming octave, PnEveN
# eve-of-Fast Sunday-number, As/ExSatMD weekday x civil-date saint grid) reaches 9346/9495 = 98.43%.
COVERAGE_PCT_FLOOR = float(os.environ.get("COVERAGE_PCT_FLOOR", "98.4"))
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
