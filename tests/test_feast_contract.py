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

  1. no placeholder -- an internal marker is not a name; a consumer can only discard it,
     and the day silently loses its name;
  2. Armenian resolves -- a name with no `hy` form is nearly always a name the engine
     made up rather than one the source uses;
  3. no runaway or repeated components -- the position-label overlay assembles names by
     concatenation, so it needs a guard against doubling one;
  4. clean characters -- reuses the same allow-list the shipped artifacts are gated on.

Deliberately NOT here: any storage limit. The engine serves whatever name the source
states, and the longest is 289 characters because that feast's name enumerates twelve
saints. How to store that belongs to the consumer, not to this package.
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

# Runaway-concatenation guard, NOT a storage limit. The engine serves whatever name the
# source states, however long -- how to store that is a consumer's problem, and encoding
# any particular consumer's column width here would be the wrong dependency direction.
#
# What this does catch is a bug in the name assembly. `_apply_position_label` prepends a
# regenerated component to a stored one, so a mistake there (a doubled label, a component
# appended per family instead of once) would inflate names without necessarily making any
# single component wrong. The longest name the engine legitimately serves is 289 chars --
# the Twelve Holy Doctors, whose name enumerates all twelve -- so a name past ~2x that is
# structurally broken rather than merely verbose.
MAX_PLAUSIBLE_NAME = int(os.environ.get("MAX_PLAUSIBLE_NAME", "600"))

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

    def test_no_name_is_implausibly_long(self):
        """Catches runaway concatenation in the name assembly, not a storage limit."""
        bad = [(d.isoformat(), len(en)) for d, (en, _) in self.names.items()
               if len(en) > MAX_PLAUSIBLE_NAME]
        self.assertEqual(
            bad[:10], [],
            f"{len(bad)} dates serve a name over {MAX_PLAUSIBLE_NAME} chars, well past "
            "the longest real one (289); suspect a duplicated or repeatedly-appended "
            "component in _apply_position_label")

    def test_no_component_is_repeated(self):
        """The position-label overlay must not re-add a component the name already has."""
        bad = []
        for d, (en, _) in self.names.items():
            parts = [p.strip() for p in en.split(" — ") if p.strip()]
            if len(parts) != len(set(parts)):
                bad.append((d.isoformat(), en))
        self.assertEqual(bad[:10], [],
                         f"{len(bad)} dates repeat a name component")

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
