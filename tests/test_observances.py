"""Unit tests for the ``Observances`` field (engine.py's ``_observances``).

``Observances`` is ``Liturgical Day`` as the ordered list the engine already holds
internally, one dict per component: its stable id, its served name, and the per-observance
marks the human review states (``is_fast``, ``is_comm``). It replaced the parallel
``FastIds``/``CommemorationIds`` arrays, which were this same table stored transposed.

Three things these tests exist to hold, in descending order of what a regression would
cost:

  * **the attributes are independent.** Neither mark is the other's negation -- both are
    true on a named Lenten Sunday, both false on an ordinal-day label -- so neither may
    ever be computed from the other. One date is pinned per quadrant, plus the set
    relations.
  * **the names still join back to ``Liturgical Day``**, in both languages. That is what
    lets a consumer stop splitting the display string.
  * **the ids agree with ``ObservanceIds``** on every date, since that field is now a
    projection of this one and the 2.0.0 contract rests on it.

Self-contained: no ground-truth cache needed.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402
from armenian_lectionary import compute_armenian_lectionary                # noqa: E402
from armenian_lectionary.engine import _OBSERVANCE_SEP                     # noqa: E402

# One date per quadrant of (is_fast x is_comm), which is the whole argument for two marks.
GREAT_FRIDAY = datetime.date(2026, 4, 3)          # a fast beside a commemoration
LENTEN_SUNDAY = datetime.date(2026, 3, 1)         # both marks, on one id
WEEKLY_FAST_DAY = datetime.date(2026, 1, 14)      # "Wednesday Fast" -- fast, not a comm
PLAIN_POSITION_DAY = datetime.date(2026, 1, 8)    # "Third day of Nativity" -- neither
# "Fifth Sunday of Eastertide - Appearance of the Holy Cross": a bare position label
# beside a commemoration. The day the whole design argument is made on.
POSITION_PLUS_COMMEMORATION = datetime.date(2026, 5, 3)
EVE_ONLY_DAY = datetime.date(2026, 1, 5)          # Eve of the Nativity is the ONLY component

ATTRIBUTES = ("is_fast", "is_comm")


class TestObservanceEntryShape(unittest.TestCase):
    def test_an_entry_carries_the_id_the_name_and_every_attribute(self):
        [entry] = compute_armenian_lectionary(EVE_ONLY_DAY)["Observances"]
        self.assertEqual(entry, {
            "id": "eve_of_the_nativity",
            "name": "Eve of the Nativity and Theophany of Our Lord Jesus Christ",
            "is_fast": False,
            "is_comm": True,
        })

    def test_the_only_component_may_be_an_eve(self):
        """Jan 5 serves the eve and nothing else, so leaving eves unmarked would give the
        Nativity vigil no commemoration at all. The same holds for Poon Barekendan
        (`eve_of_great_lent`). This is what makes the eve marking more than a preference."""
        result = compute_armenian_lectionary(EVE_ONLY_DAY)
        self.assertEqual([o["id"] for o in result["Observances"]], ["eve_of_the_nativity"])
        self.assertTrue(result["Observances"][0]["is_comm"])

    def test_entries_are_in_served_order(self):
        result = compute_armenian_lectionary(POSITION_PLUS_COMMEMORATION)
        self.assertEqual([o["id"] for o in result["Observances"]],
                         ["fifth_sunday_of_eastertide", "appearance_of_the_holy_cross"])

    def test_every_attribute_is_a_bool_not_a_missing_key(self):
        """The API promises a boolean. The catalog's degrade-to-empty convention means an
        entry may carry no such key at all, and that must not leak ``None`` into a
        response."""
        for o in compute_armenian_lectionary(GREAT_FRIDAY)["Observances"]:
            for attribute in ATTRIBUTES:
                with self.subTest(sid=o["id"], attribute=attribute):
                    self.assertIsInstance(o[attribute], bool)

    def test_observance_ids_is_the_id_projection(self):
        result = compute_armenian_lectionary(GREAT_FRIDAY)
        self.assertEqual(result["ObservanceIds"],
                         [o["id"] for o in result["Observances"]])

    def test_resolution_is_all_or_nothing(self):
        self.assertEqual(engine._observances("Not A Real Observance"), [])
        self.assertEqual(engine._observances(""), [])
        self.assertEqual(
            engine._observances(f"Great Friday{_OBSERVANCE_SEP}Not A Real Observance"), [])
        self.assertEqual(engine._ids_of([]), [])

    def test_a_resolvable_component_beside_an_unresolvable_one_yields_nothing(self):
        """The half that resolved is not served on its own: a partial list would identify
        a different day than the one actually served. Same rule ``ObservanceIds`` has had
        since 2.0.0, and the reason ``[]`` has exactly one meaning."""
        self.assertEqual(
            engine._observance_ids(f"Great Friday{_OBSERVANCE_SEP}Not A Real Observance"),
            [])


class TestTheNamesJoinBackToTheServedDay(unittest.TestCase):
    """What lets a consumer stop splitting ``Liturgical Day`` on the separator."""

    def test_joining_the_names_reproduces_the_served_name_in_english(self):
        result = compute_armenian_lectionary(GREAT_FRIDAY)
        self.assertEqual(_OBSERVANCE_SEP.join(o["name"] for o in result["Observances"]),
                         result["Liturgical Day"])

    def test_joining_the_names_reproduces_the_served_name_in_armenian(self):
        result = compute_armenian_lectionary(GREAT_FRIDAY, language="hy")
        self.assertEqual(_OBSERVANCE_SEP.join(o["name"] for o in result["Observances"]),
                         result["Liturgical Day"])


class TestAttributesAreIndependent(unittest.TestCase):
    """``is_comm`` is not ``not is_fast``. All four combinations occur, and if a later
    change derives either mark from the other, one of these fails."""

    def _only(self, date):
        result = compute_armenian_lectionary(date)
        self.assertEqual(len(result["Observances"]), 1, result["Liturgical Day"])
        return result["Observances"][0]

    def test_an_observance_can_be_both(self):
        """"Third Sunday of Great Lent: Sunday of the Prodigal Son" is one component that
        is at once a day of the Great Fast and the commemoration the Sunday is named for.
        Holy Week's `great_*` ids are NOT the example: they are fasts only -- see
        TestHolyWeekIsFastOnly below."""
        o = self._only(LENTEN_SUNDAY)
        self.assertEqual((o["id"], o["is_fast"], o["is_comm"]),
                         ("third_sunday_of_great_lent", True, True))

    def test_an_observance_can_be_a_fast_only(self):
        o = self._only(WEEKLY_FAST_DAY)
        self.assertEqual((o["id"], o["is_fast"], o["is_comm"]),
                         ("wednesday_fast", True, False))

    def test_an_observance_can_be_a_commemoration_only(self):
        o = compute_armenian_lectionary(POSITION_PLUS_COMMEMORATION)["Observances"][1]
        self.assertEqual((o["id"], o["is_fast"], o["is_comm"]),
                         ("appearance_of_the_holy_cross", False, True))

    def test_an_observance_can_be_neither(self):
        o = self._only(PLAIN_POSITION_DAY)
        self.assertEqual((o["id"], o["is_fast"], o["is_comm"]),
                         ("third_day_of_nativity", False, False))

    def test_a_day_can_mix_a_bare_position_label_with_a_commemoration(self):
        """The case the two id arrays could not express without a join, and the reason a
        consumer must not read "not a fast" as "a commemoration"."""
        observances = compute_armenian_lectionary(
            POSITION_PLUS_COMMEMORATION)["Observances"]
        self.assertEqual([(o["is_fast"], o["is_comm"]) for o in observances],
                         [(False, False), (False, True)])


class TestHolyWeekIsFastOnly(unittest.TestCase):
    """`great_monday` .. `great_saturday` are marked `is_fast` and NOT `is_comm`.

    A Holy Week day-name locates the day inside the Great Week; what the day commemorates
    is stated by its own component beside it, and those are marked. Four of the six carry
    one -- the Ten Virgins (Tuesday), the Last Supper (Thursday), the Passion (Friday),
    the Eve of the Resurrection (Saturday).

    Great Monday and Great Wednesday carry none, and that is the deliberate consequence:
    across 2001-2027 they serve their day-name alone on 27 of 27 and 26 of 27 occurrences
    (the exception is 2004-04-07, when the Annunciation, a fixed civil date, lands on
    Great Wednesday). The corpus names no commemoration for them, so the engine states
    none rather than inventing one -- these two days are 53 of the ratchet above.
    """

    HOLY_WEEK = ("great_monday", "great_tuesday", "great_wednesday",
                 "great_thursday", "great_friday", "great_saturday")

    def test_the_day_names_are_fasts_and_not_commemorations(self):
        catalog = engine._OBSERVANCE_CATALOG
        for sid in self.HOLY_WEEK:
            with self.subTest(sid=sid):
                self.assertIn(sid, catalog.fast_ids)
                self.assertNotIn(sid, catalog.commemoration_ids)

    def test_great_friday_commemorates_through_its_own_component(self):
        observances = compute_armenian_lectionary(GREAT_FRIDAY)["Observances"]
        self.assertEqual([(o["id"], o["is_fast"], o["is_comm"]) for o in observances],
                         [("great_friday", True, False),
                          ("passion_crucifixion_burial", False, True)])

    def test_great_monday_deliberately_commemorates_nothing(self):
        result = compute_armenian_lectionary(datetime.date(2026, 3, 30))
        self.assertEqual([o["id"] for o in result["Observances"]], ["great_monday"])
        self.assertEqual([o["id"] for o in result["Observances"] if o["is_comm"]], [])


class TestLanguageIndependence(unittest.TestCase):
    def test_only_the_name_varies_by_language(self):
        en = compute_armenian_lectionary(GREAT_FRIDAY, language="en")["Observances"]
        hy = compute_armenian_lectionary(GREAT_FRIDAY, language="hy")["Observances"]
        self.assertNotEqual([o["name"] for o in en], [o["name"] for o in hy])
        for a, b in zip(en, hy):
            self.assertEqual({k: v for k, v in a.items() if k != "name"},
                             {k: v for k, v in b.items() if k != "name"})

    def test_ids_do_not_vary_by_language(self):
        en = compute_armenian_lectionary(GREAT_FRIDAY, language="en")
        hy = compute_armenian_lectionary(GREAT_FRIDAY, language="hy")
        self.assertNotEqual(en["Liturgical Day"], hy["Liturgical Day"])
        self.assertEqual(en["ObservanceIds"], hy["ObservanceIds"])


class TestObservancesOverTheCorpus(unittest.TestCase):
    """The sweep: every date in range, against the catalog the entries are built from."""

    # Days in 2001-2027 that serve no commemoration at all. Overwhelmingly the weekly
    # Wed/Fri fast (1,334 days) and the ordinal-day labels inside Nativity, Eastertide and
    # the named fasts -- days that genuinely commemorate nobody, and on which a consumer is
    # right to show nothing. A ratchet rather than an equality: marking more observances
    # lowers it, and a NEW blank day is a regression. Lower it when you mark one, never
    # raise it.
    MAX_DAYS_WITH_NO_COMMEMORATION = 5070
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

    def _marked(self, attribute):
        return {o["id"] for r in self.results for o in r["Observances"] if o[attribute]}

    def test_every_day_resolves(self):
        empty = [r["Date"] for r in self.results if not r["Observances"]]
        self.assertEqual(empty[:5], [],
                         f"{len(empty)} day(s) served no resolvable observance")

    def test_observance_ids_is_the_projection_on_every_date(self):
        for r in self.results:
            with self.subTest(date=r["Date"]):
                self.assertEqual(r["ObservanceIds"], [o["id"] for o in r["Observances"]])

    def test_the_names_join_back_to_the_served_day_on_every_date(self):
        for r in self.results:
            with self.subTest(date=r["Date"]):
                self.assertEqual(
                    _OBSERVANCE_SEP.join(o["name"] for o in r["Observances"]),
                    r["Liturgical Day"])

    def test_every_served_attribute_matches_the_catalog(self):
        catalog = engine._OBSERVANCE_CATALOG
        for r in self.results:
            for o in r["Observances"]:
                with self.subTest(date=r["Date"], sid=o["id"]):
                    self.assertEqual(o["is_fast"], o["id"] in catalog.fast_ids)
                    self.assertEqual(o["is_comm"], o["id"] in catalog.commemoration_ids)

    # "fast_day" is the bare, generic marker the SOURCE prints ~2,100 times in 2001-2026.
    # It is DEPRECATED and never served: it sits in `engine._BARE_FAST_MARKERS` and
    # `_POSITION_OVERLAY_DROPS`, so `_apply_position_label` returns before it can reach the
    # name, and it therefore never enters `Observances` no matter how the row is marked.
    #
    # On most of those days that is harmless -- a more specific label claims the day (the
    # Wed/Fri split, or a named fast's own day count) and carries the fast mark itself. On
    # FOUR it is not: Dec 9 in 2005, 2011, 2016 and 2022, each a Friday falling outside the
    # Nisibis fast window, serve "Feast of the Conception of the Holy Virgin Mary by Anna"
    # with no `is_fast` component while the engine's own tables call the day a fast. The
    # fix is to serve `friday_fast` there rather than dropping the marker, retiring
    # `fast_day` properly; this exemption records the hole until then, so it cannot widen
    # unnoticed.
    _SHADOWED_IN_RANGE = {"fast_day"}

    def test_every_marked_fast_id_is_served_except_the_shadowed_one(self):
        expected = engine._OBSERVANCE_CATALOG.fast_ids - self._SHADOWED_IN_RANGE
        never_seen = expected - self._marked("is_fast")
        self.assertEqual(never_seen, set(),
                         f"fast id(s) marked but never served {engine.MIN_YEAR}-"
                         f"{engine.MAX_YEAR}: {sorted(never_seen)}")

    def test_fast_day_itself_is_shadowed_by_a_more_specific_label_in_range(self):
        """Documents the one exception above. When the Dec-9 hole is closed by serving
        `friday_fast` there, `fast_day` should be retired outright rather than made
        reachable -- either way this starts failing, so the exemption gets revisited
        instead of silently going stale."""
        self.assertNotIn("fast_day", self._marked("is_fast"))

    def test_every_marked_commemoration_id_is_served(self):
        """No exemption list, unlike ``is_fast``'s deprecated ``fast_day``: every id the
        review marks as a commemoration reaches a date in range."""
        never_seen = engine._OBSERVANCE_CATALOG.commemoration_ids - self._marked("is_comm")
        self.assertEqual(never_seen, set(),
                         f"commemoration id(s) marked but never served "
                         f"{engine.MIN_YEAR}-{engine.MAX_YEAR}: {sorted(never_seen)}")

    def test_days_with_no_commemoration_within_ratchet(self):
        if (engine.MIN_YEAR, engine.MAX_YEAR) != self._DEFAULT_RANGE:
            self.skipTest("the ratchet counts days, so it is stated for the default range")
        blank = [r for r in self.results
                 if not any(o["is_comm"] for o in r["Observances"])]
        self.assertLessEqual(
            len(blank), self.MAX_DAYS_WITH_NO_COMMEMORATION,
            f"{len(blank)} days serve no commemoration (ratchet "
            f"{self.MAX_DAYS_WITH_NO_COMMEMORATION}); a NEW blank day means an observance "
            f"lost its is_comm mark -- e.g. {blank[0]['Date']} "
            f"({blank[0]['Liturgical Day']!r})")

    def test_the_two_marks_genuinely_overlap_in_range(self):
        """Stated over the whole catalog, not just the pinned dates: if the overlap ever
        empties, the marks have been reduced to two disjoint kinds and deriving one from
        the other has quietly become correct -- which is the modelling error."""
        catalog = engine._OBSERVANCE_CATALOG
        self.assertTrue(catalog.fast_ids & catalog.commemoration_ids)
        self.assertTrue(set(catalog) - catalog.fast_ids - catalog.commemoration_ids)


if __name__ == "__main__":
    unittest.main()
