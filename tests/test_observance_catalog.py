"""The catalog's own interface, and the staleness it makes impossible.

``engine.py`` used to hold four globals for one catalog: the entries, two reverse indexes
derived from them, and a fourth recording which entries the indexes had been derived FROM
-- compared by identity on every lookup so the indexes could be rebuilt when a test
substituted a different catalog underneath them. A ``cache_clear()`` on an unrelated
``lru_cache`` hung off the same check, because that cache memoized a scan resolved through
the index.

All of it was machinery for a dependency that was created rather than accepted. These
tests assert the property that replaced it: a catalog indexes itself at construction, so
there is no window in which its indexes can disagree with it, and the cache the engine
keeps against a catalog belongs to that catalog.

Needs no ground-truth cache; runs in CI.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402
from armenian_lectionary.observance_catalog import ObservanceCatalog       # noqa: E402

ENTRIES = {
    "nativity_5": {"en": "Fifth day of Nativity", "hy": "Ե օր Ս. Ծննդեան"},
    "vahan": {"en": "St. Vahan of Goghtn", "hy": "Ս. Վահան Գողթնացի",
              "is_comm": True},
    "nativity_fast_3": {
        "en": "Third day of the Fast of Nativity", "hy": "Գ օր Ս. Ծննդեան պահոց",
        "is_fast": True,
    },
    # A fast AND a commemoration -- the quadrant that makes the two sets independent
    # rather than complements. See tests/test_commemoration_ids.py.
    "great_friday": {"en": "Great Friday", "hy": "Աւագ ուրբաթ",
                     "is_fast": True, "is_comm": True},
}


class TestTheInterface(unittest.TestCase):
    def setUp(self):
        self.catalog = ObservanceCatalog(ENTRIES)

    def test_id_of_reads_the_text_index(self):
        self.assertEqual(self.catalog.id_of("St. Vahan of Goghtn"), "vahan")

    def test_id_of_returns_none_for_unknown_text(self):
        """None, not a raise: this is the serving path, which must never fail on a name."""
        self.assertIsNone(self.catalog.id_of("(commemoration)"))

    def test_names_for_returns_both_languages(self):
        self.assertEqual(self.catalog.names_for("Fifth day of Nativity"),
                         ENTRIES["nativity_5"])
        self.assertIsNone(self.catalog.names_for("nothing"))

    def test_text_of_falls_back_to_the_literal(self):
        self.assertEqual(self.catalog.text_of("vahan", "fallback"), "St. Vahan of Goghtn")
        self.assertEqual(self.catalog.text_of("vahan", "fallback", "hy"),
                         "Ս. Վահան Գողթնացի")
        self.assertEqual(self.catalog.text_of("absent", "fallback"), "fallback")

    def test_an_empty_catalog_degrades_to_the_literal(self):
        """A thin checkout: absent catalog, English/literal text everywhere."""
        empty = ObservanceCatalog()
        self.assertFalse(empty)
        self.assertEqual(empty.text_of("vahan", "fallback"), "fallback")
        self.assertIsNone(empty.id_of("St. Vahan of Goghtn"))

    def test_load_of_a_missing_file_is_empty_not_an_error(self):
        self.assertEqual(len(ObservanceCatalog.load("/nonexistent/catalog.json")), 0)

    def test_reads_like_a_dict(self):
        """Dev tooling and several tests legitimately read entries by id."""
        self.assertIn("vahan", self.catalog)
        self.assertEqual(self.catalog["vahan"]["en"], "St. Vahan of Goghtn")
        self.assertEqual(self.catalog.get("absent"), None)
        self.assertEqual(dict(self.catalog.items()), ENTRIES)
        self.assertEqual(sorted(self.catalog),
                         ["great_friday", "nativity_5", "nativity_fast_3", "vahan"])


class TestTheIndexesCannotGoStale(unittest.TestCase):
    """The defect the four globals existed to paper over, now unreachable."""

    def test_a_new_catalog_indexes_itself(self):
        catalog = ObservanceCatalog(ENTRIES).replacing("vahan", en="RENAMED")
        self.assertEqual(catalog.id_of("RENAMED"), "vahan")
        self.assertIsNone(
            catalog.id_of("St. Vahan of Goghtn"),
            "the old text still resolves: the index outlived the entries it indexes")

    def test_replacing_does_not_mutate_the_original(self):
        original = ObservanceCatalog(ENTRIES)
        original.replacing("vahan", en="RENAMED")
        self.assertEqual(original.id_of("St. Vahan of Goghtn"), "vahan")
        self.assertIsNone(original.id_of("RENAMED"))

    def test_replacing_keeps_the_other_language(self):
        catalog = ObservanceCatalog(ENTRIES).replacing("vahan", en="RENAMED")
        self.assertEqual(catalog["vahan"]["hy"], "Ս. Վահան Գողթնացի")

    def test_replacing_an_unknown_id_raises(self):
        """A rename that silently invented an observance would be worse than a failure."""
        with self.assertRaises(KeyError):
            ObservanceCatalog(ENTRIES).replacing("no_such_id", en="X")


class TestFastIds(unittest.TestCase):
    """``fast_ids`` is the same "derived at construction, cannot go stale" pattern as
    the two text indexes -- see the module docstring."""

    def setUp(self):
        self.catalog = ObservanceCatalog(ENTRIES)

    def test_fast_ids_holds_only_the_marked_entries(self):
        self.assertEqual(self.catalog.fast_ids,
                         frozenset({"nativity_fast_3", "great_friday"}))

    def test_an_entry_with_no_is_fast_key_is_not_a_fast(self):
        """``vahan``/``nativity_5`` carry no ``is_fast`` key at all -- a thin/older
        catalog entry, not just a false one -- and must not be treated as a fast."""
        self.assertNotIn("vahan", self.catalog.fast_ids)
        self.assertNotIn("nativity_5", self.catalog.fast_ids)

    def test_an_empty_catalog_has_no_fast_ids(self):
        self.assertEqual(ObservanceCatalog().fast_ids, frozenset())

    def test_replacing_preserves_is_fast_by_default(self):
        renamed = self.catalog.replacing("nativity_fast_3", en="RENAMED")
        self.assertIn("nativity_fast_3", renamed.fast_ids)

    def test_replacing_can_override_is_fast(self):
        unmarked = self.catalog.replacing("nativity_fast_3", is_fast=False)
        self.assertNotIn("nativity_fast_3", unmarked.fast_ids)
        marked = self.catalog.replacing("vahan", is_fast=True)
        self.assertIn("vahan", marked.fast_ids)


class TestCommemorationIds(unittest.TestCase):
    """``commemoration_ids`` is built the same way as ``fast_ids``, and is INDEPENDENT of
    it: neither set is the other's complement, so neither may be derived from the other.
    ``great_friday`` is in both, ``nativity_5`` in neither."""

    def setUp(self):
        self.catalog = ObservanceCatalog(ENTRIES)

    def test_commemoration_ids_holds_only_the_marked_entries(self):
        self.assertEqual(self.catalog.commemoration_ids,
                         frozenset({"vahan", "great_friday"}))

    def test_an_entry_with_no_is_comm_key_is_not_a_commemoration(self):
        """A thin or older catalog entry carries no ``is_comm`` key at all, and must not
        be read as a commemoration on the strength of its shape."""
        self.assertNotIn("nativity_5", self.catalog.commemoration_ids)
        self.assertNotIn("nativity_fast_3", self.catalog.commemoration_ids)

    def test_an_empty_catalog_has_no_commemoration_ids(self):
        self.assertEqual(ObservanceCatalog().commemoration_ids, frozenset())

    def test_the_two_sets_are_independent(self):
        self.assertEqual(self.catalog.fast_ids & self.catalog.commemoration_ids,
                         frozenset({"great_friday"}))
        self.assertNotIn("nativity_5", self.catalog.fast_ids)
        self.assertNotIn("nativity_5", self.catalog.commemoration_ids)

    def test_replacing_preserves_is_comm_by_default(self):
        renamed = self.catalog.replacing("vahan", en="RENAMED")
        self.assertIn("vahan", renamed.commemoration_ids)

    def test_replacing_can_override_is_comm(self):
        unmarked = self.catalog.replacing("vahan", is_comm=False)
        self.assertNotIn("vahan", unmarked.commemoration_ids)
        marked = self.catalog.replacing("nativity_5", is_comm=True)
        self.assertIn("nativity_5", marked.commemoration_ids)

    def test_overriding_one_flag_leaves_the_other(self):
        """``replacing`` merges fields, so unmarking a fast must not unmark the
        commemoration riding on the same entry."""
        no_fast = self.catalog.replacing("great_friday", is_fast=False)
        self.assertNotIn("great_friday", no_fast.fast_ids)
        self.assertIn("great_friday", no_fast.commemoration_ids)


class TestTheOwnDayCacheBelongsToTheCatalog(unittest.TestCase):
    """``_canons_with_own_day`` memoizes a liturgical year's laydown, resolved THROUGH the
    catalog. It was an ``lru_cache`` on the function, which meant a substituted catalog
    could be answered from the previous one's scan unless something remembered to clear
    it -- so the index accessor called ``cache_clear()``. Holding the cache on the
    instance makes that true by construction.
    """

    PACKED_DAY = datetime.date(2026, 1, 19)          # two pool canons on one line

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")
        self._orig = engine._OBSERVANCE_CATALOG
        self.addCleanup(setattr, engine, "_OBSERVANCE_CATALOG", self._orig)

    def test_the_scan_is_cached_on_the_catalog(self):
        self._orig.own_day_cache.clear()
        engine.compute_armenian_lectionary(self.PACKED_DAY)
        self.assertEqual(
            list(self._orig.own_day_cache), [engine._liturgical_year(self.PACKED_DAY)],
            "the packed day's liturgical year should be scanned once and kept")

    def test_a_substituted_catalog_starts_with_an_empty_cache(self):
        engine.compute_armenian_lectionary(self.PACKED_DAY)      # warm the original
        self.assertTrue(self._orig.own_day_cache)
        engine._OBSERVANCE_CATALOG = self._orig.replacing(
            next(iter(self._orig)), en="IRRELEVANT RENAME")
        self.assertEqual(
            engine._OBSERVANCE_CATALOG.own_day_cache, {},
            "a different catalog inherited the previous catalog's scan")

    def test_the_original_cache_survives_the_swap(self):
        """Restoring the catalog restores its cache too -- nothing was invalidated."""
        engine.compute_armenian_lectionary(self.PACKED_DAY)
        warmed = dict(self._orig.own_day_cache)
        engine._OBSERVANCE_CATALOG = ObservanceCatalog(ENTRIES)
        engine._OBSERVANCE_CATALOG = self._orig
        self.assertEqual(self._orig.own_day_cache, warmed)


if __name__ == "__main__":
    unittest.main()
