"""Unit tests for the ``ObservanceIds`` field (engine.py's ``_observance_ids``).

Purely about the field's own contract -- shape, round-trip, language-independence, and
corpus-wide completeness. Rename-reachability for the ids themselves (does a TSV edit
survive to what's served) is already covered end to end by
``tests/test_rename_reaches_the_served_name.py`` and, at the build layer, by
``tests/test_build_registration.py``; nothing here re-tests that. Self-contained: no
ground-truth cache needed, since it only checks internal consistency of what the engine
serves against its own shipped catalog.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402
from armenian_lectionary import compute_armenian_lectionary                # noqa: E402
from armenian_lectionary.observance_name import ObservanceName             # noqa: E402


class TestObservanceIdsShape(unittest.TestCase):
    def test_multi_observance_day_names_each_component_in_order(self):
        # PR's own worked example: a position label, a commemoration, and an eve note.
        result = compute_armenian_lectionary(datetime.date(2004, 11, 21))
        self.assertEqual(
            result["ObservanceIds"],
            ["eleventh_sunday_of_the_holy_cross", "presentation_of_the_holy_mother",
             "eve_of_fast_of_advent"])

    def test_ids_round_trip_to_their_source_text(self):
        result = compute_armenian_lectionary(datetime.date(2004, 11, 21))
        parts = list(ObservanceName.parse(result["Liturgical Day"]))
        self.assertEqual(len(parts), len(result["ObservanceIds"]))
        for part, sid in zip(parts, result["ObservanceIds"]):
            self.assertEqual(engine._OBSERVANCE_CATALOG.text_of(sid, None), part)

    def test_single_observance_day_yields_one_id(self):
        result = compute_armenian_lectionary(datetime.date(2026, 4, 5))  # Easter
        self.assertEqual(len(result["ObservanceIds"]), 1)

    def test_unresolvable_component_yields_empty_list_not_a_partial_one(self):
        # A day whose label the substituted catalog cannot identify at all: all-or-nothing,
        # not "everything except the one component we couldn't place."
        self.assertEqual(engine._observance_ids("Not A Real Observance"), [])

    def test_empty_label_yields_empty_list(self):
        self.assertEqual(engine._observance_ids(""), [])


class TestObservanceIdsAreLanguageIndependent(unittest.TestCase):
    DATE = datetime.date(2004, 11, 21)  # multi-observance, exercises every component kind

    def test_same_ids_in_en_and_hy(self):
        en = compute_armenian_lectionary(self.DATE, language="en")
        hy = compute_armenian_lectionary(self.DATE, language="hy")
        # Guard against vacuous equality: the Armenian text must actually differ, or this
        # would pass even if ObservanceIds were wrongly resolved post-localization.
        self.assertNotEqual(en["Liturgical Day"], hy["Liturgical Day"])
        self.assertEqual(en["ObservanceIds"], hy["ObservanceIds"])


class TestObservanceIdsOverTheCorpus(unittest.TestCase):
    """Every day MIN_YEAR-MAX_YEAR resolves completely and round-trips -- the corpus-wide
    version of TestObservanceIdsShape's single-date checks."""

    @classmethod
    def setUpClass(cls):
        cls.results = []
        d = datetime.date(engine.MIN_YEAR, 1, 1)
        end = datetime.date(engine.MAX_YEAR, 12, 31)
        one = datetime.timedelta(days=1)
        while d <= end:
            cls.results.append(compute_armenian_lectionary(d))
            d += one

    def test_no_day_resolves_to_an_empty_list(self):
        empty = [r["Date"] for r in self.results if not r["ObservanceIds"]]
        self.assertEqual(empty, [], f"{len(empty)} day(s) with unresolved ObservanceIds")

    def test_every_day_round_trips_through_the_catalog(self):
        for r in self.results:
            parts = list(ObservanceName.parse(r["Liturgical Day"]))
            with self.subTest(date=r["Date"]):
                self.assertEqual(len(parts), len(r["ObservanceIds"]))
                for part, sid in zip(parts, r["ObservanceIds"]):
                    self.assertEqual(engine._OBSERVANCE_CATALOG.text_of(sid, None), part)

    def test_id_tuples_distinguish_at_least_as_many_days_as_names_do(self):
        names = {r["Liturgical Day"] for r in self.results}
        id_tuples = {tuple(r["ObservanceIds"]) for r in self.results}
        self.assertGreaterEqual(len(id_tuples), len(names))

    def test_over_a_thousand_days_carry_more_than_one_observance(self):
        multi = sum(1 for r in self.results if len(r["ObservanceIds"]) > 1)
        self.assertGreater(multi, 1000)

    def test_the_ten_labels_pr46_reindexed_all_resolve(self):
        """The two weekly fasts, six "Nth Sunday after Nativity", and "Second Sunday after
        Pentecost" had no readings/coordinate index entry before PR #46 declared their ids
        directly -- a regression to text-only resolution would silently return [] for
        every one of these again."""
        targets = {
            "Wednesday Fast", "Friday Fast", "Second Sunday after Pentecost",
            "First Sunday after Nativity", "Second Sunday after Nativity",
            "Third Sunday after Nativity", "Fourth Sunday after Nativity",
            "Fifth Sunday after Nativity", "Sixth Sunday after Nativity",
            "Seventh Sunday after Nativity",
        }
        seen = set()
        for r in self.results:
            parts = list(ObservanceName.parse(r["Liturgical Day"]))
            for part, sid in zip(parts, r["ObservanceIds"]):
                if part in targets:
                    seen.add(part)
                    self.assertTrue(sid, f"{part} on {r['Date']} resolved to no id")
        self.assertEqual(seen, targets, f"never observed in range: {targets - seen}")

    def test_every_eve_note_resolves_via_observance_ids(self):
        """Rename-reachability for eves is already swept by
        tests/test_rename_reaches_the_served_name.py; this only checks that
        ObservanceIds actually carries the id for each -- a distinct question, since the
        field could in principle resolve the wrong component or drop the eve slot."""
        for r in self.results:
            eve = engine._eve_label(datetime.date.fromisoformat(r["Date"]))
            if eve is None:
                continue
            name = ObservanceName.parse(r["Liturgical Day"])
            stored = name.find(engine._is_eve_component)
            if stored is None:
                continue
            sid = engine._OBSERVANCE_CATALOG.id_of(stored)
            with self.subTest(date=r["Date"]):
                self.assertIn(sid, r["ObservanceIds"])


if __name__ == "__main__":
    unittest.main()
