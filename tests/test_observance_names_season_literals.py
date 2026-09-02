"""Pins the bug the Assumption's fuller name left in dev/observance_names.py.

``commemoration_of`` isolates a feast string's commemoration by stripping a leading
"Nth day of <season>" / "Nth Sunday after/of <anchor>" position label, matched against
``_SEASONS``/``_ANCHORS``. Those lists already read the Illuminator, Nisibis and Prophet
Elijah fasts' bare names live from the catalog (``_served_season_name``), specifically so a
TSV rename cannot leave a stale hardcoded copy here. The Assumption's own two families were
not wired the same way: when its position labels grew from "the Assumption" to "the
Assumption of the Holy Mother of God", the bare short literal only matched the FIRST word
of the new season name, leaving "of the Holy Mother of God" glued onto whatever
commemoration followed instead of stripped.

``tests/test_observance.py`` does not catch this on its own, because the reference cache it
reads is itself corrected on load through the same TSV -- both sides of that comparison get
the identical contamination and still match each other, so the test stays green while
silently losing precision on these two families. This file checks the extraction directly,
against the real committed catalog, independent of that coincidence.

Needs no ground-truth cache; runs in CI.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import compute_armenian_lectionary        # noqa: E402
from dev.observance_names import commemoration_of                         # noqa: E402


class TestAssumptionPositionLabelsStripCleanly(unittest.TestCase):
    """Each date pins a specific, already-known-composite-or-not day rather than scanning
    the whole range, so a failure names exactly which family regressed."""

    def _served(self, iso):
        return compute_armenian_lectionary(datetime.date.fromisoformat(iso))["Liturgical Day"]

    def test_a_plain_fast_day_strips_to_nothing(self):
        # 2026-08-10: "First day of the Fast of the Assumption of the Holy Mother of God"
        served = self._served("2026-08-10")
        self.assertIn("Assumption of the Holy Mother of God", served)
        self.assertEqual(commemoration_of(served), "")

    def test_a_composite_octave_day_leaves_only_its_companion(self):
        # 2026-08-17: "...the Assumption of the Holy Mother of God — Remembrance of the Dead"
        served = self._served("2026-08-17")
        self.assertIn("Assumption of the Holy Mother of God", served)
        commem = commemoration_of(served)
        self.assertEqual(commem, "Remembrance of the Dead")
        self.assertNotIn("Holy Mother of God", commem)

    def test_a_following_sunday_strips_to_nothing(self):
        # 2026-08-23: "Second Sunday of the Assumption of the Holy Mother of God"
        served = self._served("2026-08-23")
        self.assertIn("Assumption of the Holy Mother of God", served)
        self.assertEqual(commemoration_of(served), "")

    def test_no_residual_fragment_of_the_season_name_survives(self):
        """The general shape of the bug: whatever IS extracted must never itself contain
        the tail of a season/anchor name, which is what a partial prefix match leaves
        behind."""
        for iso in ("2026-08-10", "2026-08-17", "2026-08-23"):
            with self.subTest(iso=iso):
                commem = commemoration_of(self._served(iso))
                self.assertNotIn("Holy Mother of God", commem)
                self.assertNotIn("Assumption", commem)


if __name__ == "__main__":
    unittest.main()
