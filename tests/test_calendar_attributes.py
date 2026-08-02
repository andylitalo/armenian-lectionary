"""Contracts for language-independent calendar routing attributes."""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import compute_armenian_lectionary  # noqa: E402


CALENDAR_KEYS = {
    "Weekday",
    "Is Sunday",
    "Is Dominical",
    "Is Fast Day",
    "Fast Context",
    "Is Saints Day",
    "Saint Classes",
    "Is Cross Feast",
    "Is Marian Feast",
    "Is Memorial",
}

FAST_CONTEXTS = {
    None,
    "weekly_fast",
    "great_lent",
    "holy_week",
    "fast_of_catechumens",
    "fast_of_prophet_elijah",
    "fast_of_saint_gregory",
    "fast_of_transfiguration",
    "fast_of_assumption",
    "fast_of_holy_cross",
    "fast_of_varaga_cross",
    "fast_of_advent",
    "fast_of_saint_james",
    "fast_of_nativity",
}

SAINT_CLASSES = {
    "apostle",
    "prophet",
    "martyr",
    "hierarch",
    "vartapet",
    "monastic",
    "virgin",
    "illuminator",
    "hripsimian",
}


class TestCalendarAttributes(unittest.TestCase):
    def test_contract_for_every_supported_date(self):
        day = datetime.date(2001, 1, 1)
        end = datetime.date(2027, 12, 31)
        while day <= end:
            attributes = compute_armenian_lectionary(day)["Calendar"]
            self.assertEqual(set(attributes), CALENDAR_KEYS, day)
            self.assertEqual(attributes["Weekday"], day.strftime("%A"), day)
            self.assertEqual(attributes["Is Sunday"], day.weekday() == 6, day)
            for key in (
                    "Is Sunday", "Is Dominical", "Is Fast Day", "Is Saints Day",
                    "Is Cross Feast", "Is Marian Feast", "Is Memorial"):
                self.assertIs(type(attributes[key]), bool, (day, key))
            self.assertIn(attributes["Fast Context"], FAST_CONTEXTS, day)
            self.assertIs(type(attributes["Saint Classes"]), list, day)
            self.assertTrue(set(attributes["Saint Classes"]) <= SAINT_CLASSES, day)
            self.assertEqual(
                len(attributes["Saint Classes"]),
                len(set(attributes["Saint Classes"])),
                day,
            )
            if attributes["Saint Classes"]:
                self.assertTrue(attributes["Is Saints Day"], day)
            if attributes["Is Fast Day"]:
                self.assertIsNotNone(attributes["Fast Context"], day)
            day += datetime.timedelta(days=1)

    def test_language_does_not_change_calendar_identifiers(self):
        day = datetime.date(2026, 6, 1)
        en = compute_armenian_lectionary(day, language="en")
        hy = compute_armenian_lectionary(day, language="hy")
        self.assertEqual(en["Calendar"], hy["Calendar"])

    def test_great_lent_context_does_not_make_sunday_a_fast_day(self):
        sunday = compute_armenian_lectionary(datetime.date(2026, 3, 22))["Calendar"]
        monday = compute_armenian_lectionary(datetime.date(2026, 3, 23))["Calendar"]
        self.assertTrue(sunday["Is Sunday"])
        self.assertFalse(sunday["Is Fast Day"])
        self.assertEqual(sunday["Fast Context"], "great_lent")
        self.assertTrue(monday["Is Fast Day"])
        self.assertEqual(monday["Fast Context"], "great_lent")

    def test_named_and_weekly_fast_contexts(self):
        catechumens = compute_armenian_lectionary(
            datetime.date(2026, 1, 26))["Calendar"]
        weekly = compute_armenian_lectionary(datetime.date(2026, 1, 14))["Calendar"]
        self.assertEqual(catechumens["Fast Context"], "fast_of_catechumens")
        self.assertEqual(weekly["Fast Context"], "weekly_fast")

    def test_fast_collisions_preserve_both_calendar_identities(self):
        nativity = compute_armenian_lectionary(
            datetime.date(2026, 9, 8))["Calendar"]
        conception = compute_armenian_lectionary(
            datetime.date(2026, 12, 9))["Calendar"]
        annunciation = compute_armenian_lectionary(
            datetime.date(2023, 4, 7))["Calendar"]

        self.assertTrue(nativity["Is Fast Day"])
        self.assertEqual(nativity["Fast Context"], "fast_of_holy_cross")
        self.assertTrue(nativity["Is Marian Feast"])
        self.assertTrue(conception["Is Fast Day"])
        self.assertEqual(conception["Fast Context"], "fast_of_saint_james")
        self.assertTrue(conception["Is Marian Feast"])
        self.assertTrue(annunciation["Is Fast Day"])
        self.assertEqual(annunciation["Fast Context"], "holy_week")
        self.assertTrue(annunciation["Is Marian Feast"])

    def test_source_derived_varaga_and_saint_james_fast_windows(self):
        varaga = compute_armenian_lectionary(
            datetime.date(2026, 9, 21))["Calendar"]
        saint_james = compute_armenian_lectionary(
            datetime.date(2026, 12, 7))["Calendar"]

        self.assertTrue(varaga["Is Fast Day"])
        self.assertEqual(varaga["Fast Context"], "fast_of_varaga_cross")
        self.assertTrue(saint_james["Is Fast Day"])
        self.assertEqual(saint_james["Fast Context"], "fast_of_saint_james")

    def test_saint_day_and_broad_classes(self):
        hripsime = compute_armenian_lectionary(
            datetime.date(2026, 6, 1))["Calendar"]
        hermits = compute_armenian_lectionary(
            datetime.date(2026, 1, 19))["Calendar"]
        self.assertTrue(hripsime["Is Saints Day"])
        self.assertEqual(
            hripsime["Saint Classes"], ["martyr", "virgin", "hripsimian"])
        self.assertTrue(hermits["Is Saints Day"])
        self.assertEqual(hermits["Saint Classes"], ["monastic"])

    def test_cross_feast_is_not_the_cross_season(self):
        feast = compute_armenian_lectionary(datetime.date(2026, 9, 13))["Calendar"]
        sunday_after = compute_armenian_lectionary(
            datetime.date(2026, 9, 20))["Calendar"]
        self.assertTrue(feast["Is Cross Feast"])
        self.assertTrue(feast["Is Dominical"])
        self.assertFalse(sunday_after["Is Cross Feast"])

    def test_marian_feast_is_not_a_fast_named_for_mary(self):
        fast = compute_armenian_lectionary(datetime.date(2026, 8, 10))["Calendar"]
        feast = compute_armenian_lectionary(datetime.date(2026, 8, 16))["Calendar"]
        self.assertFalse(fast["Is Marian Feast"])
        self.assertTrue(fast["Is Fast Day"])
        self.assertTrue(feast["Is Marian Feast"])
        self.assertTrue(feast["Is Dominical"])

    def test_assumption_observance_ends_before_later_sundays(self):
        postfeast = compute_armenian_lectionary(
            datetime.date(2026, 8, 23))["Calendar"]
        belt = compute_armenian_lectionary(
            datetime.date(2026, 8, 30))["Calendar"]
        later_sunday = compute_armenian_lectionary(
            datetime.date(2026, 9, 6))["Calendar"]

        self.assertTrue(postfeast["Is Marian Feast"])
        self.assertTrue(belt["Is Marian Feast"])
        self.assertFalse(later_sunday["Is Marian Feast"])

    def test_church_dedication_is_dominical_but_not_a_cross_feast(self):
        attributes = compute_armenian_lectionary(
            datetime.date(2026, 9, 12))["Calendar"]

        self.assertFalse(attributes["Is Cross Feast"])
        self.assertTrue(attributes["Is Dominical"])

    def test_memorial_can_overlap_a_feast_family(self):
        attributes = compute_armenian_lectionary(
            datetime.date(2026, 9, 14))["Calendar"]
        self.assertTrue(attributes["Is Memorial"])
        self.assertTrue(attributes["Is Cross Feast"])
        self.assertTrue(attributes["Is Dominical"])

    def test_vardanants_source_memorial_marker_is_exposed(self):
        attributes = compute_armenian_lectionary(
            datetime.date(2026, 2, 12))["Calendar"]

        self.assertTrue(attributes["Is Saints Day"])
        self.assertTrue(attributes["Is Memorial"])

    def test_genocide_commemoration_has_a_source_era_change(self):
        before = compute_armenian_lectionary(
            datetime.date(2015, 4, 24))["Calendar"]
        after = compute_armenian_lectionary(
            datetime.date(2016, 4, 24))["Calendar"]

        self.assertFalse(before["Is Saints Day"])
        self.assertTrue(after["Is Saints Day"])
        self.assertIn("martyr", after["Saint Classes"])

    def test_source_explicit_saint_titles_and_classes(self):
        john = compute_armenian_lectionary(
            datetime.date(2026, 1, 15))["Calendar"]
        translators = compute_armenian_lectionary(
            datetime.date(2026, 10, 10))["Calendar"]
        doctors = compute_armenian_lectionary(
            datetime.date(2026, 10, 24))["Calendar"]

        self.assertTrue(john["Is Saints Day"])
        self.assertTrue(translators["Is Saints Day"])
        self.assertIn("vartapet", translators["Saint Classes"])
        self.assertTrue(doctors["Is Saints Day"])
        self.assertIn("vartapet", doctors["Saint Classes"])

    def test_service_selection_data_is_out_of_scope(self):
        result = compute_armenian_lectionary(datetime.date(2026, 4, 7))
        for key in (
                "Service Data", "Service Profile", "Trisagion", "Karoz", "Mesedi",
                "Hamparsum"):
            self.assertNotIn(key, result)


if __name__ == "__main__":
    unittest.main()
