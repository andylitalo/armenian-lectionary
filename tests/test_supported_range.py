"""The supported-year guard on ``compute_armenian_lectionary``.

Outside 2001-2027 the engine has no validated data. It used to answer anyway, falling
through to its internal absence-markers and returning them as if they were names --
``compute_armenian_lectionary(date(2038, 2, 28))["Liturgical Day"]`` was
``"(commemoration)"``, and 2038-02-13 was ``"Feast (day not yet in validated table)"``.

``tests/test_feast_contract.py`` forbids exactly those strings *inside* the range, on the
grounds that an internal marker is not a name and a consumer can only discard it. Outside
the range it was the same defect with nothing looking.

Self-contained -- no reference cache.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import (                                       # noqa: E402
    MAX_YEAR, MIN_YEAR, calculate_liturgical_mode, compute_armenian_lectionary,
)


class TestSupportedRange(unittest.TestCase):
    def test_range_is_the_documented_window(self):
        self.assertEqual((MIN_YEAR, MAX_YEAR), (2001, 2027))

    def test_boundary_years_are_served(self):
        for d in (datetime.date(MIN_YEAR, 1, 1), datetime.date(MAX_YEAR, 12, 31)):
            with self.subTest(date=d):
                self.assertIn("Liturgical Day", compute_armenian_lectionary(d))

    def test_just_outside_raises(self):
        for d in (datetime.date(MIN_YEAR - 1, 12, 31),
                  datetime.date(MAX_YEAR + 1, 1, 1)):
            with self.subTest(date=d):
                with self.assertRaises(ValueError) as caught:
                    compute_armenian_lectionary(d)
                message = str(caught.exception)
                self.assertIn(d.isoformat(), message)
                self.assertIn(f"{MIN_YEAR}-{MAX_YEAR}", message)

    def test_the_placeholder_days_that_motivated_this_now_raise(self):
        """The two dates a 1990-2060 sweep found serving an internal marker."""
        for d in (datetime.date(2038, 2, 13), datetime.date(2038, 2, 28)):
            with self.subTest(date=d):
                with self.assertRaises(ValueError):
                    compute_armenian_lectionary(d)

    def test_the_guard_applies_in_every_language(self):
        for language in ("en", "hy"):
            with self.subTest(language=language):
                with self.assertRaises(ValueError):
                    compute_armenian_lectionary(
                        datetime.date(2038, 2, 28), language=language)

    def test_language_is_validated_before_the_date(self):
        """Both are ValueError, so pin which one a caller passing two bad arguments sees.

        The language check is the cheaper, more obviously-wrong failure, and it was here
        first; leaving the order to chance would make the message depend on argument
        evaluation order.
        """
        with self.assertRaises(ValueError) as caught:
            compute_armenian_lectionary(datetime.date(1900, 1, 1), language="fr")
        self.assertIn("unsupported language", str(caught.exception))

    def test_liturgical_mode_is_not_restricted(self):
        """Pure arithmetic on the paschal cycle, correct for any date the calendar allows.

        Guarding it would be scope creep with a cost: it is the one part of the result that
        needs no validated data, and callers computing a tone for an out-of-range date are
        not getting anything unvalidated.
        """
        for d in (datetime.date(1900, 1, 1), datetime.date(2038, 2, 28),
                  datetime.date(2400, 6, 1)):
            with self.subTest(date=d):
                mode = calculate_liturgical_mode(d)
                self.assertIn("Tone", mode)
                self.assertTrue(1 <= mode["Number"] <= 8)


if __name__ == "__main__":
    unittest.main()
