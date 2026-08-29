"""A rename in dev/observance_name_review.tsv must reach the served name.

That is the contract CLAUDE.md states -- "a rename is a TSV edit, not an engine.py edit"
-- and until now nothing asserted it end to end. What was asserted was narrower: that a
rename reaches the served name for the specific labels
``tests/test_language.py::TestNisibisAndElijahRenamesResolveThroughTheCatalog`` names, and
that the readings/coordinate index resolves the days it covers
(``tests/test_coordinate_index.py``). Neither could see an observance that has NO index
entry, because both start from the index.

The Advent eve is exactly that: it is Heesnak itself, its readings vary by year, and its
coordinate is one of two ((EX, 63) or (EX, 70)) depending on how far Heesnak falls after
Exaltation -- so it has no readings entry and no coordinate entry, and a rename of it
reached nothing at all. It was the one eve of thirteen that did not work, and no test
looked.

This sweeps EVERY eve the engine declares, on several occurrences each, in both
languages. It substitutes a renamed catalog rather than running the build, so it needs no
ground-truth cache and runs in CI.

Position labels are swept the same way. They declare their ids too, in
``engine._POSITION_IDS`` -- keyed on (template, ordinal), because a position family renders
one observance per ordinal and so cannot carry a single id inside its tuple the way an eve
can. Ten of them were never in the readings/coordinate index at all (the six "Nth Sunday
after Nativity", "Second Sunday of Pentecost", the two weekly fasts, and the bare marker),
so before the table a rename of those reached nothing.

The bare fast marker is excluded: it is declared as never served
(``engine._BARE_FAST_MARKERS``, docs section 6e -- 0 days in range carry it), so there is no
served text for a rename to reach.
"""

import csv
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402
from armenian_lectionary.engine import compute_armenian_lectionary         # noqa: E402

# Occurrences to try per eve. One is not enough: coverage is a property of a LABEL, but
# whether a rename reaches a given day is a property of that OCCURRENCE, and the two came
# apart before (CLAUDE.md, "Coverage is per-label; resolution is per-occurrence").
_SAMPLES = 3


def _dates_by_eve_id():
    """``{declared eve id: [every date it falls on, in range]}``."""
    out = {}
    d = datetime.date(engine.MIN_YEAR, 1, 1)
    end = datetime.date(engine.MAX_YEAR, 12, 31)
    while d <= end:
        sid = engine._eve_observance_id(d)
        if sid:
            out.setdefault(sid, []).append(d)
        d += datetime.timedelta(days=1)
    return out


