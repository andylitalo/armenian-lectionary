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
