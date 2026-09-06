"""Unit tests for the ``CommemorationIds`` field (engine.py's ``_commemoration_ids``).

Like ``FastIds`` (tests/test_fast_ids.py), this is a filter over the already-resolved
``ObservanceIds`` field rather than a second text resolution, so it inherits that field's
all-or-nothing, fully-covered-in-range guarantee for free. What these tests add is the
thing that made the field necessary: ``CommemorationIds`` is **not** the complement of
``FastIds``, and must never be reimplemented as one. Self-contained: no ground-truth cache
needed.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402
from armenian_lectionary import compute_armenian_lectionary                # noqa: E402

# "Fifth Sunday of Eastertide - Appearance of the Holy Cross": a position label the day
# does not commemorate, beside a commemoration it does. The whole point of the field.
POSITION_PLUS_COMMEMORATION = datetime.date(2026, 5, 3)
PLAIN_POSITION_DAY = datetime.date(2026, 1, 8)    # "Third day of Nativity" -- neither
WEEKLY_FAST_DAY = datetime.date(2026, 1, 14)      # "Wednesday Fast" -- a fast, not a comm
GREAT_FRIDAY = datetime.date(2026, 4, 3)          # both, on the same id
EVE_ONLY_DAY = datetime.date(2026, 1, 5)          # Eve of the Nativity is the ONLY component


class TestCommemorationIdsShape(unittest.TestCase):
    def test_a_position_label_is_dropped_and_its_commemoration_kept(self):
        result = compute_armenian_lectionary(POSITION_PLUS_COMMEMORATION)
        self.assertEqual(result["ObservanceIds"],
                         ["fifth_sunday_of_eastertide", "appearance_of_the_holy_cross"])
        self.assertEqual(result["CommemorationIds"], ["appearance_of_the_holy_cross"])

    def test_a_bare_position_day_commemorates_nothing(self):
        self.assertEqual(
            compute_armenian_lectionary(PLAIN_POSITION_DAY)["CommemorationIds"], [])

    def test_the_only_component_may_be_an_eve(self):
        """Jan 5 serves the eve and nothing else, so excluding eves wholesale would leave
        the Nativity vigil with no commemoration at all."""
        result = compute_armenian_lectionary(EVE_ONLY_DAY)
        self.assertEqual(result["ObservanceIds"], ["eve_of_the_nativity"])
        self.assertEqual(result["CommemorationIds"], ["eve_of_the_nativity"])

    def test_commemoration_ids_is_a_subset_of_observance_ids_in_order(self):
        result = compute_armenian_lectionary(GREAT_FRIDAY)
        self.assertEqual(
            result["CommemorationIds"],
            [sid for sid in result["ObservanceIds"] if sid in result["CommemorationIds"]])
        for sid in result["CommemorationIds"]:
            self.assertIn(sid, result["ObservanceIds"])

    def test_filters_out_non_commemoration_and_unknown_ids(self):
        self.assertEqual(engine._commemoration_ids([]), [])
        self.assertEqual(
            engine._commemoration_ids(["third_day_of_nativity", "not_a_real_id"]), [])
        self.assertEqual(
            engine._commemoration_ids(
                ["third_day_of_nativity", "appearance_of_the_holy_cross"]),
            ["appearance_of_the_holy_cross"])


class TestCommemorationIdsAreNotTheComplementOfFastIds(unittest.TestCase):
    """The field exists because ``ObservanceIds`` minus ``FastIds`` answers a different
    question. These four cases are the whole argument, one per quadrant -- if a later
    change makes any of them pass by computing one set from the other, they fail."""

    def test_an_observance_can_be_both_a_fast_and_a_commemoration(self):
        result = compute_armenian_lectionary(GREAT_FRIDAY)
        self.assertIn("great_friday", result["FastIds"])
        self.assertIn("great_friday", result["CommemorationIds"])

    def test_an_observance_can_be_neither(self):
        result = compute_armenian_lectionary(PLAIN_POSITION_DAY)
        self.assertEqual(result["FastIds"], [])
        self.assertEqual(result["CommemorationIds"], [])
        self.assertNotEqual(result["ObservanceIds"], [])

    def test_a_fast_that_is_not_a_commemoration(self):
        result = compute_armenian_lectionary(WEEKLY_FAST_DAY)
        self.assertEqual(result["FastIds"], ["wednesday_fast"])
        self.assertEqual(result["CommemorationIds"], [])

    def test_a_commemoration_that_is_not_a_fast(self):
        result = compute_armenian_lectionary(POSITION_PLUS_COMMEMORATION)
        self.assertEqual(result["FastIds"], [])
        self.assertEqual(result["CommemorationIds"], ["appearance_of_the_holy_cross"])


class TestCommemorationIdsAreLanguageIndependent(unittest.TestCase):
    def test_same_commemoration_ids_in_en_and_hy(self):
        en = compute_armenian_lectionary(GREAT_FRIDAY, language="en")
        hy = compute_armenian_lectionary(GREAT_FRIDAY, language="hy")
        self.assertNotEqual(en["Liturgical Day"], hy["Liturgical Day"])
        self.assertEqual(en["CommemorationIds"], hy["CommemorationIds"])


class TestCommemorationIdsMatchTheCatalog(unittest.TestCase):
    """The engine's filter and the catalog's own set must agree by construction, and the
    marking must reach the calendar: a mark on an id no date ever serves is a review
    decision with no effect, and a day that loses its commemoration is the regression this
    whole field exists to prevent."""

    # Days in 2001-2027 that serve no commemoration at all. Overwhelmingly the weekly
    # Wed/Fri fast (1,334 days) and the ordinal-day labels inside Nativity, Eastertide and
    # the named fasts -- days that genuinely commemorate nobody, and on which a consumer
    # is right to show nothing. A ratchet rather than an equality: marking more
    # observances lowers it, and a NEW blank day is a regression. Lower it when you mark
    # one, never raise it.
    MAX_DAYS_WITH_NO_COMMEMORATION = 5017
    _DEFAULT_RANGE = (2001, 2027)

    @classmethod
    def setUpClass(cls):
        if not engine._OBSERVANCE_CATALOG:
            raise unittest.SkipTest("observance catalog not present")
        cls.results = []
        d = datetime.date(engine.MIN_YEAR, 1, 1)
        end = datetime.date(engine.MAX_YEAR, 12, 31)
        one = datetime.timedelta(days=1)
        while d <= end:
            cls.results.append(compute_armenian_lectionary(d))
            d += one

    def test_every_served_commemoration_id_is_in_the_catalogs_set(self):
        marked = engine._OBSERVANCE_CATALOG.commemoration_ids
        for r in self.results:
            for sid in r["CommemorationIds"]:
                with self.subTest(date=r["Date"], sid=sid):
                    self.assertIn(sid, marked)

    def test_every_marked_id_is_served_at_least_once(self):
        """No exemption list, unlike ``FastIds``'s deprecated ``fast_day``: every id the
        review marks as a commemoration reaches a date in range."""
        seen = {sid for r in self.results for sid in r["CommemorationIds"]}
        never_seen = engine._OBSERVANCE_CATALOG.commemoration_ids - seen
        self.assertEqual(never_seen, set(),
                         f"commemoration id(s) marked but never served "
                         f"{engine.MIN_YEAR}-{engine.MAX_YEAR}: {sorted(never_seen)}")

    def test_days_with_no_commemoration_within_ratchet(self):
        if (engine.MIN_YEAR, engine.MAX_YEAR) != self._DEFAULT_RANGE:
            self.skipTest("the ratchet counts days, so it is stated for the default range")
        blank = [r for r in self.results if not r["CommemorationIds"]]
        self.assertLessEqual(
            len(blank), self.MAX_DAYS_WITH_NO_COMMEMORATION,
            f"{len(blank)} days serve no commemoration (ratchet "
            f"{self.MAX_DAYS_WITH_NO_COMMEMORATION}); a NEW blank day means an observance "
            f"lost its is_comm mark -- e.g. {blank[0]['Date']} "
            f"({blank[0]['Liturgical Day']!r})")

    def test_the_two_sets_genuinely_overlap_in_range(self):
        """Stated over the whole range, not just the pinned dates above: if the overlap
        ever empties, the catalog has been reduced to two disjoint kinds and the
        complement shortcut has quietly become correct -- which is the modelling error."""
        catalog = engine._OBSERVANCE_CATALOG
        self.assertTrue(catalog.fast_ids & catalog.commemoration_ids)
        self.assertTrue(set(catalog) - catalog.fast_ids - catalog.commemoration_ids)


if __name__ == "__main__":
    unittest.main()
