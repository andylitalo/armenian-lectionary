"""Accuracy lock over the raw ARMENIAN feast name.

``tests/test_feast_name_raw.py`` does this for English and holds it at 9,496 of 9,496
days. Armenian had no equivalent, and the gap was not academic: consolidating display text
onto the id-keyed observance catalog (#17/#18) changed ``language="hy"`` on 145 days and
regressed it on ~118 of them, and every test in the suite stayed green. The old flat map
keyed *whole composite English strings* to Armenian; the catalog keys single components,
so wherever the source's Armenian segments differently from its English the component-wise
rejoin silently dropped the richer Armenian form. Nothing was watching.

This test watches. Classification lives in ``dev/hy_discrepancy`` so the test and the
report can never drift, mirroring how the English test delegates to
``dev/feast_discrepancy_report``.

Why these are ratchets and not zeroes
-------------------------------------
The English test can assert CONTRADICTIONS == 0 because every deliberate departure from
the source is registered in ``dev/source_corrections`` and folded on both sides before
comparing. Armenian has no such registry, and the residue is not all engine defect. At the
time of writing the 12 contradictions are:

  * 7 days where the shipped table's commemoration enumerates a different companion list
    than the year the cache sampled -- the same class ``canonical_commem`` folds away on
    the English side, which has no Armenian analogue;
  * 1 deliberate correction, where the source's own Armenian carries a wrong ordinal
    (``Ա`` for ``Բ`` Sunday after Pentecost) that English pins as wrong;
  * 2 word-form variants (``Առաջաւորի``/``Առաջաւորաց``) where the engine serves the
    source's dominant spelling, but which the DOMINANT_FORM classifier is deliberately too
    crude to group -- it compares spacing and case, not morphology;
  * 2 single-day punctuation differences.

So the contract is "no NEW divergence", enforced by floors that may only move toward zero.
Lower them whenever a fix lands; never raise one to make a change pass.

DOMINANT_FORM has a ceiling too, for a different reason. Those days are correct -- the
source spells one name several ways and we serve the one it uses most -- but a RISING count
means the source grew a new spelling that nobody has looked at, which is worth knowing.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.hy_discrepancy import collect, counts                          # noqa: E402
from tests._reference_cache import requires_reference_cache_hy          # noqa: E402

# Days where the engine emits an Armenian component the source does not have.
# Monotonic DOWN. The target is 0, as on the English side.
HY_CONTRADICTION_CEILING = int(os.environ.get("HY_CONTRADICTION_CEILING", "12"))

# Days where the engine drops an Armenian component the source states. Monotonic DOWN.
HY_OMISSION_CEILING = int(os.environ.get("HY_OMISSION_CEILING", "2"))

# Days carrying the right components in a different order. Monotonic DOWN.
HY_ORDER_CEILING = int(os.environ.get("HY_ORDER_CEILING", "1"))

# Days where the source spells a name several ways and we serve its dominant form. Correct,
# but monotonic DOWN anyway: a rise means a new unreviewed spelling appeared in the source.
HY_DOMINANT_FORM_CEILING = int(os.environ.get("HY_DOMINANT_FORM_CEILING", "5"))

# Days whose Armenian name matches the source exactly (under the registered orthography
# reversal). Monotonic UP.
HY_EXACT_FLOOR = int(os.environ.get("HY_EXACT_FLOOR", "413"))

# Days with a source Armenian name to compare against. Guards against a shrinking cache
# silently weakening every assertion above.
HY_EXPECTED_COMPARED = int(os.environ.get("HY_EXPECTED_COMPARED_DAYS", "433"))


@requires_reference_cache_hy
class TestRawArmenianFeastName(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = collect()
        cls.tally = counts(cls.data)

    def _sample(self, kind):
        return [(f["iso"], f["contradictions"], f["omissions"])
                for f in self.data["findings"] if f["kind"] == kind][:10]

    def test_contradictions_within_ratchet(self):
        n = self.tally["CONTRADICTION"]
        self.assertLessEqual(
            n, HY_CONTRADICTION_CEILING,
            f"{n} days emit an Armenian component the source does not have (ceiling "
            f"{HY_CONTRADICTION_CEILING}); run `python dev/hy_discrepancy.py --list`. "
            f"First few: {self._sample('CONTRADICTION')}")

    def test_omissions_within_ratchet(self):
        n = self.tally["OMISSION"]
        self.assertLessEqual(
            n, HY_OMISSION_CEILING,
            f"{n} days drop an Armenian component the source states (ceiling "
            f"{HY_OMISSION_CEILING}); run `python dev/hy_discrepancy.py --list`. "
            f"First few: {self._sample('OMISSION')}")

    def test_ordering_within_ratchet(self):
        n = self.tally["ORDER"]
        self.assertLessEqual(
            n, HY_ORDER_CEILING,
            f"{n} days serve the right Armenian components in the wrong order (ceiling "
            f"{HY_ORDER_CEILING}); run `python dev/hy_discrepancy.py --list`")

    def test_dominant_form_within_ratchet(self):
        n = self.tally["DOMINANT_FORM"]
        self.assertLessEqual(
            n, HY_DOMINANT_FORM_CEILING,
            f"{n} days serve a dominant spelling where the source varies (ceiling "
            f"{HY_DOMINANT_FORM_CEILING}); these are not defects, but a rise means the "
            "source grew a spelling nobody has reviewed -- run "
            "`python dev/audit_hy_variants.py`")

    def test_exact_match_floor(self):
        n = self.data["exact"]
        self.assertGreaterEqual(
            n, HY_EXACT_FLOOR,
            f"only {n} days match the source's Armenian exactly (floor {HY_EXACT_FLOOR})")

    def test_oracle_did_not_shrink(self):
        self.assertGreaterEqual(
            self.data["compared"], HY_EXPECTED_COMPARED,
            f"only {self.data['compared']} days had a source Armenian name to compare "
            f"(expected >= {HY_EXPECTED_COMPARED}); a thinner cache quietly weakens every "
            "assertion in this file")

    def test_every_day_is_accounted_for(self):
        """No day escapes classification -- the sum must close."""
        classified = self.data["exact"] + len(self.data["findings"])
        self.assertEqual(
            classified, self.data["compared"],
            "some compared days were neither exact nor recorded as a finding")


if __name__ == "__main__":
    unittest.main()
