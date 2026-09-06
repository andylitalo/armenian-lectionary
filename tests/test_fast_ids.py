"""Unit tests for the ``FastIds`` field (engine.py's ``_fast_ids``).

``FastIds`` is a filter over the already-resolved ``ObservanceIds`` field (see
``tests/test_observance_ids.py``), not a second text resolution, so it inherits that
field's all-or-nothing, fully-covered-in-range guarantee for free -- these tests only
check the filter itself: which ids the catalog marks as fasts, and that the marking is
independent of ``language``. Self-contained: no ground-truth cache needed.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402
from armenian_lectionary import compute_armenian_lectionary                # noqa: E402

NATIVITY_FAST_DAY = datetime.date(2026, 12, 30)   # "First day of the Fast of Nativity"
PLAIN_FEAST_DAY = datetime.date(2026, 5, 3)       # "Appearance of the Holy Cross"


class TestFastIdsShape(unittest.TestCase):
    def test_a_fast_day_carries_its_own_fast_id(self):
        result = compute_armenian_lectionary(NATIVITY_FAST_DAY)
        self.assertEqual(result["FastIds"], ["nativity_fast_day_1"])

    def test_a_plain_feast_day_has_no_fast_ids(self):
        result = compute_armenian_lectionary(PLAIN_FEAST_DAY)
        self.assertEqual(result["FastIds"], [])

    def test_fast_ids_is_a_subset_of_observance_ids_in_order(self):
        result = compute_armenian_lectionary(NATIVITY_FAST_DAY)
        self.assertEqual(result["FastIds"],
                          [sid for sid in result["ObservanceIds"] if sid in result["FastIds"]])
        for sid in result["FastIds"]:
            self.assertIn(sid, result["ObservanceIds"])

    def test_fast_ids_filters_out_non_fast_and_unknown_ids(self):
        self.assertEqual(engine._fast_ids([]), [])
        self.assertEqual(
            engine._fast_ids(["appearance_of_the_holy_cross", "not_a_real_id"]), [])
        self.assertEqual(
            engine._fast_ids(["appearance_of_the_holy_cross", "nativity_fast_day_1"]),
            ["nativity_fast_day_1"])


class TestFastIdsAreLanguageIndependent(unittest.TestCase):
    def test_same_fast_ids_in_en_and_hy(self):
        en = compute_armenian_lectionary(NATIVITY_FAST_DAY, language="en")
        hy = compute_armenian_lectionary(NATIVITY_FAST_DAY, language="hy")
        self.assertNotEqual(en["Liturgical Day"], hy["Liturgical Day"])
        self.assertEqual(en["FastIds"], hy["FastIds"])


class TestFastIdsMatchTheCatalog(unittest.TestCase):
    """The engine's filter and the catalog's own set must agree by construction --
    a regression here would mean the two drifted apart, not that a date resolved
    incorrectly (that's ``ObservanceIds``'s contract, already covered elsewhere)."""

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

    def test_every_served_fast_id_is_in_the_catalogs_fast_ids(self):
        fast_ids = engine._OBSERVANCE_CATALOG.fast_ids
        for r in self.results:
            for sid in r["FastIds"]:
                with self.subTest(date=r["Date"], sid=sid):
                    self.assertIn(sid, fast_ids)

    # "fast_day" is the bare, generic marker the SOURCE prints ~2,100 times in 2001-2026.
    # It is DEPRECATED and never served: it sits in `engine._BARE_FAST_MARKERS` and
    # `_POSITION_OVERLAY_DROPS`, so `_apply_position_label` returns before it can reach the
    # name, and it therefore never enters `ObservanceIds` or `FastIds` no matter how the
    # row is marked.
    #
    # On most of those days that is harmless -- a more specific label claims the day (the
    # Wed/Fri split, or a named fast's own day count) and carries the fast id itself. On
    # FOUR it is not: Dec 9 in 2005, 2011, 2016 and 2022, each a Friday falling outside the
    # Nisibis fast window, serve "Feast of the Conception of the Holy Virgin Mary by Anna"
    # with `FastIds == []` while the engine's own tables call the day a fast. The fix is to
    # serve `friday_fast` there rather than dropping the marker, retiring `fast_day`
    # properly; this exemption records the hole until then, so it cannot widen unnoticed.
    _SHADOWED_IN_RANGE = {"fast_day"}

    def test_every_other_catalog_fast_id_is_observed_at_least_once(self):
        seen = {sid for r in self.results for sid in r["FastIds"]}
        expected = engine._OBSERVANCE_CATALOG.fast_ids - self._SHADOWED_IN_RANGE
        never_seen = expected - seen
        self.assertEqual(never_seen, set(),
                          f"fast id(s) marked but never served {engine.MIN_YEAR}-"
                          f"{engine.MAX_YEAR}: {sorted(never_seen)}")

    def test_fast_day_itself_is_shadowed_by_a_more_specific_label_in_range(self):
        """Documents the one exception above. When the Dec-9 hole is closed by serving
        `friday_fast` there, `fast_day` should be retired outright rather than made
        reachable -- either way this starts failing, so the exemption gets revisited
        instead of silently going stale."""
        seen = {sid for r in self.results for sid in r["FastIds"]}
        self.assertNotIn("fast_day", seen)

    def test_at_least_one_day_carries_a_fast_id(self):
        self.assertTrue(any(r["FastIds"] for r in self.results))


if __name__ == "__main__":
    unittest.main()
