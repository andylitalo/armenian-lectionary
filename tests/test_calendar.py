"""Fast, data-free unit tests for the pure calendar/coordinate math."""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import armenian_lectionary.engine as L  # noqa: E402


class TestEaster(unittest.TestCase):
    def test_known_years(self):
        self.assertEqual(L.calculate_gregorian_easter(2024),
                         datetime.date(2024, 3, 31))
        self.assertEqual(L.calculate_gregorian_easter(2025),
                         datetime.date(2025, 4, 20))
        self.assertEqual(L.calculate_gregorian_easter(2026),
                         datetime.date(2026, 4, 5))


class TestSundayClosestTo(unittest.TestCase):
    def test_always_sunday_within_three_days(self):
        for year in range(2014, 2027):
            for month, day in ((8, 15), (9, 14), (11, 18)):
                got = L.sunday_closest_to(year, month, day)
                target = datetime.date(year, month, day)
                self.assertEqual(got.weekday(), 6,
                                 f"{got} is not a Sunday")
                self.assertLessEqual(abs((got - target).days), 3,
                                     f"{got} too far from {target}")


class TestAnchors(unittest.TestCase):
    def test_keys_and_relations(self):
        a = L.anchors(2025)
        self.assertEqual(set(a), {"E", "TR", "AS", "EX", "HE", "TH"})
        self.assertEqual(a["TR"], a["E"] + datetime.timedelta(days=98))
        self.assertEqual(a["TH"], datetime.date(2025, 1, 6))


class TestWinterCoords(unittest.TestCase):
    def test_advent_saint_weekday(self):
        # Nov 22 2025 is a Saturday in the opening week of Advent (he = Nov 16,
        # Advent length 51 days, back-week 6 from Theophany). Plain + length-classed
        # + backward grid coordinates are all emitted.
        self.assertEqual(L.winter_coords(datetime.date(2025, 11, 22)),
                         {"AdvSatL": "51:0:Sat", "AdvSatBL": "51:6:Sat",
                          "AdvSat": "0:Sat", "AdvSatB": "6:Sat"})

    def test_postnativity_sunday(self):
        # Jan 19 2025 is the 1st Sunday after Nativity (post-Nat length 26 days,
        # 3 Sundays remaining before the eve of the Fast of Catechumens).
        self.assertEqual(L.winter_coords(datetime.date(2025, 1, 19)),
                         {"PnSunL": "26:1", "PnSunB": "3", "PnSun": "1"})

    def test_embedded_fixed_dates_excluded(self):
        # Presentation of Mary (Nov 21) and Conception of Mary (Dec 9) must not
        # pollute the grid -> no winter coordinates emitted.
        self.assertEqual(L.winter_coords(datetime.date(2025, 11, 21)), {})
        self.assertEqual(L.winter_coords(datetime.date(2025, 12, 9)), {})


class TestReadingClassification(unittest.TestCase):
    def test_classify(self):
        cases = {
            "2 Kings 1.1-5": "Old Testament",
            "Isaiah 1.1": "Old Testament",
            "Matthew 5.1": "Gospel",
            "Epistle of Paul to the Romans 1.1; Matthew 1.1": "Epistle",
            "Acts of the Apostles 2.1": "Epistle",
        }
        for ref, expected in cases.items():
            self.assertEqual(L._classify_reading(ref), expected, ref)

    def test_group_orders_liturgically(self):
        refs = ["Matthew 5.1", "Isaiah 1.1", "Acts of the Apostles 2.1"]
        grouped = L._group_readings(refs)
        self.assertEqual(list(grouped), ["Old Testament", "Epistle", "Gospel"])


class TestFastOfCatechumensAliturgical(unittest.TestCase):
    """The Mon-Thu ferial days of the Fast of the Catechumens are kept without a
    Liturgy: the Tōnats'oyts appoints no readings. The API must serve them empty but
    flag that emptiness as validated/intentional, never as a not-yet-modeled gap."""

    def test_aliturgical_days_are_validated_empty(self):
        # 2010: Fast-of-Catechumens Mon-Thu = Jan 25-28 (Easter offsets -69..-66).
        for day in (25, 26, 27, 28):
            r = L.compute_armenian_lectionary(datetime.date(2010, 1, day))
            self.assertEqual(r["ReadingsList"], [], day)
            self.assertEqual(r["Source"], "validated-table", day)
            self.assertEqual(r["Confidence"], "validated", day)
            self.assertIn("aliturgical", r["Note"], day)
            self.assertIn("Fast of the Catechumens", r["Liturgical Day"], day)


class TestSummerSundayContinua(unittest.TestCase):
    """The after-Transfiguration Sundays reached as a blank only in the earliest-Easter
    years (2008) ship source-derived readings byte-matching the ground truth."""

    def test_2008_summer_sundays(self):
        expected = {
            datetime.date(2008, 7, 20): [
                "Luke 4.14-30", "Isaiah 54.1-13",
                "St. Paul's First Epistle to Timothy 1.1-11", "John 2.1-11"],
            datetime.date(2008, 7, 27): [
                "Isaiah 58.13-59.7",
                "St. Paul's First Epistle to Timothy 4.12-5.10", "John 3.13-21"],
            datetime.date(2008, 8, 3): [
                "Isaiah 62.1-11",
                "St. Paul's Second Epistle to Timothy 2.15-19", "John 6.39-47"],
        }
        for d, refs in expected.items():
            r = L.compute_armenian_lectionary(d)
            self.assertEqual(r["ReadingsList"], refs, d)
            self.assertEqual(r["Source"], "first-volume-continua", d)
            self.assertEqual(r["Season"], "After Transfiguration", d)

    def test_summer_tier_does_not_overfire(self):
        # A normal-Easter year's same civil dates must NOT be claimed by the summer tier
        # (they are covered by the validated grid, or fall elsewhere).
        for d in (datetime.date(2015, 7, 20), datetime.date(2020, 8, 3)):
            self.assertIsNone(L._first_volume_summer_continua(d), d)


if __name__ == "__main__":
    unittest.main()
