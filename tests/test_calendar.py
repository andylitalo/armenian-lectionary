"""Fast, data-free unit tests for the pure calendar/coordinate math."""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lectionary as L  # noqa: E402


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
        # Nov 22 2025 is a Saturday in the opening week of Advent (he = Nov 16).
        self.assertEqual(L.winter_coords(datetime.date(2025, 11, 22)),
                         {"AdvSat": "0:Sat", "AdvSatB": "6:Sat"})

    def test_postnativity_sunday(self):
        # Jan 19 2025 is the 1st Sunday after Nativity.
        self.assertEqual(L.winter_coords(datetime.date(2025, 1, 19)),
                         {"PnSun": "1"})

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


if __name__ == "__main__":
    unittest.main()
