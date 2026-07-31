"""Source-INDEPENDENT invariants on the feast name, over the whole supported range.

Every other feast test needs ``dev/reference_data/``, which is git-ignored and stops at
2026 -- sacredtradition.am publishes nothing for 2027 (probed 2026-07-30: an empty page),
so its 365 cached days are empty and no oracle test asserts anything about them. bahk
nonetheless serves feast names through 2027.

These invariants need no ground truth, so they run on a fresh checkout, in CI, and across
the entire supported window including the year with no oracle. They are also the cheapest
guard in the suite: invariant 3 alone (`hy` differs from `en`) would have caught all six
of the defective dates the bahk PR review found, because the engine has no Armenian form
for a name it invented.

What each invariant protects:

  1. no placeholder -- bahk discards a placeholder as "no feast", so the day silently
     loses its name in the app;
  2. storable length -- ``Feast.name`` is a bounded CharField and PostgreSQL raises
     DataError past it, while bahk's SQLite test DB accepts it silently;
  3. Armenian resolves -- a name with no `hy` form is nearly always a name the engine
     made up;
  4. clean characters -- reuses the same allow-list the shipped artifacts are gated on.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.source_corrections import unexpected_chars                   # noqa: E402
from armenian_lectionary.engine import compute_armenian_lectionary     # noqa: E402

# The supported window (armenian_lectionary/app.py's range guard, and the window bahk's
# hub/services/feast_service.py mirrors). Deliberately includes 2027, the year with no
# ground truth -- covering it is the point.
MIN_YEAR = int(os.environ.get("LECTIONARY_MIN_YEAR", "2001"))
MAX_YEAR = int(os.environ.get("LECTIONARY_MAX_YEAR", "2027"))

# bahk's hub.models.Feast.name limit. Kept as a literal rather than imported: this package
# must not depend on bahk.
#
# 512, matching the widened column. Two names in the corpus exceed the previous 256 -- the
# Twelve Holy Doctors (289 chars) and the Holy Fathers of Egypt (257) -- and both are
# byte-identical to what sacredtradition.am serves, so the retired scrape hit the same
# PostgreSQL DataError: pre-existing, not a regression. The engine cannot fix them without
# truncating a name the source states in full, so the column was widened downstream
# instead (bahk migration 0057). Raise this only in step with that column, never to make a
# failing day pass.
FEAST_NAME_MAX = int(os.environ.get("FEAST_NAME_MAX", "512"))

# Internal markers that are not commemorations. A day reaching a caller with one of these
# has no usable name.
PLACEHOLDERS = ("(commemoration)", "(movable ordinary-time reading)",
                "(day not yet in validated table)")


def _every_supported_date():
    d = datetime.date(MIN_YEAR, 1, 1)
    end = datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        yield d
        d += datetime.timedelta(days=1)


class TestFeastNameContract(unittest.TestCase):
    """Invariants every served feast name must satisfy, on every supported date."""

    @classmethod
    def setUpClass(cls):
        cls.names = {}
        for d in _every_supported_date():
            cls.names[d] = (
                compute_armenian_lectionary(d)["Liturgical Day"],
                compute_armenian_lectionary(d, language="hy")["Liturgical Day"],
            )

    def test_range_is_fully_covered(self):
        self.assertGreater(len(self.names), 9800,
                           "the supported window should be ~27 years of dates")

    def test_no_name_is_empty(self):
        blank = [d.isoformat() for d, (en, _) in self.names.items() if not en.strip()]
        self.assertEqual(blank[:10], [], f"{len(blank)} dates have an empty feast name")

    def test_no_placeholder_reaches_callers(self):
        bad = [(d.isoformat(), en) for d, (en, _) in self.names.items()
               if any(marker in en for marker in PLACEHOLDERS)]
        self.assertEqual(
            bad[:10], [],
            f"{len(bad)} dates serve a placeholder instead of a feast name; downstream "
            "records these as 'no feast' and the day loses its name")

    def test_name_fits_downstream_storage(self):
        bad = [(d.isoformat(), len(en)) for d, (en, _) in self.names.items()
               if len(en) > FEAST_NAME_MAX]
        self.assertEqual(
            bad[:10], [],
            f"{len(bad)} dates serve a name longer than {FEAST_NAME_MAX} chars; "
            "PostgreSQL raises DataError on these (SQLite does not, so downstream tests "
            "will not catch it)")

    def test_armenian_name_resolves(self):
        """``hy`` must differ from ``en`` -- equality means no Armenian form is known."""
        bad = [(d.isoformat(), en) for d, (en, hy) in self.names.items() if en == hy]
        self.assertEqual(
            bad[:10], [],
            f"{len(bad)} dates have no Armenian feast name (hy == en). This usually means "
            "the English name is one the engine invented rather than one the source uses")

    def test_names_carry_no_contaminant_characters(self):
        bad = []
        for d, (en, hy) in self.names.items():
            for label, value in (("en", en), ("hy", hy)):
                stray = unexpected_chars(value)
                if stray:
                    bad.append((d.isoformat(), label, stray))
        self.assertEqual(bad[:10], [], f"{len(bad)} names carry unexpected characters")


if __name__ == "__main__":
    unittest.main()
