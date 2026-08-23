"""A canon is kept once per liturgical year -- source-INDEPENDENT, so 2027 is covered.

The Tonats'oyts lays each saint's canon down once per annual cycle. An observance id
served on two days of the same liturgical year is therefore a name the engine puts on a
day the book does not.

No other test can see this, and the reason is structural rather than an oversight. Every
name test compares the engine to sacredtradition.am **one day at a time**, and a duplicate
is invisible that way: the packed day is a declared EXPANSION -- the engine naming
companion canons the Second Volume abbreviated away, which its preface (Sixth) instructs
-- and the companion's own day matches the source byte for byte. Neither day is wrong
alone. Only the pair is.

Being source-independent is also what lets this reach **2027**, whose 365 cached days are
empty because sacredtradition.am publishes nothing for it. Four of the findings this
ratchet holds are 2027-only, and no oracle test can assert anything about them.

The ratchet is an upper bound, not an equality, for the usual reason: a change that closes
a duplicate should pass, and one that opens a duplicate should fail. When it drops, lower
it -- ``dev/audit_duplicate_commemorations.py --list`` prints the survivors with the
source text beside each occurrence.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.audit_duplicate_commemorations import findings                # noqa: E402

# What survives after the Mark/Pionius repair (docs section 7b). Three groups remain, each
# needing evidence this ratchet is not the place to settle:
#
#   * 17 -- a packed companion that also holds its own day, where the packing is stored in
#     lectionary_data.json / saint_schedule.json against a liturgical COORDINATE shared by
#     civil years that disagree about it. Dropping it needs a per-date overlay, not an
#     artifact edit;
#   *  2 -- gordius_polyeuctus_and_grigoris, packed onto BOTH its occurrences and heading
#     neither, so there is no "own day" to keep and no readings signature to tell them
#     apart;
#   *  1 -- patriarchs_barlaam_anthimus_and on 2027-07-31, which is not a packing at all:
#     the second-volume-cycle tier lays a September canon into the July pool, eight weeks
#     from the coordinate it holds in all 26 cached years.
MAX_DUPLICATE_COMMEMORATIONS = 20


class TestDuplicateCommemorations(unittest.TestCase):

    def test_no_new_duplicate_commemoration(self):
        found = findings()
        detail = "\n".join(
            f"  LY{ly} {sid}: {', '.join(d.isoformat() for d in days)}"
            for ly, sid, days in found)
        self.assertLessEqual(
            len(found), MAX_DUPLICATE_COMMEMORATIONS,
            f"{len(found)} canons kept twice in one liturgical year, over the "
            f"{MAX_DUPLICATE_COMMEMORATIONS} this ratchet allows:\n{detail}")

    def test_ratchet_is_tight(self):
        """The bound tracks reality, so a repair cannot quietly stop counting."""
        self.assertEqual(
            len(findings()), MAX_DUPLICATE_COMMEMORATIONS,
            "duplicates changed; if this is a repair, lower "
            "MAX_DUPLICATE_COMMEMORATIONS to the new count")

    def test_the_repaired_canon_stays_repaired(self):
        """Mark/Pionius is packed only where its own day is taken (docs section 7b)."""
        offenders = [ly for ly, sid, _ in findings() if sid == "mark_the_bishop_pionius"]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
