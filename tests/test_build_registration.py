"""A TSV rename must survive the BUILD, not only the serving path.

CLAUDE.md's contract is "a rename is a TSV edit, not an engine.py edit". Everything that
asserted it asserted the second half: tests/test_rename_reaches_the_served_name.py and
tests/test_language.py substitute a renamed catalog in process and re-run
``compute_armenian_lectionary``. Nothing anywhere imported dev/build_observance_catalog.py,
so the half of the contract that runs at build time -- does the rebuild still recognise the
renamed observance -- had no coverage at all, and shipped broken.

What broke, and why the serving tests could not see it. A generated label is registered by
three routes: ``approved_en``, the immutable ``source_en``, and the id the engine declares
for it. For 52 of the 216 labels the engine's literal equals NEITHER column ("Eve of the
Fast of Nativity" against a source_en of "Eve of Fast of Nativity"), so both text routes
die on a rename and only the declared id is left. The build was not asking for it:

  * ``declared_label_ids`` inferred through the previously-SHIPPED readings index instead
    of asking for the declaration, and
  * ``build_readings_index`` asked for a declared id for eves only, never for positions.

Two failures followed, and this file pins one test to each:

  * a label with no index entry had no route left at all -- the build refused, and
    ``--mint`` then reported ids it had not written, so re-running repeated the no-op
    forever. Index coverage has since grown to cover every pinned label with a unique id
    (see CLAUDE.md's "Index coverage" note), so ``UNINDEXED`` below no longer names a
    label the index actually misses -- the fixture only needs to be pinned with a single
    owning row, which this test does not depend on index coverage to exercise;
  * a label WITH an index entry ("Fifth Sunday of the Holy Cross") looked fine: the build
    succeeded, because registration was reading the previous build's index. But the index
    it wrote had silently dropped that label, so the NEXT rebuild -- reading what this one
    wrote -- failed. Silent artifact damage first, breakage one build later.

Everything here reads the tracked dev/observance_name_ground_truth.json and the shipped
table, so it needs no dev/reference_data/ cache and runs in CI. It drives the real build
functions over an in-memory copy of the ground truth; nothing is written to disk.
"""

import copy
import datetime
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import engine                                     # noqa: E402
from dev import build_observance_catalog as build                          # noqa: E402

# Two labels that exercise the two different failure modes. Both are "pinned": the engine
# literal differs from every source_en of their id, so a rename of approved_en leaves only
# the declared route. UNINDEXED must additionally be the SOLE row carrying its id -- the
# Advent eve, the one label still actually missing from the readings/coordinate index,
# fails that: its two raw spellings ("Eve of Fast of Advent" / "Eve of the Fast of Advent")
# share one id across two rows, so stripping the id from only one leaves it registered via
# its twin and the test below finds nothing to fail on.
UNINDEXED = ("Eve of Fast of Nativity", "Eve of the Fast of Nativity")
INDEXED = ("Fifth Sunday after the Holy Cross", "Fifth Sunday of the Holy Cross")


def _generated_labels():
    """``{(kind, literal label text): the date it was first seen}`` over the whole range."""
    out = {}
    d, end = datetime.date(engine.MIN_YEAR, 1, 1), datetime.date(engine.MAX_YEAR, 12, 31)
    while d <= end:
        for kind, label in (("position", engine._position_label(d)),
                            ("eve", engine._eve_label(d))):
            if label:
                out.setdefault((kind, label), d)
        d += datetime.timedelta(days=1)
    return out


class TestEveryGeneratedLabelIsDeclared(unittest.TestCase):
    """The invariant the build now rests on: the declared id is the ONLY route that
    survives a rename, so a label without one is a rename waiting to be stranded."""

    @classmethod
    def setUpClass(cls):
        cls.labels = _generated_labels()
        cls.ground_truth = build.load_ground_truth()

    def test_there_are_labels_to_check(self):
        self.assertGreater(len(self.labels), 200)

    def test_every_generated_label_declares_an_id(self):
        missing = {kl: d for kl, d in self.labels.items()
                   if engine.generated_observance_id(d, kl[0]) is None}
        self.assertEqual(
            {}, missing,
            "generated label(s) with no declared id. A position family declares its ids in "
            "engine._POSITION_IDS keyed on (template, ordinal); editing a _POSITION_FAMILIES "
            f"template without updating it lands here: {sorted(missing)[:5]}")

    def test_the_declared_id_agrees_with_the_text_route(self):
        """Where both resolve they are independent authorities on one question.

        A declared id that contradicts the row it belongs to would make a rename reach the
        wrong observance -- worse than not reaching one, because nothing downstream marks it.
        """
        gt = self.ground_truth
        approved = {r["approved_en"]: r.get("id") for r in gt.values() if r.get("approved_en")}
        by_source = {s: r.get("id") for s, r in gt.items() if r.get("id")}
        conflicts = []
        for (kind, label), d in sorted(self.labels.items()):
            declared = engine.generated_observance_id(d, kind)
            by_text = approved.get(label) or by_source.get(label)
            if declared and by_text and declared != by_text:
                conflicts.append(f"{kind} {label!r}: declared {declared}, text {by_text}")
        self.assertEqual([], conflicts[:5])

    def test_every_declared_id_is_stated_by_a_row(self):
        """registration() only accepts a declared id some row states; if none did, the
        build would refuse rather than register an observance nothing can reach."""
        stated = {r["id"] for r in self.ground_truth.values() if r.get("id")}
        orphaned = sorted({engine.generated_observance_id(d, kind)
                           for (kind, _l), d in self.labels.items()
                           if engine.generated_observance_id(d, kind)} - stated)
        self.assertEqual([], orphaned[:5])


