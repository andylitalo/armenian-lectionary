"""Holds the engine to OUR reviewed feast names, not to sacredtradition.am's.

``dev/feast_name_review.tsv`` is the one ground truth in this repo that is ours: a row per
distinct feast-name component with the English spelling a human has approved. Every other
name test measures fidelity to the source, and the engine now reproduces the source on
9496/9496 days -- so those tests would happily pass on a name the source spells wrong.
Only this one can fail for the right reason.

The two directions matter differently:

  * every component the engine SERVES is approved -- the strong one, and the only test in
    the suite that covers 2001-2027 against a reviewed name rather than against the
    source. It is what stops a rebuild from quietly reintroducing a spelling a reviewer
    rejected;
  * every component the source publishes has a row -- so a re-fetch that adds a name
    cannot slip past review by simply not being in the file.

Editing ``approved`` in the TSV is how a reviewer states a decision; the test then fails
until the fold is registered in ``dev/source_corrections._FEAST_TEXT_FIXES`` and the
artifacts are rebuilt (CLAUDE.md gives the order). That failure is the point.

The TSV is checked in and needs no cache, so the served-name direction runs anywhere. The
coverage direction needs ``dev/reference_data/`` and skips without it.
"""

import csv
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import (                               # noqa: E402
    _FEAST_SEP, compute_armenian_lectionary,
)
from tests._reference_cache import requires_reference_cache            # noqa: E402

REVIEW_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "dev", "feast_name_review.tsv")

MIN_YEAR = int(os.environ.get("LECTIONARY_MIN_YEAR", "2001"))
MAX_YEAR = int(os.environ.get("LECTIONARY_MAX_YEAR", "2027"))


def _rows():
    with open(REVIEW_PATH, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _components(text):
    return [c.strip() for c in (text or "").split(_FEAST_SEP) if c.strip()]


class TestApprovedNames(unittest.TestCase):
    """Runs everywhere: the reviewed names are checked in, no cache needed."""

    @classmethod
    def setUpClass(cls):
        cls.rows = _rows()
        # An approved name may itself be several components: one registered fix splits a
        # comma-joined fast marker off its commemoration.
        cls.approved = {p for r in cls.rows for p in _components(r["approved"])}

    def test_review_file_is_populated(self):
        self.assertGreater(len(self.rows), 380,
                           f"{REVIEW_PATH} should carry every distinct feast component")
        blank = [r["source"] for r in self.rows if not r["approved"].strip()]
        self.assertEqual(blank[:5], [],
                         f"{len(blank)} rows have no approved English name")

    def test_every_served_component_is_approved(self):
        """No date in the supported window may serve an unreviewed name."""
        unapproved = {}
        d = datetime.date(MIN_YEAR, 1, 1)
        end = datetime.date(MAX_YEAR, 12, 31)
        while d <= end:
            for comp in _components(
                    compute_armenian_lectionary(d)["Liturgical Day"]):
                if comp not in self.approved:
                    unapproved.setdefault(comp, d.isoformat())
            d += datetime.timedelta(days=1)
        self.assertEqual(
            sorted(unapproved.items())[:10], [],
            f"{len(unapproved)} feast-name component(s) reach callers without an "
            f"approved spelling in dev/feast_name_review.tsv. Either the reviewed name "
            "has not been applied (register the fold in dev/source_corrections and "
            "rebuild -- see CLAUDE.md), or a new name appeared and needs a review row "
            "(python dev/feast_name_review.py)")

    def test_open_questions_are_still_flagged(self):
        """The unresolved rows keep their question until someone answers it."""
        open_rows = [r for r in self.rows if r["status"] == "review"]
        self.assertGreater(len(open_rows), 0,
                           "the review status was dropped from every row")
        silent = [r["source"] for r in open_rows if not r["note"].strip()]
        self.assertEqual(silent[:5], [],
                         f"{len(silent)} rows are marked for review with no question")


@requires_reference_cache
class TestReviewCoversTheSource(unittest.TestCase):
    """Needs the ground-truth cache: checks the file has not fallen behind the source."""

    def test_every_source_component_has_a_row(self):
        from dev.feast_name_review import source_components

        days, _first = source_components()
        known = {r["source"] for r in _rows()}
        missing = sorted(set(days) - known)
        self.assertEqual(
            missing[:5], [],
            f"{len(missing)} feast component(s) in dev/reference_data have no row in "
            "dev/feast_name_review.tsv -- run python dev/feast_name_review.py and review "
            "the new rows")


if __name__ == "__main__":
    unittest.main()
