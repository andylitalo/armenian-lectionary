"""Accuracy lock over the RAW feast name -- the exact string downstream stores.

``test_feast.py`` locks the *commemoration component* of ``"Liturgical Day"``. That
projection deliberately discards the calendar-position label, the ``Eve of ...`` note and
the engine's own placeholders, and it discards them from BOTH sides before comparing -- so
on 53% of the corpus it compared ``"" == ""`` and asserted nothing. bahk persists the raw
string into ``Feast.name``, and the difference was not academic: the engine shipped a name
the source contradicted on 41 days across 2001-2026, and six more days as bare
placeholders, all of it invisible to that test (see reports/feast_name_discrepancies.md).

This test compares the raw string, component by component on ``_FEAST_SEP``, after the
registered ``dev/source_corrections`` folds are applied to both sides. Every remaining
difference is therefore either counted by a ratchet or registered as a reviewed
correction; nothing passes silently. The classification lives in
``dev/feast_discrepancy_report`` so the test and the human-readable report can never drift.

The three contracts, strongest first:

  * CONTRADICTIONS == 0 -- a hard assert, the name-side analogue of the readings 0-wrong
    contract. The engine must never emit a component the source does not have.
  * OMISSIONS <= a floor that only moves down. Dropping a component the source carries is
    incomplete but not wrong, so it is ratcheted rather than forbidden.
  * EXACT >= a floor that only moves up.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.feast_discrepancy_report import collect, is_position         # noqa: E402
from tests._reference_cache import requires_reference_cache           # noqa: E402

# Days the engine drops a source component on. All 15 are an "Eve of <Fast>" note on a
# fixed feast whose table key could not keep it (the eve floats across civil years, so
# build_table.unanimous_feast drops it and no verified rule regenerates it yet).
# Monotonic DOWN -- lower it whenever a fix lands, never raise it.
OMISSION_FLOOR = int(os.environ.get("FEAST_OMISSION_FLOOR", "15"))

# Days whose raw name matches the source exactly (or under the registered folds).
# Monotonic UP.
EXACT_FLOOR = int(os.environ.get("FEAST_EXACT_FLOOR", "9481"))

# Days with a source feast name to compare against. Guards against a shrinking cache
# silently shrinking the oracle.
EXPECTED_COMPARED = int(os.environ.get("EXPECTED_COMPARED_DAYS", "9496"))

# Cached days carrying NO source feast name. sacredtradition.am publishes nothing for 2027
# (probed 2026-07-30: an empty page), so its 365 days have no oracle and are skipped here.
# They are covered instead by tests/test_feast_contract.py, which needs no ground truth.
EXPECTED_SKIPPED = int(os.environ.get("EXPECTED_SKIPPED_DAYS", "365"))


@requires_reference_cache
class TestRawFeastName(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = collect()

    def _findings(self, kind):
        return [f for f in self.data["findings"] if f["kind"] == kind]

    def test_no_contradiction(self):
        """The engine never emits a name component the source contradicts."""
        bad = self._findings("CONTRADICTION")
        self.assertEqual(
            [], [(f["iso"], f["contradictions"], f["omissions"]) for f in bad[:10]],
            f"{len(bad)} days ship a feast-name component the source does not have; "
            "regenerate reports/feast_name_discrepancies.md for the full list")

    def test_no_unregistered_casing_variant(self):
        """Case-only differences must be registered in source_corrections, not tolerated."""
        bad = self._findings("CASING")
        self.assertEqual(
            [], [(f["iso"], f["contradictions"], f["omissions"]) for f in bad[:10]],
            f"{len(bad)} days differ from the source only in letter case; either register "
            "the fold in dev/source_corrections._FEAST_CANON_RULES or emit the source's "
            "casing")

    def test_no_position_label_is_ever_dropped(self):
        """Every calendar-position / fast-day marker the source states must be served.

        Stronger than the omission ratchet below, and separate from it on purpose. These
        components are what a fasting calendar is built from -- "Sixth day of the Fast of
        Nativity", "Fast day" -- so losing one is a different kind of failure from losing
        a commemoration's eve note, and must not be absorbed by a shared budget.

        They reach the served name two ways: regenerated per date by
        ``engine._position_label``, or kept in the validated table where every year
        sharing the key agreed. This asserts the union covers the source completely.
        """
        dropped = [(f["iso"], c) for f in self.data["findings"]
                   for c in f["omissions"] if is_position(c)]
        self.assertEqual(
            dropped[:10], [],
            f"{len(dropped)} days lost a position/fast label the source states; run "
            "dev/verify_position_labels.py, whose END-TO-END line must read 0 LOST")

    def test_omissions_within_ratchet(self):
        """Dropped components are allowed, but the count may only shrink."""
        n = len(self._findings("OMISSION"))
        self.assertLessEqual(
            n, OMISSION_FLOOR,
            f"{n} days drop a source component (floor {OMISSION_FLOOR}); a NEW omission "
            "is a regression -- lower the floor when you fix one, never raise it")

    def test_exact_match_floor(self):
        n = self.data["exact"]
        self.assertGreaterEqual(
            n, EXACT_FLOOR,
            f"only {n} days match the source exactly (floor {EXACT_FLOOR})")

    def test_oracle_did_not_shrink(self):
        """A thinner cache must not quietly weaken every assertion above."""
        self.assertGreaterEqual(
            self.data["compared"], EXPECTED_COMPARED,
            f"only {self.data['compared']} days had a source feast name to compare "
            f"(expected >= {EXPECTED_COMPARED})")
        self.assertLessEqual(
            self.data["skipped"], EXPECTED_SKIPPED,
            f"{self.data['skipped']} cached days carry no source feast name (expected "
            f"<= {EXPECTED_SKIPPED}, the 2027 gap); a wider gap means the oracle silently "
            "stopped covering days it used to")

    def test_every_day_is_accounted_for(self):
        """No day escapes classification -- the sum must close."""
        classified = self.data["exact"] + len(self.data["findings"])
        self.assertEqual(
            classified, self.data["compared"],
            "some compared days were neither exact nor recorded as a finding")


if __name__ == "__main__":
    unittest.main()
