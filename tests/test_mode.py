"""Eight-mode cycle tests with SacredTradition source fixtures."""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import (  # noqa: E402
    LITURGICAL_MODES,
    calculate_gregorian_easter,
    calculate_liturgical_mode,
    compute_armenian_lectionary,
)


class TestLiturgicalMode(unittest.TestCase):
    def test_canonical_order(self):
        self.assertEqual(
            LITURGICAL_MODES,
            (
                "ԱՁ", "ԱԿ", "ԲՁ", "ԲԿ", "ԳՁ", "ԳԿ", "ԴՁ", "ԴԿ",
            ),
        )
        self.assertEqual(len(set(LITURGICAL_MODES)), 8)

    def test_great_barekendan_and_easter_reset(self):
        for year in range(2001, 2027):
            easter = calculate_gregorian_easter(year)
            great_barekendan = easter - datetime.timedelta(days=49)
            self.assertEqual(
                calculate_liturgical_mode(great_barekendan),
                {"Tone": "ԴԿ", "Number": 8},
                year,
            )
            self.assertEqual(
                calculate_liturgical_mode(great_barekendan + datetime.timedelta(days=1)),
                {"Tone": "ԱՁ", "Number": 1},
                year,
            )
            self.assertEqual(
                calculate_liturgical_mode(easter),
                {"Tone": "ԱՁ", "Number": 1},
                year,
            )

    def test_cycle_advances_daily_between_annual_resets(self):
        day = datetime.date(2001, 1, 1)
        end = datetime.date(2026, 12, 31)
        while day < end:
            next_day = day + datetime.timedelta(days=1)
            next_reset = (
                calculate_gregorian_easter(next_day.year)
                - datetime.timedelta(days=49)
            )
            if next_day == next_reset:
                self.assertEqual(
                    calculate_liturgical_mode(next_day)["Number"], 8, next_day
                )
                day = next_day
                continue
            current_number = calculate_liturgical_mode(day)["Number"]
            next_number = calculate_liturgical_mode(next_day)["Number"]
            self.assertEqual(next_number, current_number % 8 + 1, day)
            day = next_day

    def test_source_spot_checks(self):
        # Values fetched from sacredtradition.am/Calendar/xorh.php.  January 1 in
        # every supported source year guards the previous-Easter continuation rule;
        # the 2026 entries cover Great Barekendan, Easter, and the supplied July date.
        expected = {
            datetime.date(2001, 1, 1): "ԳԿ",
            datetime.date(2002, 1, 1): "ԳԿ",
            datetime.date(2003, 1, 1): "ԳՁ",
            datetime.date(2004, 1, 1): "ԱՁ",
            datetime.date(2005, 1, 1): "ԱԿ",
            datetime.date(2006, 1, 1): "ԱՁ",
            datetime.date(2007, 1, 1): "ԳՁ",
            datetime.date(2008, 1, 1): "ԳՁ",
            datetime.date(2009, 1, 1): "ԳՁ",
            datetime.date(2010, 1, 1): "ԱՁ",
            datetime.date(2011, 1, 1): "ԱՁ",
            datetime.date(2012, 1, 1): "ԳՁ",
            datetime.date(2013, 1, 1): "ԳՁ",
            datetime.date(2014, 1, 1): "ԳՁ",
            datetime.date(2015, 1, 1): "ԱՁ",
            datetime.date(2016, 1, 1): "ԴԿ",
            datetime.date(2017, 1, 1): "ԱՁ",
            datetime.date(2018, 1, 1): "ԳՁ",
            datetime.date(2019, 1, 1): "ԲԿ",
            datetime.date(2020, 1, 1): "ԴԿ",
            datetime.date(2021, 1, 1): "ԱՁ",
            datetime.date(2022, 1, 1): "ԱՁ",
            datetime.date(2023, 1, 1): "ԲԿ",
            datetime.date(2024, 1, 1): "ԲԿ",
            datetime.date(2025, 1, 1): "ԳՁ",
            datetime.date(2026, 1, 1): "ԱՁ",
            datetime.date(2026, 2, 14): "ԳՁ",
            datetime.date(2026, 2, 15): "ԴԿ",
            datetime.date(2026, 2, 16): "ԱՁ",
            datetime.date(2026, 4, 4): "ԴԿ",
            datetime.date(2026, 4, 5): "ԱՁ",
            datetime.date(2026, 4, 6): "ԱԿ",
            datetime.date(2026, 7, 28): "ԲՁ",
            datetime.date(2026, 7, 29): "ԲԿ",
            datetime.date(2026, 7, 30): "ԳՁ",
            datetime.date(2026, 12, 31): "ԴՁ",
        }
        numbers_by_tone = {
            tone: number for number, tone in enumerate(LITURGICAL_MODES, start=1)
        }
        for day, tone in expected.items():
            mode = calculate_liturgical_mode(day)
            self.assertEqual(mode["Tone"], tone, day)
            self.assertEqual(mode["Number"], numbers_by_tone[tone], day)

    def test_exact_mode_records(self):
        expected = {
            datetime.date(2026, 2, 15): {"Tone": "ԴԿ", "Number": 8},
            datetime.date(2026, 2, 16): {"Tone": "ԱՁ", "Number": 1},
            datetime.date(2026, 4, 5): {"Tone": "ԱՁ", "Number": 1},
            datetime.date(2026, 7, 29): {"Tone": "ԲԿ", "Number": 4},
        }
        for day, mode in expected.items():
            with self.subTest(day=day):
                self.assertEqual(calculate_liturgical_mode(day), mode)

    def test_mode_is_in_every_result_and_is_not_localized(self):
        day = datetime.date(2026, 7, 29)
        expected = {"Tone": "ԲԿ", "Number": 4}
        english_mode = compute_armenian_lectionary(day)["Mode"]
        armenian_mode = compute_armenian_lectionary(day, language="hy")["Mode"]
        self.assertEqual(english_mode, expected)
        self.assertEqual(armenian_mode, expected)
        self.assertEqual(english_mode, armenian_mode)
        self.assertIs(type(english_mode["Number"]), int)

    def test_returned_mode_records_are_independent(self):
        first = calculate_liturgical_mode(datetime.date(2026, 4, 5))
        first["Tone"] = "changed"
        self.assertEqual(
            calculate_liturgical_mode(datetime.date(2026, 4, 5)),
            {"Tone": "ԱՁ", "Number": 1},
        )


if __name__ == "__main__":
    unittest.main()