class TestRegistrationSurvivesARename(unittest.TestCase):
    """The build must still recognise a renamed observance by the text it SERVES.

    ``served_components`` enumerates what engine.py composes -- the literal -- while the
    rename moves ``approved_en`` away from it. Registration has to bridge that, or the
    build reports a served, catalogued observance as having no id and refuses to write.
    """

    @classmethod
    def setUpClass(cls):
        cls.ground_truth = build.load_ground_truth()

    def _renamed(self, source_en):
        gt = copy.deepcopy(self.ground_truth)
        gt[source_en]["approved_en"] = gt[source_en]["approved_en"] + " RENAMED"
        return gt

    def test_the_fixture_labels_are_really_pinned(self):
        """Guards the premise: if a correction ever made a literal equal its source_en,
        these two would start passing through the text route and stop testing anything."""
        for source_en, literal in (UNINDEXED, INDEXED):
            row = self.ground_truth[source_en]
            self.assertEqual(row["approved_en"], literal)
            self.assertNotEqual(source_en, literal,
                                f"{source_en!r} is no longer pinned; pick another fixture")

    def test_a_rename_of_an_unindexed_label_stays_registered(self):
        source_en, literal = UNINDEXED
        expected = self.ground_truth[source_en]["id"]
        registered = build.registration(self._renamed(source_en))
        self.assertEqual(expected, registered(literal),
                         "the build no longer recognises the renamed observance, so it "
                         "would refuse to write and --mint could not unblock it")

    def test_a_rename_of_an_indexed_label_stays_registered(self):
        source_en, literal = INDEXED
        expected = self.ground_truth[source_en]["id"]
        registered = build.registration(self._renamed(source_en))
        self.assertEqual(expected, registered(literal))

    def test_registration_does_not_lean_on_the_shipped_index(self):
        """The index is the previous build's own output. Resolving through it made each
        build inherit the last one's blind spot -- a label dropped from the index stayed
        dropped, and the failure surfaced a build later, far from its cause."""
        source_en, literal = INDEXED
        expected = self.ground_truth[source_en]["id"]
        original = engine._OBSERVANCE_ID_BY_READINGS
        engine._OBSERVANCE_ID_BY_READINGS = {}          # simulate a thin/stale checkout
        try:
            registered = build.registration(self._renamed(source_en))
            self.assertEqual(expected, registered(literal))
        finally:
            engine._OBSERVANCE_ID_BY_READINGS = original


class TestTheReadingsIndexSurvivesARename(unittest.TestCase):
    """A rename must not cost a label its index entry.

    This is the failure that hid: the build SUCCEEDED and wrote an index two entries
    smaller, because id_for_literal_text had a declared route for eves and not for
    positions. Nothing compared the index to its predecessor, so the loss was invisible
    until the next rebuild failed on it.
    """

    @classmethod
    def setUpClass(cls):
        cls.ground_truth = build.load_ground_truth()
        cls.baseline = build.build_readings_index(cls.ground_truth)

    def test_the_baseline_index_is_populated(self):
        self.assertGreater(len(self.baseline), 300)

    def test_a_rename_costs_no_index_entry(self):
        source_en, _literal = INDEXED
        gt = copy.deepcopy(self.ground_truth)
        gt[source_en]["approved_en"] += " RENAMED"
        after = build.build_readings_index(gt)

        lost = sorted(x for x in (set(self.baseline.values()) - set(after.values())) if x)
        self.assertEqual([], lost,
                         "renaming one label dropped observance(s) from the rebuilt index; "
                         "the next rebuild would fail on them")
        self.assertEqual(len(self.baseline), len(after),
                         "the rebuilt index changed size after a rename")


