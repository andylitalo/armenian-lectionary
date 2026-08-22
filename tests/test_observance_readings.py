"""The observance we name is the observance whose readings we serve.

This is the contract that makes the remaining packing differences safe to leave alone. The
Tonatsoyts packs several First Volume canons onto one day when the taregir leaves few days
for them (docs/observance-name-corrections.md section 7), and which canons a given year-type
names varies. The engine serves one packing per liturgical coordinate, so on a handful of
days it names a canon the source did not, or misses one the source did.

That is tolerable ONLY because the packing does not decide the propers. The source keys its
readings to the HEAD canon and does not change them when it names more companions: every
Cyricus-headed line ships Cyricus's five readings, every Vahan-headed line ships Vahan's
four. A packing difference is a difference of naming, never of reading.

"Tolerable only because" was a load-bearing claim with nothing checking it. The raw-name
tests measure names against the source; test_full_dataset measures readings against the
source; neither would notice the two drifting apart, because each day would still be
individually explicable on its own axis. This file asserts the JOIN: of the days whose name
differs from the source, none may serve different readings.

If it ever fails, a name difference has started coming with a reading difference -- and then
it is the day's entry that is wrong, not its name.

Scoping matches tests/test_full_dataset: the first-volume-cohort tier serves the source's own
verse ranges, so the cache oracle is reconciled through the same reviewed corrections. No
tier is excluded -- as of writing all 57 name-differing days pass, second-volume-cycle
included, which is the point.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import compute_armenian_lectionary      # noqa: E402
from dev.analyze import load_all                                        # noqa: E402
from tests._reference_cache import requires_reference_cache             # noqa: E402
from tests.test_full_dataset import apply_cohort_corrections            # noqa: E402

# Days whose served name is not the source's byte for byte. Informational, but pinned as a
# floor so a refactor cannot quietly empty the population this test measures and leave it
# passing vacuously.
EXPECTED_NAME_DIFFERING_DAYS = int(
    os.environ.get("EXPECTED_NAME_DIFFERING_DAYS", "40"))


@requires_reference_cache
class TestObservanceMatchesReadings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_a_name_difference_never_comes_with_a_reading_difference(self):
        offenders = []
        differing = 0
        for iso in sorted(self.days):
            day = self.days[iso]
            src_name = (day.get("feast") or "").strip()
            src_reads = list(day.get("readings") or [])
            if not src_name or not src_reads:
                continue
            got = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
            if got["Liturgical Day"] == src_name:
                continue
            differing += 1
            expected = (apply_cohort_corrections(src_reads)
                        if got["Source"] == "first-volume-cohort" else src_reads)
            if got["ReadingsList"] != expected:
                offenders.append((iso, got["Source"], got["Liturgical Day"][:60],
                                  src_name[:60]))

        self.assertGreaterEqual(
            differing, EXPECTED_NAME_DIFFERING_DAYS,
            f"only {differing} days have a name that differs from the source (expected "
            f">= {EXPECTED_NAME_DIFFERING_DAYS}); this test asserts nothing about a "
            "population that has vanished")
        self.assertEqual(
            offenders[:10], [],
            f"{len(offenders)} of {differing} days whose NAME differs from the source also "
            "serve different READINGS. A name difference is only safe while the propers "
            "still match: these days name one observance and read another.")


if __name__ == "__main__":
    unittest.main()
