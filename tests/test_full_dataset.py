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

# Structurally-validated tiers (bound by the 0-wrong contract) vs. the labeled tiers
# that ship readings but are not cache cross-year validated (tracked separately).
VALIDATED = {"validated-table", "validated-composite"}
# Best-effort tiers: the generative best-guess laydown/continua, and the Second-Volume
# directory cycle. The cycle tier is build-time checked for cache consistency
# (dev/build_second_volume_cycles.py drops any entry contradicted by ground truth), so
# it ships 0 wrong on the cache -- asserted below.
BEST_EFFORT = {"generative-saint", "generative-continua", "second-volume-cycle"}
DIRECTORY = {"second-volume-cycle"}

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
# chunk 13 (generative best-guess saint laydown over the residual floating /
# extreme-Easter saint-weekdays) lifts non-blank COVERAGE to ~99.1%; chunk 14
# (Annunciation Easter-offset keyspace AnnE -- the Holy-Week reorder is
# deterministic in the Easter offset) raises VALIDATED-tier exact 9346 -> 9364 /
# 9495 = 98.62% (0-wrong frozen) and coverage to ~99.3%.
COVERAGE_PCT_FLOOR = float(os.environ.get("COVERAGE_PCT_FLOOR", "98.6"))
# Lower bound on processed reference days; guards against silent data loss.
EXPECTED_TOTAL_DAYS = int(os.environ.get("EXPECTED_TOTAL_DAYS", "9495"))
# Floor on the fraction of all days that ship ANY readings (validated + best-guess).
# chunk 15 (generative-continua: Fast-of-Assumption Wed/Fri lectio-continua tail)
# lifts coverage to ~99.4%.
COVERAGE_ANY_PCT_FLOOR = float(os.environ.get("COVERAGE_ANY_PCT_FLOOR", "99.4"))
# chunk 16 (Second-Volume directory cycle tier: per-year-type saint resolved from the
# Tonatsoyts Second Volume, matched by Easter date) adds 16 cache-exact, 0-wrong days
# over the residual floating saints, lifting best-effort exact 24 -> 39.
# Floor on best-effort days (generative + directory) that turn out exact on the cache
# (monotonic up; guards the saint-laydown / continua / cycle tiers from regressing).
BEST_EFFORT_EXACT_FLOOR = int(os.environ.get("BEST_EFFORT_EXACT_FLOOR", "38"))


class TestFullDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_no_wrong_and_coverage_floor(self):
        validated_exact = validated_wrong = blank = nonblank = 0
        best_effort_exact = directory_wrong = 0
        for iso, day in self.days.items():
            if not day["readings"] and not day["feast"]:
                continue
            res = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
            src = res["Source"]
            if src == "algorithmic-estimate":
                blank += 1
                continue
            nonblank += 1
            match = res["ReadingsList"] == list(day["readings"])
            if src in VALIDATED:
                if match:
                    validated_exact += 1
                else:
                    validated_wrong += 1
            elif src in BEST_EFFORT:
                if match:
                    best_effort_exact += 1
                elif src in DIRECTORY:
                    directory_wrong += 1

        total = blank + nonblank
        val_pct = validated_exact / total * 100 if total else 0.0
        any_pct = nonblank / total * 100 if total else 0.0

        # 0-wrong contract: the VALIDATED tier never ships a wrong reading.
        self.assertEqual(validated_wrong, 0,
                         "engine produced a wrong VALIDATED reading")
        # The Second-Volume cycle tier is cache-consistency-checked at build time, so
        # it must ship 0 wrong on the cache.
        self.assertEqual(directory_wrong, 0,
                         "Second-Volume cycle tier produced a wrong reading on the cache")
        # No silent data loss.
        self.assertGreaterEqual(
            total, EXPECTED_TOTAL_DAYS,
            f"only {total} reference days processed (< {EXPECTED_TOTAL_DAYS})")
        # Validated exact-match floor (monotonic upward, structurally safe).
        self.assertGreaterEqual(
            val_pct, COVERAGE_PCT_FLOOR,
            f"validated exact-match {val_pct:.2f}% below floor {COVERAGE_PCT_FLOOR}%")
        # Any-readings coverage floor (the generative tier fills the blanks).
        self.assertGreaterEqual(
            any_pct, COVERAGE_ANY_PCT_FLOOR,
            f"coverage {any_pct:.2f}% below floor {COVERAGE_ANY_PCT_FLOOR}%")
        # Best-effort exact-on-cache floor (generative + directory; monotonic up).
        self.assertGreaterEqual(
            best_effort_exact, BEST_EFFORT_EXACT_FLOOR,
            f"best-effort exact {best_effort_exact} below floor "
            f"{BEST_EFFORT_EXACT_FLOOR}")


if __name__ == "__main__":
    unittest.main()
