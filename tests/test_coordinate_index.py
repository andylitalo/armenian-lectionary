"""The coordinate route may restate the labelling rule, but never contradict the table.

A position/eve label is resolved to its catalogued id by hashing the day's READINGS. When
a fixed civil feast outranks the day and takes its readings, that hash stops matching, and
before the coordinate route existed the day fell back to the literal template text -- so a
rename made in dev/observance_name_review.tsv reached every other day of the same label
but not that one. That was 93 of ~4,300 label-days across 31 labels and 11 civil dates
(Sep 8, Dec 9, Feb 14, Nov 20, Apr 7 ...), all of them days the engine was still visibly
serving the label on.

The coordinate route closes them by asking a second question -- "did the labelling rule
fire at this (anchor, offset)?" -- when the readings no longer answer the first. The two
are NOT equally strong, and this file is where that asymmetry is kept honest:

  * readings are evidence. They come from the validated table, produced independently of
    the rule that emitted the label.
  * a coordinate is the rule restating itself. It can only ever confirm what it already
    said, so its backing is rule-level: dev/verify_position_labels.py (6,216 matched, 0
    MISMATCH, 0 EXTRA) and dev/verify_eve_labels.py (338/338).

So the coordinate route is allowed to name an observance the readings cannot, but it is
never allowed to overrule the table about one. Three checks below, one per place that can
break: the two authorities agreeing (the premise), them being asked consistently (the
build), and the engine deferring when they part (the guard).
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                    # noqa: E402
from armenian_lectionary.engine import compute_armenian_lectionary        # noqa: E402


def _labelled_days():
    """``(date, base result, kind, rule label, coordinate, stored component)`` per day."""
    d, end = datetime.date(engine.MIN_YEAR, 1, 1), datetime.date(engine.MAX_YEAR, 12, 31)
    while d <= end:
        base = engine._compute_lectionary(d)
        parts = [p for p in base["Liturgical Day"].split(engine._OBSERVANCE_SEP)
                 if p and p not in engine._PLACEHOLDER_LABELS]
        for kind, label, coordinate, stored in (
                ("position", engine._position_label(d), engine._position_coordinate(d),
                 next((p for p in parts if engine._is_position_component(p)), None)),
                ("eve", engine._eve_label(d), engine._eve_coordinate(d),
                 next((p for p in parts if p.startswith("Eve of ")), None))):
            if label:
                yield d, base, kind, label, coordinate, stored
        d += datetime.timedelta(days=1)


class TestTheTableAndTheRuleAgree(unittest.TestCase):
    """The premise the coordinate route rests on, checked rather than assumed.

    A coordinate hit means "the rule fired here", and the rename it carries then overrides
    whatever the table stored for that day. That is only safe while the table and the rule
    agree about WHICH OBSERVANCE a coordinate names, which they do on every day in range
    that has both -- 6,312 position components and 335 eve components, zero disagreements.

    Compared by id, not by text: the table's stored text is looked up in the CURRENT
    catalog to get its id, and the rule's coordinate is looked up in the readings/coordinate
    index to get its id, using the exact same accessors the request-time override uses
    (``engine._OBSERVANCE_CATALOG``, ``engine._OBSERVANCE_ID_BY_READINGS``,
    ``engine._observance_id_from_coordinate``). A renamed label's text changes; its id
    never does (ids are stated, not derived -- CLAUDE.md), so a TSV-only rename of a
    covered label no longer fails this test. A genuine ``_POSITION_FAMILIES``/
    ``_EVE_FAMILIES`` defect (wrong anchor, wrong offset/window) still fails it: that
    changes the COORDINATE the rule computes for the date, which changes which id it
    resolves to, independent of any display text. For the 8 families with no readings or
    coordinate route ("Fast day", the six "Nth Sunday after Nativity", "Second Sunday
    after Pentecost") there is no id to compare, so this falls back to the old text
    comparison for them -- unchanged.

    One thing this no longer catches: a hand-typo directly in a covered family's literal
    template that leaves the anchor/offset arithmetic (and so the coordinate) untouched.
    That is an acceptable, deliberate narrowing, not a hole: for a covered label the
    literal's exact wording is already unreachable by any real request --
    ``_resolve_generated_text`` resolves through the readings hash first, which is
    independent of the literal's text -- so such a typo was never visible to a caller in
    the first place. It stays covered by ``dev/verify_position_labels.py``/
    ``verify_eve_labels.py`` (rule vs. source, cache-gated) and
    ``tests/test_observance_name_review.py`` (served vs. approved).

    This is deliberately NOT a check against sacredtradition.am: the verifiers do that, and
    they can only do it for years the reference cache covers. This one needs nothing but
    the shipped package, which is what lets it keep running after the cache stops.
    """

    def test_no_stored_component_disagrees_with_the_rule(self):
        ids = {entry["en"]: sid for sid, entry in engine._OBSERVANCE_CATALOG.items()}
        index = engine._OBSERVANCE_ID_BY_READINGS
        checked = {"position": 0, "eve": 0}
        disagreements = []
        for d, _base, kind, label, coordinate, stored in _labelled_days():
            if stored is None:
                continue
            checked[kind] += 1
            stored_id = ids.get(stored)
            coord_id = (index.get(engine._observance_id_from_coordinate(*coordinate, kind=kind))
                        if coordinate else None)
            if stored_id is not None and coord_id is not None:
                if stored_id != coord_id:
                    disagreements.append(
                        f"{d} {kind}: table {stored!r} (id {stored_id}) names a different "
                        f"observance than the rule's coordinate (id {coord_id}, currently "
                        f"{engine._OBSERVANCE_CATALOG[coord_id]['en']!r})")
            elif stored != label:
                # No id route on one or both sides (an uncovered family, or the catalog is
                # absent/thin) -- fall back to the old text comparison, unchanged.
                disagreements.append(f"{d} {kind}: table {stored!r} != rule {label!r}")
        self.assertEqual(
            disagreements, [],
            "the table and the labelling rule disagree; a coordinate-route rename would "
            "override the stored, validated value on these days:\n  "
            + "\n  ".join(disagreements[:20]))
        # Guards against the sweep silently going empty and passing vacuously.
        self.assertGreater(checked["position"], 6000)
        self.assertGreater(checked["eve"], 300)


class TestTheTwoRoutesNeverDisagree(unittest.TestCase):
    """dev/build_observance_catalog.py refuses to write an index whose two routes name
    different observances for the same day (``_assert_routes_agree``). That assertion runs
    at build time; this runs in CI against the SHIPPED index, so a data file that reaches
    the repo without a clean rebuild is caught too.
    """

    def setUp(self):
        if not engine._OBSERVANCE_ID_BY_READINGS:
            self.skipTest("readings index not present")

    def test_readings_and_coordinate_resolve_to_the_same_id(self):
        index = engine._OBSERVANCE_ID_BY_READINGS
        conflicts = []
        for d, base, kind, _label, coordinate, _stored in _labelled_days():
            readings = base["ReadingsList"]
            via_readings = (index.get(engine._observance_id_from_readings(readings, kind))
                            if readings else None)
            via_coordinate = (
                index.get(engine._observance_id_from_coordinate(*coordinate, kind=kind))
                if coordinate else None)
            if via_readings and via_coordinate and via_readings != via_coordinate:
                conflicts.append(f"{d} {kind}: readings -> {via_readings}, "
                                 f"coordinate -> {via_coordinate}")
        self.assertEqual(conflicts, [], "\n  ".join(conflicts[:20]))

    def test_position_and_eve_coordinates_cannot_collide(self):
        """Pentecost+21 is the coordinate of BOTH "Third Sunday after Pentecost" and "Eve
        of Fast of St. Gregory the Illuminator" -- 21 is a multiple of 7, so the eve is
        that Sunday every year, forever. ``kind`` is folded into the coordinate hash for
        exactly the reason it is folded into the readings hash.
        """
        self.assertNotEqual(
            engine._observance_id_from_coordinate("PE", 21, "position"),
            engine._observance_id_from_coordinate("PE", 21, "eve"))

    def test_every_covered_label_day_resolves(self):
        """The 93 unresolvable occurrences are gone, and stay gone.

        A label-day counts as covered if the label's id appears in the index at all; the
        assertion is that EVERY such day resolves, not merely most of them. That is the
        distinction the old mechanism could not make -- a label was covered while some of
        its days silently were not.
        """
        covered = set(engine._OBSERVANCE_ID_BY_READINGS.values())
        ids = {entry["en"]: sid for sid, entry in engine._OBSERVANCE_CATALOG.items()}
        unresolved, total = [], 0
        for d, base, kind, label, coordinate, _stored in _labelled_days():
            if ids.get(label) not in covered:
                continue
            total += 1
            if engine._resolve_generated_text(
                    None, base["ReadingsList"], kind, coordinate) is None:
                unresolved.append(f"{d} {kind} {label!r}")
        self.assertEqual(unresolved, [], "\n  ".join(unresolved[:20]))
        self.assertGreater(total, 5000)


class TestTheCoordinateGuard(unittest.TestCase):
    """The engine defers to the table when the two authorities part.

    Nothing in range exercises this -- that is what TestTheTableAndTheRuleAgree asserts --
    so it is driven with a constructed disagreement. It exists for the moment the range
    moves: LECTIONARY_MAX_YEAR is env-overridable by design (the deploy runbook widens it
    with one `gcloud run services update`, and the engine's own ValueError tells a library
    consumer to do the same), and neither the build assertion nor the sweep above is in
    the path when someone widens the range against an already-shipped index.
    """

    def setUp(self):
        if not engine._OBSERVANCE_ID_BY_READINGS:
            self.skipTest("readings index not present")
        self._orig = engine._OBSERVANCE_CATALOG
        self.addCleanup(setattr, engine, "_OBSERVANCE_CATALOG", self._orig)

    def _a_coordinate_only_day(self):
        """A day whose label resolves by coordinate but NOT by readings -- the only days
        the guard can change the outcome for."""
        index = engine._OBSERVANCE_ID_BY_READINGS
        for d, base, kind, label, coordinate, _stored in _labelled_days():
            if kind != "position" or not coordinate:
                continue
            readings = base["ReadingsList"]
            if readings and index.get(engine._observance_id_from_readings(readings, kind)):
                continue
            sid = index.get(
                engine._observance_id_from_coordinate(*coordinate, kind=kind))
            if sid:
                return d, label, sid
        self.skipTest("no coordinate-only position day in range")

    def test_a_rename_reaches_a_coordinate_only_day(self):
        d, label, sid = self._a_coordinate_only_day()
        engine._OBSERVANCE_CATALOG = {
            **self._orig, sid: {**self._orig[sid], "en": f"RENAMED {sid}"}}
        served = compute_armenian_lectionary(d)["Liturgical Day"]
        self.assertIn(f"RENAMED {sid}", served, f"{d} served {served!r} (was {label!r})")

    def test_a_disagreeing_stored_component_blocks_the_rename(self):
        """Same day, same rename -- but the stored label now carries a position component
        the rule would not print. The stored value must survive untouched.
        """
        d, label, sid = self._a_coordinate_only_day()
        engine._OBSERVANCE_CATALOG = {
            **self._orig, sid: {**self._orig[sid], "en": f"RENAMED {sid}"}}
        readings = engine._compute_lectionary(d)["ReadingsList"]
        disagreeing = "Fortieth day of Great Lent"
        self.assertTrue(engine._is_position_component(disagreeing))
        self.assertNotEqual(disagreeing, label)
        out = engine._apply_position_label(disagreeing, d, readings)
        self.assertIn(disagreeing, out, f"the stored component was overridden: {out!r}")
        self.assertNotIn(f"RENAMED {sid}", out)


if __name__ == "__main__":
    unittest.main()
