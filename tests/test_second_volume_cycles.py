"""The Second Volume cycle artifact still comes out of its generator.

``armenian_lectionary/data/second_volume_cycles.json`` feeds the ``second-volume-cycle``
tier, which sits above the generative laydown because it reads the Tonatsoyts' per-year-type
calendar directly. It is built dev-time from the grabar-ocr translation and validated
against ground truth, then committed.

Committed build products rot quietly. This one did: for a stretch, re-running
``dev/build_second_volume_cycles.py`` no longer reproduced the checked-in file, so nobody
could safely touch the generator -- any change to it arrived mixed with an unrelated diff
nobody had reviewed, and the standing advice was simply not to run it. That is a bad place
for a data file that decides which readings 68 days get.

The two failure modes this catches:

  * the generator changes and the artifact is not rebuilt (or the reverse);
  * the artifact is hand-edited, which would be invisible otherwise.

It is skipped without ``dev/reference_data/``, because the build validates every entry
against ground truth and refuses to run without it.
"""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests._reference_cache import requires_reference_cache            # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACT = os.path.join(REPO, "armenian_lectionary", "data", "second_volume_cycles.json")
BUILD = os.path.join(REPO, "dev", "build_second_volume_cycles.py")
TRANSLATION = os.path.expanduser(
    "~/church/grabar-ocr/runs/human__proj__tess__gemini-min/translations/"
    "gemini-flash/translated.md")


class TestCycleSelectionIsGregorianNotTrueTaregir(unittest.TestCase):
    """The cycle tier is keyed by this year's REFORMED (Gregorian) Easter, never by the
    year's true Taregir letter -- see dev/build_second_volume_cycles.py's module
    docstring and dev/paschal_index.taregir_for's warning. Both answer real questions;
    they are just DIFFERENT questions, and confusing them once nearly reverted a correct
    fix (docs/observance-name-corrections.md section 7d). This pins the distinction so it
    cannot happen silently again. Needs no ground truth or grabar-ocr -- source-
    independent, so it also covers 2027.
    """

    def test_true_taregir_and_served_easter_key_disagree_every_year(self):
        """Checked across the whole supported range: 0/27 years share a letter between
        dev.paschal_index.taregir_for(y) and ALPHA[k-1] computed from y's REFORMED
        Easter -- i.e. these are never interchangeable, not merely "usually different".
        """
        import datetime

        from dev.paschal_index import ALPHA, taregir_for
        from armenian_lectionary.engine import (
            MAX_YEAR, MIN_YEAR, calculate_gregorian_easter,
        )

        agree = 0
        for y in range(MIN_YEAR, MAX_YEAR + 1):
            k = (calculate_gregorian_easter(y) - datetime.date(y, 3, 21)).days
            if taregir_for(y) == ALPHA[k - 1]:
                agree += 1
        self.assertEqual(0, agree)

    def test_2010_is_governed_by_its_reformed_easter_not_its_true_taregir(self):
        """2010's true Taregir is Ա (Julian Easter Mar 22); what's actually served comes
        from the section whose OWN printed label is 04-04 -- 2010's REFORMED Easter.
        Ա's own pages (First Volume p.558) print this canon on July 23/27, dates that
        never appear in what 2010 serves; the section matched by 04-04 prints January 21
        and August 2, exactly what 2010 serves, verbatim against sacredtradition.am.
        """
        import datetime

        from dev.paschal_index import taregir_for
        from armenian_lectionary.engine import compute_armenian_lectionary

        self.assertEqual("Ա", taregir_for(2010))
        self.assertEqual(
            "Sts. Cyricus and His Mother Julitta",
            compute_armenian_lectionary(datetime.date(2010, 1, 21))["Liturgical Day"])
        self.assertEqual(
            "St. Vahan of Goghtn — Sts. Gordius, Polyeuctus and Grigoris",
            compute_armenian_lectionary(datetime.date(2010, 8, 2))["Liturgical Day"])


@requires_reference_cache
class TestSecondVolumeCyclesReproduce(unittest.TestCase):
    def test_build_reproduces_the_committed_artifact(self):
        if not os.path.exists(TRANSLATION):
            self.skipTest("grabar-ocr translation not present; the build reads it directly")
        with open(ARTIFACT, encoding="utf-8") as fh:
            committed = fh.read()
        proc = subprocess.run([sys.executable, BUILD], capture_output=True, text=True,
                              cwd=REPO)
        try:
            self.assertEqual(proc.returncode, 0,
                             f"the cycle build failed:\n{proc.stderr[-2000:]}")
            with open(ARTIFACT, encoding="utf-8") as fh:
                rebuilt = fh.read()
            self.assertEqual(
                json.loads(rebuilt), json.loads(committed),
                "dev/build_second_volume_cycles.py no longer reproduces "
                "second_volume_cycles.json. Rebuild and review the diff -- this artifact "
                "decides which readings the second-volume-cycle tier serves.")
        finally:
            if proc.returncode == 0:
                with open(ARTIFACT, "w", encoding="utf-8") as fh:
                    fh.write(committed)


if __name__ == "__main__":
    unittest.main()
