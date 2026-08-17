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
comparing. Armenian now has such a registry too -- ``ground_truth_hy_fixes``, projected
from the ``approved_hy`` column -- and ``hy_discrepancy.source_feast`` folds it, so a
reviewed Armenian correction no longer reads as a defect. That is what took the count from
12 to 11 and the exact floor from 407 to 409; it was not expressible while ``approved_hy``
was an override filled on 3 rows of 397 rather than a decision stated on every one.

The residue is still not all engine defect. The 11 contradictions are:

  * 7 days where the shipped table's commemoration enumerates a different companion list
    than the year the cache sampled -- the same class ``canonical_commem`` folds away on
    the English side, which has no Armenian analogue;
  * 2 word-form variants (``Առաջաւորի``/``Առաջաւորաց``) where the engine serves the
    source's dominant spelling, but which the DOMINANT_FORM classifier is deliberately too
    crude to group -- it compares spacing and case, not morphology;
  * 2 single-day punctuation differences.

(The deliberate ``Ա``-for-``Բ`` Sunday-after-Pentecost ordinal correction used to be a
twelfth. It is now folded, along with ``Սկիզբն պահոց`` -> ``Սկիզբն շաբաթական պահոց``.)

So the contract is "no NEW divergence", enforced by floors that may only move toward zero.
Lower them whenever a fix lands; never raise one to make a change pass. A deliberate
Armenian correction is not an exception to that -- register it in ``approved_hy``, where
the fold picks it up and the ceiling goes DOWN.

DOMINANT_FORM and INTERNAL_DELIMITER have ceilings too, for a different reason. Those days
are correct as served -- the source spells one name several ways and we serve the one it
uses most; or its Armenian glues a trailing note onto a name whose English has no such
piece, and the catalog keeps the text while changing the delimiter. Neither is a defect,
but a RISING count means the source grew a spelling or a glued note that nobody has looked
at, which is worth knowing.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.hy_discrepancy import collect, counts                          # noqa: E402
from tests._reference_cache import requires_reference_cache_hy          # noqa: E402

# Days where the engine emits an Armenian component the source does not have.
# Monotonic DOWN. The target is 0, as on the English side.
HY_CONTRADICTION_CEILING = int(os.environ.get("HY_CONTRADICTION_CEILING", "11"))

# Days where the engine drops an Armenian component the source states. Monotonic DOWN.
HY_OMISSION_CEILING = int(os.environ.get("HY_OMISSION_CEILING", "2"))

# Days carrying the right components in a different order. Monotonic DOWN.
HY_ORDER_CEILING = int(os.environ.get("HY_ORDER_CEILING", "1"))

# Days where the source spells a name several ways and we serve its dominant form. Correct,
# but monotonic DOWN anyway: a rise means a new unreviewed spelling appeared in the source.
HY_DOMINANT_FORM_CEILING = int(os.environ.get("HY_DOMINANT_FORM_CEILING", "5"))

# Days identical to the source except that a catalog entry's internal break uses the
# catalog's own delimiter rather than the component separator. Monotonic DOWN, but only
# reachable by a source change: these are correct as served.
HY_INTERNAL_DELIMITER_CEILING = int(
    os.environ.get("HY_INTERNAL_DELIMITER_CEILING", "6"))

# Days whose Armenian name matches the source byte for byte (under the registered
# orthography reversal). Monotonic UP.
#
# Note this counts BYTE equality, so the internal-delimiter days above are excluded from it
# even though their text is identical. exact + INTERNAL_DELIMITER is the "same words" number
# and is what moves when a real fix lands: 409 + 6 = 415.
#
# The floor is 409 rather than the 410 a full cache now reports: 2 of the 3 days gained
# since it was set at 407 come from folding the registered Armenian corrections, which is
# reproducible anywhere, and the third from the cache growing 433 -> 435 days, which is not.
HY_EXACT_FLOOR = int(os.environ.get("HY_EXACT_FLOOR", "409"))

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

    def test_internal_delimiter_within_ratchet(self):
        n = self.tally["INTERNAL_DELIMITER"]
        self.assertLessEqual(
            n, HY_INTERNAL_DELIMITER_CEILING,
            f"{n} days differ from the source only by the catalog's internal delimiter "
            f"(ceiling {HY_INTERNAL_DELIMITER_CEILING}); a rise means the source glued a "
            "new trailing note onto a name, which is worth a look")

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

    def test_no_entry_serves_a_minority_spelling(self):
        """Where the source spells a name several ways, ship the one it uses most.

        dev/fetch_translations.py pairs each English name with the Armenian of ONE
        representative day, so a name the source spells three ways ships whichever the
        pairing happened to sample. That is a coin flip, and it landed wrong once: the
        Presentation of the Theotokos shipped 'ս.Աստուածածնի' -- lowercase, no space after
        the abbreviation dot -- on every Nov 21, because that 1-of-7 day was the sample.

        Asserting the audit rather than pinning individual strings: this covers every entry,
        including names nobody has looked at yet, and it keeps working after a re-fetch
        resamples the cache.
        """
        from dev.audit_hy_variants import minority_variants
        findings = [(sid, shipped, majority)
                    for sid, shipped, _n, majority, _m, _all in minority_variants()]
        self.assertEqual(
            findings[:5], [],
            f"{len(findings)} catalog entr(y/ies) serve a minority Armenian spelling; "
            "run `python dev/audit_hy_variants.py` for the witness counts")


if __name__ == "__main__":
    unittest.main()