class TestEveryPinnedLabelSurvivesARenameAtOnce(unittest.TestCase):
    """The named cases above cover two shapes; this covers all 52 pinned labels at once.

    Renames every row whose id any generated label declares, in one pass, and asserts the
    build still registers everything and writes the same index. One rebuild buys coverage
    of every label at once; the named tests stay because when this fails they say which
    shape broke.
    """

    @classmethod
    def setUpClass(cls):
        cls.ground_truth = build.load_ground_truth()
        cls.baseline = build.build_readings_index(cls.ground_truth)
        declared = {sid for (kind, _l), d in _generated_labels().items()
                    for sid in [engine.generated_observance_id(d, kind)] if sid}
        cls.renamed = copy.deepcopy(cls.ground_truth)
        cls.touched = 0
        for row in cls.renamed.values():
            if row.get("id") in declared and row.get("approved_en"):
                row["approved_en"] += " RENAMED"
                cls.touched += 1

    def test_the_sweep_actually_renamed_something(self):
        self.assertGreater(self.touched, 200)

    def test_nothing_the_engine_serves_loses_its_id(self):
        registered = build.registration(self.renamed)
        unregistered = sorted(t for t in build.served_components(self.renamed)
                              if not registered(t))
        self.assertEqual(
            [], unregistered[:5],
            f"{len(unregistered)} served component(s) became unregistered under a mass "
            "rename, so the build would refuse to write")

    def test_the_index_is_unchanged_by_a_mass_rename(self):
        after = build.build_readings_index(self.renamed)
        self.assertEqual(self.baseline, after,
                         "a mass rename changed the readings index; ids must not move "
                         "when the text they stand for does")


class TestTheShippedArtifactsAreReproducible(unittest.TestCase):
    """Both artifacts must rebuild from source, byte for byte.

    Standing cover for the thing that degraded silently: the index lost entries and no test
    compared it to anything. Needs no cache, unlike tests/test_table_build.py, so this
    reproducibility check is the one that actually runs in CI.
    """

    @classmethod
    def setUpClass(cls):
        cls.ground_truth = build.load_ground_truth()

    def test_the_catalog_rebuilds_to_what_is_shipped(self):
        catalog, problems = build.build_catalog(self.ground_truth)
        self.assertEqual([], problems)
        with open(build.CATALOG_PATH, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), catalog)

    def test_the_readings_index_rebuilds_to_what_is_shipped(self):
        with open(build.READINGS_INDEX_PATH, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), build.build_readings_index(self.ground_truth))


class TestRoutesAgreeIsActuallyAsserted(unittest.TestCase):
    """``_assert_routes_agree`` computed the declared id and only printed it.

    So a readings or coordinate entry that contradicted the DECLARATION passed the build
    silently -- and since the runtime takes the declared id first, the index would have been
    written keyed to one observance while the engine served another. Driven here with
    hand-built dicts, so it costs milliseconds and pins each disagreement separately.
    """

    KIND, TEXT, READINGS, COORD = "position", "A Label", ["Gen 1.1"], ("E", 3)

    def _run(self, expected, via_readings, via_coordinate):
        readings_ids, coordinate_ids = {}, {}
        if via_readings:
            readings_ids[engine._observance_id_from_readings(self.READINGS, self.KIND)] = \
                via_readings
        if via_coordinate:
            coordinate_ids[engine._observance_id_from_coordinate(*self.COORD, self.KIND)] = \
                via_coordinate
        key = (self.KIND, self.TEXT)
        d = datetime.date(2020, 1, 1)
        build._assert_routes_agree(
            readings_ids, coordinate_ids,
            {key: {"validated-table": [(tuple(self.READINGS), "commem", d)]}},
            {(self.KIND, self.TEXT, d): self.COORD},
            lambda text, kind=None: expected)

    def test_all_three_agreeing_is_fine(self):
        self._run("obs_a", "obs_a", "obs_a")

    def test_readings_disagreeing_with_the_declaration_fails(self):
        with self.assertRaises(SystemExit):
            self._run("obs_a", "obs_b", None)

    def test_coordinate_disagreeing_with_the_declaration_fails(self):
        with self.assertRaises(SystemExit):
            self._run("obs_a", None, "obs_b")

    def test_the_two_inferences_disagreeing_still_fails(self):
        with self.assertRaises(SystemExit):
            self._run(None, "obs_a", "obs_b")


class TestMintReportsOnlyWhatItWrote(unittest.TestCase):
    """``--mint`` must not claim to have written an id it could not place.

    It keys new ids by the text the ENGINE serves but writes them onto rows found by
    approved_en/source_en. Where a served text matches no row there is nothing to write to,
    and that used to be silent: the run printed "N id(s) written", changed nothing, and the
    identical re-run repeated the no-op, so the build could never be unblocked.
    """

    def test_mint_raises_rather_than_reporting_a_phantom_write(self):
        gt = build.load_ground_truth()
        source_en, literal = UNINDEXED
        # Rename the row AND strip its id, so the literal is served, unregistered, and
        # matched by no row -- the exact state that produced the phantom write.
        gt[source_en] = dict(gt[source_en], approved_en=literal + " RENAMED", id="")
        with self.assertRaises(SystemExit) as caught:
            build.mint(gt)
        self.assertIn("no row to carry an id", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
