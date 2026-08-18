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

Armenian also has the second half of that now. The Tonats'oyts packs several First Volume
canons onto one line when the taregir leaves few days for them, and its preface (Sixth)
says it prints "only the name of the first saints ... for the sake of brevity". Splitting
those lines into one component per canon gave the Armenian both halves of what English gets
from ``canonical_commem``: the glued source spelling folds through ``approved_hy``, and a
canon the engine serves from the same declared pool reports as EXPANSION rather than as a
contradiction. 6 -> 3.

The 3 that remain are all source-side, and all accepted:

  * 2 word-form variants (``Առաջաւորի``/``Առաջաւորաց``, ``Ծննդեան``/``Ս. Ծննդեան``) where
    the engine serves the source's dominant spelling, but which the DOMINANT_FORM
    classifier is deliberately too crude to group -- it compares spacing and case, not
    morphology. Neither minority spelling is in the TSV to correct: a row holds ONE
    ``source_hy``, sampled from one day, and these are what the source printed on another.
    The engine serves the source's own dominant spelling in both cases, so it is the source
    disagreeing with itself, not a defect -- see docs/feast-name-corrections.md section 8;
  * 1 segmentation difference (2005-01-01), where the source's Armenian glues ``Կաղանդ.
    տարեմուտ`` (New Year's Day) onto the saints that follow while the English carries it
    with the day count. Jan 1 now serves that as its own observance
    (``blessing_of_the_pomegranates``, docs section 9), which fixed the other two Jan 1 days
    outright; this one stays because the source glues the New Year to the SAINTS here rather
    than printing it as its own component, and a row holds one source_hy, not two.

(The deliberate ``Ա``-for-``Բ`` Sunday-after-Pentecost ordinal correction used to be a
twelfth. It is now folded, along with ``Սկիզբն պահոց`` -> ``Սկիզբն շաբաթական պահոց``.)

So the contract is "no NEW divergence", enforced by floors that may only move toward zero.
Lower them whenever a fix lands; never raise one to make a change pass. A deliberate
Armenian correction is not an exception to that -- register it in ``approved_hy``, where
the fold picks it up and the ceiling goes DOWN.

CONTRADICTION/OMISSION moved deliberately once more, for the Wednesday/Friday Fast split
and the named-fast day-count relabeling (docs/feast-name-corrections.md section 10) --
the first time either has moved for a reason other than an unreviewed source change or a
newly-registered fold. ``ground_truth_hy_fixes`` only folds a SOURCE string into its
``approved_hy``; it has nothing to fold when the source's own text is the same
undifferentiated ``Պահք`` on hundreds of days and the served text now differs by weekday
or by which named fast the day falls in, so every date this change touches shows up here
as a literal divergence from the raw scrape rather than a registered correction:

  * 16 new CONTRADICTION days -- the engine now serves ``Չորեքշաբթիի/Ուրբաթի պահք`` (the
    ordinary-time weekday split) or one of three fixed named-fast phrases (``Եղիական
    պահք``, ``Սուրբ Գրիգոր Լուսավորչի պահք``, ``Սուրբ Հակոբի պահք``, supplied directly,
    not per-day ordinals) the source's Armenian does not have -- including the
    Illuminator fast's days, which used to fold the source's own per-day ordinal and now
    serve the fixed phrase instead, by deliberate choice (section 10 explicitly overrides
    section 5's conclusion for this one fast).
  * 17 new OMISSION days -- the source's Armenian states a bare ``Պահք`` the engine no
    longer serves at all: Holy Week (already named ``Աւագ ...``), the Fast of Assumption
    ferias (already named ``Դ օր Վերափոխման`` etc.), and a handful of Eastertide Wed/Fri
    days the source marks ``Պահք`` in Armenian with no English "Fast day" counterpart at
    all (a pre-existing English/Armenian asymmetry this change did not create, only
    exposed by no longer keeping the redundant marker anywhere).

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
# Monotonic DOWN, except for the +16 documented above -- see
# docs/feast-name-corrections.md section 10.
HY_CONTRADICTION_CEILING = int(os.environ.get("HY_CONTRADICTION_CEILING", "19"))

# Days where the engine drops an Armenian component the source states. Monotonic DOWN,
# except for the +17 documented above -- see docs/feast-name-corrections.md section 10.
HY_OMISSION_CEILING = int(os.environ.get("HY_OMISSION_CEILING", "21"))

# Days carrying the right components in a different order. Monotonic DOWN.
HY_ORDER_CEILING = int(os.environ.get("HY_ORDER_CEILING", "1"))

# Days where the source states a component the engine deliberately does not serve. Exactly
# the two cached Jan 1 days before 2015 on which sacredtradition.am prints "Կաղանդ.
# տարեմուտ" -- a civil New Year note the 1915 Tonatsoyts does not carry (docs section 9).
# An EQUALITY: a decline is excluded from the omission count by construction, so nothing
# else would notice it spreading to days it was never meant to cover.
HY_DECLINED_DAYS = int(os.environ.get("HY_DECLINED_DAYS", "2"))

# Days where the source names one canon of a packed pool and the engine serves others from
# the same pool. Correct as served: the Second Volume prints only the first saints "for the
# sake of brevity" and its preface (Sixth) says to celebrate the companions the First Volume
# sets down. Monotonic DOWN anyway: a rise means a new packing nobody has looked at.
HY_EXPANSION_CEILING = int(os.environ.get("HY_EXPANSION_CEILING", "4"))

# Days where the source spells a name several ways and we serve its dominant form. Correct,
# but monotonic DOWN anyway: a rise means a new unreviewed spelling appeared in the source.
HY_DOMINANT_FORM_CEILING = int(os.environ.get("HY_DOMINANT_FORM_CEILING", "4"))

# Days identical to the source except that a catalog entry's internal break uses the
# catalog's own delimiter rather than the component separator. Monotonic DOWN, but only
# reachable by a source change: these are correct as served.
#
# It went 6 -> 7 once, the single exception the "never raise a ceiling" rule allows, because
# nothing got worse: 2002-04-07 MOVED here out of CONTRADICTION when octave_of_easter_new's
# internal break was normalized to _INTERNAL_SEP. It is back down to 5 now that Jan 1's
# "Կաղանդ. տարեմուտ" is its own observance instead of a note glued inside the position
# label's Armenian (docs section 9).
HY_INTERNAL_DELIMITER_CEILING = int(
    os.environ.get("HY_INTERNAL_DELIMITER_CEILING", "5"))

# Days whose Armenian name matches the source byte for byte (under the registered
# orthography reversal). Monotonic UP.
#
# Note this counts BYTE equality, so the internal-delimiter days above are excluded from it
# even though their text is identical. exact + INTERNAL_DELIMITER is the "same words" number
# and is what moves when a real fix lands: 409 + 6 = 415.
#
# The floor is 379 rather than the 412 it was before the Wednesday/Friday Fast split and
# named-fast relabeling (docs/feast-name-corrections.md section 10): 33 days move out of
# "exact" and into CONTRADICTION/OMISSION above by deliberate choice, not regression --
# see that section for the day-counts.
HY_EXACT_FLOOR = int(os.environ.get("HY_EXACT_FLOOR", "379"))

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

    def test_declines_are_exactly_the_declared_days(self):
        n = self.tally["DECLINED"]
        self.assertEqual(
            n, HY_DECLINED_DAYS,
            f"{n} days drop a component the engine declines to serve, expected exactly "
            f"{HY_DECLINED_DAYS}. A decline is excluded from the omission count by "
            "construction, so a change either way means "
            "observance_ids._DECLINED_SOURCE_HY now covers days it should not, or has "
            "stopped covering days it should.")

    def test_expansions_within_ratchet(self):
        n = self.tally["EXPANSION"]
        self.assertLessEqual(
            n, HY_EXPANSION_CEILING,
            f"{n} days expand the Second Volume's brevity into more First Volume canons "
            f"than the source printed (ceiling {HY_EXPANSION_CEILING}); these are not "
            "defects, but a rise means a packing nobody has reviewed -- run "
            "`python dev/hy_discrepancy.py --list`")

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