class TestEveRenamesReachTheServedName(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.by_id = _dates_by_eve_id()

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")
        self._orig = engine._OBSERVANCE_CATALOG
        self.addCleanup(setattr, engine, "_OBSERVANCE_CATALOG", self._orig)

    def _occurrences(self, dates):
        if len(dates) <= _SAMPLES:
            return dates
        return [dates[0], dates[len(dates) // 2], dates[-1]]

    def test_every_declared_eve_is_in_the_catalog(self):
        """A declared id with no row is a rename that can never be made."""
        missing = sorted(sid for sid in self.by_id if sid not in self._orig)
        self.assertEqual(
            [], missing,
            "engine._EVE_FAMILIES/_EVE_CIVIL declare an id the catalog does not have; "
            "either the id is wrong or dev/observance_name_review.tsv lost its row")

    def test_a_rename_reaches_every_occurrence_in_both_languages(self):
        failures = []
        for sid, dates in sorted(self.by_id.items()):
            for lang in ("en", "hy"):
                sentinel = f"RENAMED-{sid}-{lang}"
                original = self._orig[sid][lang]
                engine._OBSERVANCE_CATALOG = self._orig.replacing(sid, **{lang: sentinel})
                for day in self._occurrences(dates):
                    served = compute_armenian_lectionary(
                        day, language=lang)["Liturgical Day"]
                    if sentinel not in served:
                        failures.append(f"{sid} {lang} {day}: rename absent, served "
                                        f"{served!r}")
                    elif original in served:
                        failures.append(f"{sid} {lang} {day}: served BOTH names, "
                                        f"{served!r}")
                engine._OBSERVANCE_CATALOG = self._orig
        self.assertEqual(
            [], failures[:10],
            f"{len(failures)} eve rename(s) did not reach the served name:\n  "
            + "\n  ".join(failures[:10]))

    def test_the_sweep_covers_every_declared_eve(self):
        """Guards against the sweep quietly shrinking to the eves that happen to work."""
        declared = {sid for _a, _o, sid, _t in engine._EVE_FAMILIES}
        declared |= {sid for sid, _t in engine._EVE_CIVIL.values()}
        declared.add(engine._ADVENT_EVE_ID)
        self.assertEqual(
            declared - set(self.by_id), set(),
            "an eve is declared but never falls in the supported range, so nothing here "
            "exercises it")


def _dates_by_position_id():
    """``{declared position id: [every date it is served on, in range]}``."""
    out = {}
    d = datetime.date(engine.MIN_YEAR, 1, 1)
    end = datetime.date(engine.MAX_YEAR, 12, 31)
    while d <= end:
        sid = engine._position_observance_id(d)
        if sid:
            out.setdefault(sid, []).append(d)
        d += datetime.timedelta(days=1)
    return out


class TestPositionRenamesReachTheServedName(TestEveRenamesReachTheServedName):
    """The position twin of the eve sweep, over engine._POSITION_IDS."""

    @classmethod
    def setUpClass(cls):
        declined = {engine._OBSERVANCE_CATALOG.id_of(t)
                    for t in engine._BARE_FAST_MARKERS}
        cls.by_id = {sid: days for sid, days in _dates_by_position_id().items()
                     if sid not in declined}

    def test_every_declared_eve_is_in_the_catalog(self):
        missing = sorted(sid for sid in self.by_id if sid not in self._orig)
        self.assertEqual(
            [], missing,
            "engine._POSITION_IDS declares an id the catalog does not have")

    def test_the_sweep_covers_every_declared_eve(self):
        """Every (template, ordinal) the rule can render must have a declared id.

        This is what makes a template edit fail loudly instead of silently stranding a
        rename: change the wording in ``_POSITION_FAMILIES`` without adding the entry to
        ``_POSITION_IDS`` and the label turns up here with no id.
        """
        d = datetime.date(engine.MIN_YEAR, 1, 1)
        end = datetime.date(engine.MAX_YEAR, 12, 31)
        uncovered = {}
        while d <= end:
            label = engine._position_label(d)
            if label and engine._position_observance_id(d) is None:
                uncovered.setdefault(label, d)
            d += datetime.timedelta(days=1)
        self.assertEqual(
            {}, uncovered,
            "position label(s) the rule renders with no entry in engine._POSITION_IDS; "
            "add the (template, ordinal) -> id entry, reusing the observance's existing "
            f"id: {sorted(uncovered)[:5]}")


class TestCompositeRowsReferenceTheirHalvesById(unittest.TestCase):
    """A packed day's approved name is its halves' names, joined -- not a third decision.

    Three rows pack the Atomian generals' canon. Each quoted that canon's name as TEXT, so
    renaming the canon left all three quoting the old one: the catalog build reported the
    old name as a served observance with no id and refused to write, and the days those
    rows name went on serving the old text.

    ``component_ids`` is the link, frozen once while the halves still resolved by text and
    immutable thereafter, exactly as ``id`` is. ``build_ground_truth._compose`` recomputes
    the join from it every time, so the stored text is a record rather than a source.
    """

    SEP = " \u2014 "

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "dev", "observance_name_review.tsv")
        if not os.path.exists(path):
            raise unittest.SkipTest("dev/observance_name_review.tsv absent")
        with open(path, encoding="utf-8", newline="") as fh:
            cls.rows = list(csv.DictReader(fh, delimiter="\t"))
        cls.by_id = {r["id"]: r for r in cls.rows if r["id"]}
        cls.composites = [r for r in cls.rows
                          if r["approved_en"] and cls.SEP in r["approved_en"]]

    def test_there_are_composites_to_check(self):
        self.assertGreater(len(self.composites), 0)

    def test_every_composite_states_its_halves(self):
        missing = [r["source_en"] for r in self.composites if not r["component_ids"]]
        self.assertEqual(
            [], missing[:5],
            f"{len(missing)} composite row(s) do not state component_ids, so a rename of "
            "one of their halves cannot reach them; run dev/observance_name_review.py "
            "while the halves still resolve by text")

    def test_every_referenced_id_exists(self):
        """An id retired out from under a composite would silently break the join."""
        dangling = []
        for r in self.composites:
            for sid in (r["component_ids"] or "").split(self.SEP):
                if sid.strip() and sid.strip() not in self.by_id:
                    dangling.append((r["source_en"], sid.strip()))
        self.assertEqual([], dangling[:5])

    def test_the_stored_text_equals_the_join_of_its_halves(self):
        """The record and the projection agree -- if they ever part, the record is stale."""
        stale = []
        for r in self.composites:
            if not r["component_ids"]:
                continue
            ids = [sid.strip() for sid in r["component_ids"].split(self.SEP)]
            for lang in ("en", "hy"):
                field = f"approved_{lang}"
                rebuilt = self.SEP.join(self.by_id[sid][field] for sid in ids)
                if rebuilt != r[field]:
                    stale.append(f"{r['source_en']!r} {lang}:\n"
                                 f"      stored  {r[field]!r}\n"
                                 f"      halves  {rebuilt!r}")
        self.assertEqual(
            [], stale[:3],
            "a composite row's stored text disagrees with its halves; rerun "
            "dev/observance_name_review.py then dev/build_ground_truth.py:\n  "
            + "\n  ".join(stale[:3]))


if __name__ == "__main__":
    unittest.main()
