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

Editing ``approved_en`` in the TSV is how a reviewer states a decision; the test then fails
until the artifacts are rebuilt (CLAUDE.md gives the order). For a whole component the
row itself is the registration -- ``build_ground_truth.py`` freezes ``approved_en`` and
``apply_ground_truth`` serves it. That failure is the point.

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
        cls.approved = {p for r in cls.rows for p in _components(r["approved_en"])}

    def test_review_file_is_populated(self):
        self.assertGreater(len(self.rows), 380,
                           f"{REVIEW_PATH} should carry every distinct feast component")
        blank = [r["source_en"] for r in self.rows if not r["approved_en"].strip()]
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

    def test_every_row_has_an_approved_armenian(self):
        """``approved_hy`` is a decision on every row, not an override on a few.

        It was an override column once -- filled on 3 rows of 397, empty everywhere else,
        with ``source_hy`` standing in. That made the two languages asymmetric in a way
        nothing enforced: a row could reach the catalog with no Armenian at all and the
        only symptom would be an English fallback at runtime.
        """
        blank = [r["source_en"] for r in self.rows if not r["approved_hy"].strip()]
        self.assertEqual(blank[:5], [],
                         f"{len(blank)} rows have no approved Armenian name")

    def test_every_id_less_row_says_why(self):
        """An empty ``id`` is a statement, so it has to be a legible one.

        Most id-less rows are PACKED DAYS -- one line carrying several First Volume canons,
        whose approved name splits them so each canon resolves to its own id. The rest are
        a comma-joined day and a one-off source spelling nothing emits or stores. Without
        the reason written down, an id missing on purpose and an id missing by accident
        look identical -- and the accident is the one that makes a served observance
        unaddressable.
        """
        silent = [r["source_en"] for r in self.rows
                  if not r["id"].strip() and "no id" not in r["note"]]
        self.assertEqual(
            silent[:5], [],
            f"{len(silent)} row(s) have no id and no note explaining why. Add the reason "
            "to dev/feast_name_review.NO_ID_REASONS so it survives a rebuild.")

    def test_source_text_never_reaches_a_served_name(self):
        """``source_en`` is a key and a record, never an ingredient.

        ``apply_ground_truth`` passes unknown text through unchanged, which is deliberate
        (a newly appearing name should surface for review, not be silently rewritten). The
        invariant that makes that safe is this one: every component the source publishes
        has a row, so the lookup always hits and the answer is always ``approved_en``
        verbatim. Nothing is ever assembled out of the raw text.
        """
        from dev.source_corrections import apply_ground_truth

        approved_for = {r["source_en"]: r["approved_en"] for r in self.rows}
        passed_through = [src for src, want in approved_for.items()
                          if apply_ground_truth(src) != want]
        self.assertEqual(
            passed_through[:5], [],
            f"{len(passed_through)} source component(s) do not resolve to their approved "
            "text through the lookup, so the raw spelling would reach a caller")

    def test_packed_days_resolve_to_their_canons(self):
        """A packed day carries no id, and every canon it names has one.

        This is what stops a consumer seeing one commemoration as several observances, and
        the other way round: the Tonats'oyts packs several First Volume canons onto one
        line when the taregir leaves few days for them (preface, Sixth), so the line is a
        DAY and the canons are the observances. Splitting it is only safe if each half
        actually resolves -- an unresolvable half would make a served observance
        unaddressable, silently.
        """
        import json
        import os
        cat_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "armenian_lectionary", "data", "observance_catalog.json")
        with open(cat_path, encoding="utf-8") as fh:
            catalog = json.load(fh)
        by_text = {e["en"]: sid for sid, e in catalog.items()}

        packed = [r for r in self.rows if _FEAST_SEP in r["approved_en"]]
        self.assertTrue(packed, "the packed-day splits were dropped from every row")
        for row in packed:
            self.assertFalse(
                row["id"].strip(),
                f"{row['source_en']!r} is a packed DAY and must not carry an id")
            en_parts = [c.strip() for c in row["approved_en"].split(_FEAST_SEP)]
            hy_parts = [c.strip() for c in row["approved_hy"].split(_FEAST_SEP)]
            self.assertEqual(
                len(en_parts), len(hy_parts),
                f"{row['source_en']!r} splits into {len(en_parts)} English canons but "
                f"{len(hy_parts)} Armenian ones")
            for part in en_parts:
                self.assertIn(part, by_text,
                              f"{part!r} is a canon of a packed day with no observance id")

    def test_open_questions_are_still_flagged(self):
        """The unresolved rows keep their question until someone answers it."""
        open_rows = [r for r in self.rows if r["status"] == "review"]
        self.assertGreater(len(open_rows), 0,
                           "the review status was dropped from every row")
        silent = [r["source_en"] for r in open_rows if not r["note"].strip()]
        self.assertEqual(silent[:5], [],
                         f"{len(silent)} rows are marked for review with no question")


@requires_reference_cache
class TestReviewCoversTheSource(unittest.TestCase):
    """Needs the ground-truth cache: checks the file has not fallen behind the source."""

    def test_every_source_component_has_a_row(self):
        from dev.feast_name_review import source_components

        days, _first = source_components()
        known = {r["source_en"] for r in _rows()}
        missing = sorted(set(days) - known)
        self.assertEqual(
            missing[:5], [],
            f"{len(missing)} feast component(s) in dev/reference_data have no row in "
            "dev/feast_name_review.tsv -- run python dev/feast_name_review.py and review "
            "the new rows")


if __name__ == "__main__":
    unittest.main()
