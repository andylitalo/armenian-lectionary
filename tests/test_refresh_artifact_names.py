"""Pins the bug a second correction to an already-corrected label used to hit.

``dev/refresh_artifact_names.py`` used to resolve a ``saint_schedule.json`` label by
re-running the source-text correction chain on whatever text was currently stored, then
looking that text up in the catalog to recover its id. That works exactly once: the first
time a component is corrected, the stored text is still ``source_en`` and the chain finds
it. The second time the SAME component is corrected -- as happened twice in one session to
``discovery_of_relics_of`` (missing clause, then a transliteration fix) -- the stored text
is the FIRST correction, which is neither ``source_en`` nor the catalog's current text, so
the chain silently passes it through unchanged and the id lookup then crashes naming text
the catalog no longer has.

The fix resolves an entry that already carries ``observance_ids`` from those ids instead:
:func:`dev.observance_ids.text_for_id` asks the catalog what the id is called NOW, which is
correct no matter how many times the observance has been renamed since, because the id
itself never moves. This needs no ground-truth cache -- it substitutes a synthetic catalog
in-process, the same way ``tests/test_rename_reaches_the_served_name.py`` does -- and runs
in CI.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import _OBSERVANCE_SEP                # noqa: E402
from dev import observance_ids                                        # noqa: E402
from dev import refresh_artifact_names as refresh_mod                 # noqa: E402


class _SyntheticCatalog(unittest.TestCase):
    """Substitutes ``dev.observance_ids``'s module-level catalog lookups for the duration
    of a test, so this file needs no built ``observance_catalog.json`` and cannot leak a
    fake id into any other test."""

    def setUp(self):
        self._orig_catalog = observance_ids._catalog
        self._orig_text_to_id = observance_ids._text_to_id
        self.addCleanup(self._restore)

    def _restore(self):
        observance_ids._catalog = self._orig_catalog
        observance_ids._text_to_id = self._orig_text_to_id

    def _use_catalog(self, entries):
        """``entries``: ``{id: english text}``. Installs a catalog holding exactly these."""
        data = {sid: {"en": en, "hy": ""} for sid, en in entries.items()}

        def fake_catalog():
            return data

        def fake_text_to_id():
            return {en: sid for sid, en in entries.items()}

        observance_ids._catalog = fake_catalog
        observance_ids._text_to_id = fake_text_to_id


class TestASecondCorrectionResolvesById(_SyntheticCatalog):
    def test_a_label_one_generation_stale_is_corrected_without_raising(self):
        """The exact failure mode: the stored label is the FIRST correction, the catalog
        has moved on to a second one, and the entry still carries the (unchanged) id."""
        self._use_catalog({"discovery_of_relics_of": "...who reposed at Innaknya"})
        schedule = {"PN": {"sequence": [
            {"id": "discovery_of_relics", "label": "...who reposed at Innaknia.",
             "observance_ids": ["discovery_of_relics_of"]},
        ]}}

        changes = refresh_mod.refresh(schedule)

        entry = schedule["PN"]["sequence"][0]
        self.assertEqual(entry["label"], "...who reposed at Innaknya")
        self.assertEqual(entry["observance_ids"], ["discovery_of_relics_of"])
        self.assertIn(("...who reposed at Innaknia.", "...who reposed at Innaknya"), changes)

    def test_a_label_already_current_is_left_untouched(self):
        """The ordinary case stays a no-op -- the module's own idempotence claim."""
        self._use_catalog({"some_id": "Already Correct"})
        schedule = {"PN": {"sequence": [
            {"id": "x", "label": "Already Correct", "observance_ids": ["some_id"]},
        ]}}

        changes = refresh_mod.refresh(schedule)

        self.assertEqual(changes, [])
        self.assertEqual(schedule["PN"]["sequence"][0]["label"], "Already Correct")

    def test_a_packed_entry_recomposes_from_every_one_of_its_ids(self):
        """An entry naming several canons carries several ids; the label is their
        catalog text rejoined with the observance separator, in order."""
        self._use_catalog({
            "first_saint": "St. First, Renamed",
            "second_saint": "St. Second",
        })
        schedule = {"PN": {"sequence": [
            {"id": "packed", "label": "St. First — St. Second",
             "observance_ids": ["first_saint", "second_saint"]},
        ]}}

        refresh_mod.refresh(schedule)

        self.assertEqual(
            schedule["PN"]["sequence"][0]["label"],
            f"St. First, Renamed{_OBSERVANCE_SEP}St. Second")

    def test_a_stale_id_raises_naming_the_id_not_the_text(self):
        """A retired id with nothing migrated off it must fail loudly, not silently keep
        serving the stale label."""
        self._use_catalog({"some_other_id": "Unrelated"})
        schedule = {"PN": {"sequence": [
            {"id": "x", "label": "Old Text", "observance_ids": ["retired_id"]},
        ]}}

        with self.assertRaises(KeyError) as ctx:
            refresh_mod.refresh(schedule)
        self.assertIn("retired_id", str(ctx.exception))

    def test_an_id_less_entry_falls_back_to_text(self):
        """A brand-new entry this script has never touched has no id yet to anchor on;
        text is the only route, and it must still resolve once the text is a known one."""
        self._use_catalog({"new_id": "Untouched Feast Name"})
        schedule = {"PN": {"sequence": [
            {"id": "y", "label": "Untouched Feast Name", "observance_ids": []},
        ]}}

        changes = refresh_mod.refresh(schedule)

        # The label itself doesn't change (it was already the catalog's text) -- only
        # the id gets assigned, for the first time.
        self.assertEqual(changes, [([], ["new_id"])])
        self.assertEqual(schedule["PN"]["sequence"][0]["label"], "Untouched Feast Name")
        self.assertEqual(
            schedule["PN"]["sequence"][0]["observance_ids"], ["new_id"])


class TestTextForId(_SyntheticCatalog):
    def test_returns_the_catalog_text(self):
        self._use_catalog({"an_id": "The Text"})
        self.assertEqual(observance_ids.text_for_id("an_id"), "The Text")

    def test_raises_naming_the_id_when_absent(self):
        self._use_catalog({})
        with self.assertRaises(KeyError) as ctx:
            observance_ids.text_for_id("missing_id")
        self.assertIn("missing_id", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
