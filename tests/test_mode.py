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
            ("ԱՁ", "ԱԿ", "ԲՁ", "ԲԿ", "ԳՁ", "ԳԿ", "ԴՁ", "ԴԿ"),
        )

    def test_great_barekendan_and_easter_reset(self):
        for year in range(2001, 2027):
            easter = calculate_gregorian_easter(year)
            great_barekendan = easter - datetime.timedelta(days=49)
            self.assertEqual(calculate_liturgical_mode(great_barekendan), "ԴԿ", year)
            self.assertEqual(
                calculate_liturgical_mode(great_barekendan + datetime.timedelta(days=1)),
                "ԱՁ",
                year,
            )
            self.assertEqual(calculate_liturgical_mode(easter), "ԱՁ", year)

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
                self.assertEqual(calculate_liturgical_mode(next_day), "ԴԿ", next_day)
                day = next_day
                continue
            current_index = LITURGICAL_MODES.index(calculate_liturgical_mode(day))
            next_index = LITURGICAL_MODES.index(calculate_liturgical_mode(next_day))
            self.assertEqual(next_index, (current_index + 1) % 8, day)
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
        for day, mode in expected.items():
            self.assertEqual(calculate_liturgical_mode(day), mode, day)

    def test_mode_is_in_every_result_and_is_not_localized(self):
        day = datetime.date(2026, 7, 29)
        self.assertEqual(compute_armenian_lectionary(day)["Mode"], "ԲԿ")
        self.assertEqual(
            compute_armenian_lectionary(day, language="hy")["Mode"], "ԲԿ")


if __name__ == "__main__":
    unittest.main()
