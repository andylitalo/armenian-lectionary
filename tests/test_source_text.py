"""Locks the quality of the SOURCE's feast text, not the engine's fidelity to it.

Every other feast test asks whether the engine reproduces sacredtradition.am. Since
``fix/feast-name-accuracy`` the answer is yes on all 9,496 days with ground truth -- which
turns each of the source's own typos into a name the engine serves. This test closes that
gap from the other side: it runs ``dev/audit_source_anomalies``'s detectors over the
corrected source and requires them to stay silent.

That matters most on a re-fetch. ``dev/bulk_fetch.py`` can pull the corpus again at any
time, and sacredtradition.am is a live site: it can gain a day, fix a name, or introduce a
new slip. Without this, a new typo would land in the cache, rebuild into the shipped
artifacts, pass every oracle test (the engine would match the source perfectly) and reach
the client. Here it fails instead.

A failure is not necessarily a defect -- it is a string a human has not judged yet. Resolve
it either way and the test goes quiet: register a correction in ``dev/source_corrections``
if the source is wrong, or clear it by name in the audit script if it is fine.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev import audit_source_anomalies as audit                       # noqa: E402
from tests._reference_cache import requires_reference_cache           # noqa: E402


@requires_reference_cache
class TestSourceTextIsClean(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.comps = {}
        for iso, feast in audit.corrected_days().items():
            for c in audit.components(feast):
                cls.comps.setdefault(c, []).append(iso)
        cls.counts = {c: len(v) for c, v in cls.comps.items()}
        cls.words = audit.load_words()
        cls.hy = audit._hy_map()

    def _assert_clean(self, findings, what):
        self.assertEqual(
            [head for head, _ in findings][:6], [],
            f"{len(findings)} unjudged {what} in the source feast text. Judge each: "
            "register a fix in dev/source_corrections, or clear it by name in "
            "dev/audit_source_anomalies. Run that script for the full report.")

    def test_no_doubled_word(self):
        self._assert_clean(audit.detect_doubled_word(self.comps), "doubled words")

    def test_no_stray_edge_punctuation(self):
        self._assert_clean(audit.detect_edge_punctuation(self.comps),
                           "components edged with punctuation")

    def test_no_spacing_anomaly(self):
        self._assert_clean(audit.detect_spacing(self.comps), "spacing anomalies")

    def test_no_mixed_separator(self):
        self._assert_clean(audit.detect_mixed_separator(self.comps),
                           "comma-joined position labels")

    def test_no_near_duplicate_component(self):
        self._assert_clean(audit.detect_near_duplicates(self.comps, self.counts),
                           "near-duplicate components")

    def test_no_token_spelled_two_ways(self):
        self._assert_clean(audit.detect_token_variants(self.comps, self.counts),
                           "names spelled two ways")

    def test_no_unknown_word(self):
        if self.words is None:
            self.skipTest(f"no word list at {audit.WORDLIST}")
        self._assert_clean(audit.detect_unknown_words(self.comps, self.words),
                           "unrecognized words")

    def test_english_and_armenian_agree_on_years(self):
        """The strongest check here: the source stating a year twice, differently."""
        if not self.hy:
            self.skipTest("no observance_names_hy.json")
        self._assert_clean(audit.detect_digit_disagreement(self.comps, self.hy),
                           "years the English and Armenian names disagree on")

    def test_english_and_armenian_agree_on_ordinals(self):
        if not self.hy:
            self.skipTest("no observance_names_hy.json")
        self._assert_clean(audit.detect_ordinal_disagreement(self.comps, self.hy),
                           "ordinals the English and Armenian names disagree on")


if __name__ == "__main__":
    unittest.main()
