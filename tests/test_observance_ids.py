"""Tests for ``ObservanceIds`` and the id-stability contract behind it.

The ids exist so a consumer can key stored data on something the display text is not:
stable. bahk keys ``Feast`` rows on the name today, and 1.3.0's corrections -- ``Saint(s)``
folded to ``St(s).``, 122 spellings fixed -- made every one of those rows unreachable, with
its curated icon and generated contexts stranded behind it. An id that moved when its text
was corrected would reproduce that exactly, only harder to see, so the contract is worth
more than the field: **a published id keeps meaning the same observance forever.**

Self-contained: no ground-truth cache needed.
"""
import datetime
import importlib.util
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import (                                        # noqa: E402
    MAX_YEAR, MIN_YEAR, compute_armenian_lectionary,
)
from armenian_lectionary import engine                                   # noqa: E402


def _every_day():
    day = datetime.date(MIN_YEAR, 1, 1)
    end = datetime.date(MAX_YEAR, 12, 31)
    while day <= end:
        yield day
        day += datetime.timedelta(days=1)


class TestObservanceIdsShape(unittest.TestCase):
    """What a single result carries."""

    def test_ids_name_the_components_in_order(self):
        """A multi-observance day: position label, commemoration, eve note."""
        result = compute_armenian_lectionary(datetime.date(2004, 11, 21))
        self.assertEqual(
            result["ObservanceIds"],
            ["eleventh_sunday_after_the", "presentation_of_the_holy", "eve_of_fast_of"])

    def test_each_id_resolves_back_to_the_component_it_came_from(self):
        result = compute_armenian_lectionary(datetime.date(2004, 11, 21))
        served = [engine._OBSERVANCE_CATALOG[sid]["en"]
                  for sid in result["ObservanceIds"]]
        self.assertEqual(served, result["Liturgical Day"].split(engine._FEAST_SEP))

    def test_a_single_observance_day_is_a_one_element_list(self):
        result = compute_armenian_lectionary(datetime.date(2001, 1, 16))
        self.assertEqual(result["ObservanceIds"], ["peter_the_patriarch_blaise"])

    def test_an_unresolvable_component_yields_no_ids_rather_than_a_hole(self):
        """A partial list is not a key -- it would identify a different observance."""
        self.assertEqual(
            engine._observance_ids(
                "Sts. Peter the Patriarch, Blaise the Bishop and Absalom the Deacon"
                + engine._FEAST_SEP + "(commemoration)"),
            [])

    def test_no_label_yields_no_ids(self):
        self.assertEqual(engine._observance_ids(""), [])
        self.assertEqual(engine._observance_ids(None), [])


class TestObservanceIdsAreLanguageIndependent(unittest.TestCase):
    """The whole point: the id does not move when the words do."""

    def test_the_same_date_gives_the_same_ids_in_both_languages(self):
        for day in (datetime.date(2001, 1, 16), datetime.date(2004, 11, 21),
                    datetime.date(2026, 4, 5)):
            with self.subTest(day=day):
                self.assertEqual(
                    compute_armenian_lectionary(day, language="en")["ObservanceIds"],
                    compute_armenian_lectionary(day, language="hy")["ObservanceIds"])

    def test_the_armenian_text_differs_where_the_ids_do_not(self):
        """Guards the test above from passing because nothing was translated."""
        day = datetime.date(2001, 1, 16)
        self.assertNotEqual(
            compute_armenian_lectionary(day, language="en")["Liturgical Day"],
            compute_armenian_lectionary(day, language="hy")["Liturgical Day"])


class TestObservanceIdsOverTheCorpus(unittest.TestCase):
    """Swept over every day the engine serves, so coverage is not a sample."""

    @classmethod
    def setUpClass(cls):
        cls.results = {day: compute_armenian_lectionary(day) for day in _every_day()}

    def test_every_day_in_range_resolves_completely(self):
        """An empty list anywhere means a component the catalog does not cover."""
        empty = [day for day, r in self.results.items() if not r["ObservanceIds"]]
        self.assertEqual(empty, [], f"{len(empty)} day(s) resolve to no ids")

    def test_every_day_round_trips_through_the_catalog(self):
        for day, result in self.results.items():
            served = [engine._OBSERVANCE_CATALOG[sid]["en"]
                      for sid in result["ObservanceIds"]]
            if served != result["Liturgical Day"].split(engine._FEAST_SEP):
                self.fail(f"{day}: {served} != {result['Liturgical Day']!r}")

    def test_the_id_list_identifies_a_day_as_precisely_as_its_name(self):
        """A key that lumped distinct days together would silently merge their data."""
        by_name, by_ids = set(), set()
        for result in self.results.values():
            by_name.add(result["Liturgical Day"])
            by_ids.add(tuple(result["ObservanceIds"]))
        self.assertGreaterEqual(len(by_ids), len(by_name))

    def test_days_naming_several_observances_are_a_real_population(self):
        """If this collapsed to zero the ordered-list contract would be untested."""
        multi = sum(1 for r in self.results.values() if len(r["ObservanceIds"]) > 1)
        self.assertGreater(multi, 1000)


class TestPublishedIdsAreFrozen(unittest.TestCase):
    """The contract: an id, once shipped, never moves.

    Enforced at build time rather than here -- these tests check that the enforcement
    works, by driving the builder the way a future correction would.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "dev", "build_observance_catalog.py")
        spec = importlib.util.spec_from_file_location("build_observance_catalog", path)
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)
        cls.ground_truth = cls.builder.load_ground_truth()
        with open(cls.builder.CATALOG_PATH, encoding="utf-8") as fh:
            cls.shipped = json.load(fh)

    def test_rebuilding_reproduces_the_shipped_catalog_exactly(self):
        """Ids are stated in the TSV, not derived: a rebuild must not add, drop or edit
        anything the catalog already ships."""
        catalog, problems = self.builder.build_catalog(self.ground_truth)
        self.assertEqual(problems, [])
        self.assertEqual(catalog, self.shipped)

    def test_a_new_id_can_never_take_a_published_one(self):
        """Reusing a retired id would silently redirect a consumer to another observance."""
        approved_ids = {row["approved_en"]: row.get("id")
                        for row in self.ground_truth.values() if row.get("approved_en")}
        published = {sid for sid in approved_ids.values() if sid}
        minted = self.builder._slug(self.shipped["peter_the_patriarch_blaise"]["en"],
                                    set(published))
        self.assertNotIn(minted, published)

    def test_every_shipped_id_is_one_the_engine_serves(self):
        """An id nothing emits is an id a consumer can never match.

        Every catalog entry now names exactly one canon of the Tonats'oyts, so nothing
        should be left over -- unlike the old text-swept catalog, which minted ids for
        approved strings the current table never produces.
        """
        emitted = set()
        for day in _every_day():
            emitted.update(compute_armenian_lectionary(day)["ObservanceIds"])
        self.assertEqual(set(self.shipped) - emitted, set())


if __name__ == "__main__":
    unittest.main()
