"""Accuracy lock over the position/eve labelling RULE itself, not the name it ends up in.

``engine._position_label`` and ``engine._eve_label`` regenerate the two components a table
key cannot hold (``build_table.unanimous_feast`` drops anything the civil years sharing a
key state differently). ``dev/verify_position_labels.py`` and ``dev/verify_eve_labels.py``
have always compared those generators against every label the source printed, and have
always printed the result as three numbers that "must be 0". Nothing asserted them, and
one of the three -- END-TO-END LOST, which those scripts themselves call the number that
matters downstream -- was not even in the exit status.

**Why the served-name tests do not already cover this.** ``test_observance_name_raw.py``
compares the SERVED name, and the served name is the union of two sources: the rule, and
whatever the validated table stored. ``engine._apply_position_label`` keeps a stored
position component verbatim -- "the validated STORED value is trusted over regeneration".
So on every day where the table stores the component, the rule could regress to a label
the source contradicts and the served name would still be right, and still pass there.

That is not a hypothetical hole, because the rule is consulted for something the served
name is not evidence of. ``_resolve_generated_text`` resolves a label to its catalogued id
by calendar COORDINATE when the day's readings are no longer its own, and a coordinate is
the rule restating itself. ``tests/test_coordinate_index.py`` is explicit that its
narrowing stays "covered by ``dev/verify_position_labels.py``/``verify_eve_labels.py``
(rule vs. source, cache-gated)". This file is what makes that sentence true: the rule's
agreement with the source is now asserted, not cited.

The classification lives in the two dev scripts, imported here, so the report and the test
can never drift -- the arrangement ``tests/test_observance_name_raw.py`` already has with
``dev/observance_discrepancy_report``.

The contracts, strongest first:

  * MISMATCH == 0 and EXTRA == 0 -- hard asserts, both directions of the rule asserting
    something the source contradicts.
  * END-TO-END LOST == 0 -- hard assert. A fasting calendar is built from exactly these
    components, so a label that does not reach the served name is lost data.
  * MISSING is a *kind*, not a budget: every label the position generator does not produce
    must be a component the engine declines on purpose (docs section 6e). The eve
    generator has no residue at all, so there MISSING == 0 is a hard assert too.
  * The sweep sizes are floors, so a thinner cache cannot quietly make all of the above
    vacuous.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev import verify_eve_labels, verify_position_labels                 # noqa: E402
from dev.observance_ids import is_declined_en                             # noqa: E402
from tests._reference_cache import requires_reference_cache               # noqa: E402

# Days where the source printed a position label and the rule printed the same one.
# Monotonic UP: it may only grow as the cache does. A floor rather than an equality so
# extending the cache reports its true number instead of failing on arithmetic.
POSITION_MATCHED_FLOOR = int(os.environ.get("POSITION_MATCHED_FLOOR", "6294"))

# Source position labels that reach the SERVED name, from the rule or from the table.
# Monotonic UP, same reasoning. Excludes the declared declines counted separately.
POSITION_SERVED_FLOOR = int(os.environ.get("POSITION_SERVED_FLOOR", "6238"))

# Eve components, matched by the rule and served end-to-end. Both currently 338/338 --
# every eve family is implemented, so these two numbers are the same one.
EVE_MATCHED_FLOOR = int(os.environ.get("EVE_MATCHED_FLOOR", "338"))


@requires_reference_cache
class TestPositionLabelRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = verify_position_labels.collect()

    def test_no_label_contradicts_the_source(self):
        """The rule never prints a position label the source printed differently."""
        bad = self.data["mismatch"]
        self.assertEqual(
            [], bad[:10],
            f"{len(bad)} days: engine._position_label contradicts the source. A wrong "
            "label is worse than none -- it is persisted downstream, and the coordinate "
            "index is built from this rule. Run dev/verify_position_labels.py -v.")

    def test_no_label_is_invented(self):
        """The rule never labels a day the source left unlabelled."""
        bad = self.data["extra"]
        self.assertEqual(
            [], bad[:10],
            f"{len(bad)} days: engine._position_label prints a label where the source "
            "prints none; a _POSITION_FAMILIES window has grown too wide. Run "
            "dev/verify_position_labels.py -v.")

    def test_every_source_label_reaches_the_served_name(self):
        """END-TO-END: the table and the rule together lose nothing the source states."""
        lost = self.data["served_lost"]
        self.assertEqual(
            [], lost[:10],
            f"{len(lost)} source position labels never reach the served name. This is the "
            "number that matters downstream -- a fasting calendar is built from exactly "
            "these components.")

    def test_every_unproduced_label_is_a_declared_decline(self):
        """The generator's residue is a registered decision, not an accumulating gap.

        The rule does not produce every label the source prints, and that is fine: the
        validated table supplies the rest (which is what the end-to-end test above
        measures). What must not happen is the residue quietly acquiring a new KIND of
        label -- so this asserts what is in it rather than how big it is. Currently the
        whole residue is the undifferentiated "Fast day" marker, declined on every day
        that has another name (docs section 6e).
        """
        undeclared = [(iso, src) for iso, src in self.data["missing"]
                      if not is_declined_en(src)]
        self.assertEqual(
            [], undeclared[:10],
            f"{len(undeclared)} days: the source states a position label the rule does "
            "not produce and that is not a declared decline. Either implement the family "
            "in engine._POSITION_FAMILIES or register the decline in "
            "dev/observance_ids._DECLINED_FAST_MARKERS_EN.")

    def test_the_sweep_did_not_shrink(self):
        """A thinner cache must not quietly weaken every assertion above."""
        self.assertGreaterEqual(
            self.data["matched"], POSITION_MATCHED_FLOOR,
            f"only {self.data['matched']} days had a source position label the rule also "
            f"produced (floor {POSITION_MATCHED_FLOOR})")
        self.assertGreaterEqual(
            self.data["served_ok"], POSITION_SERVED_FLOOR,
            f"only {self.data['served_ok']} source position labels were checked "
            f"end-to-end (floor {POSITION_SERVED_FLOOR})")


@requires_reference_cache
class TestEveLabelRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = verify_eve_labels.collect()

    def test_no_eve_contradicts_the_source(self):
        bad = self.data["mismatch"]
        self.assertEqual(
            [], bad[:10],
            f"{len(bad)} days: engine._eve_label contradicts the source. Run "
            "dev/verify_eve_labels.py -v.")

    def test_no_eve_is_missing(self):
        """Unlike the position rule, this one has no declared residue.

        Every eve family is implemented, so a label the source states and the rule does
        not produce is a bug rather than a decision -- there is nothing to ratchet.
        """
        bad = self.data["missing"]
        self.assertEqual(
            [], bad[:10],
            f"{len(bad)} days: the source states an eve engine._eve_label does not "
            "produce; a family is missing from engine._EVE_FAMILIES.")

    def test_no_eve_is_invented(self):
        bad = self.data["extra"]
        self.assertEqual(
            [], bad[:10],
            f"{len(bad)} days: engine._eve_label calls a day an eve and the source does "
            "not.")

    def test_every_source_eve_reaches_the_served_name(self):
        """END-TO-END: an eve opens a fast, so losing one is losing fasting-calendar data."""
        lost = self.data["served_lost"]
        self.assertEqual(
            [], lost[:10],
            f"{len(lost)} source eve components never reach the served name.")

    def test_the_sweep_did_not_shrink(self):
        self.assertGreaterEqual(
            self.data["matched"], EVE_MATCHED_FLOOR,
            f"only {self.data['matched']} eve components were checked against the rule "
            f"(floor {EVE_MATCHED_FLOOR})")
        self.assertGreaterEqual(
            self.data["served_ok"], EVE_MATCHED_FLOOR,
            f"only {self.data['served_ok']} eve components were checked end-to-end "
            f"(floor {EVE_MATCHED_FLOOR})")


if __name__ == "__main__":
    unittest.main()
