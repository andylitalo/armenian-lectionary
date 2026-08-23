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

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.audit_duplicate_commemorations import findings                # noqa: E402
from armenian_lectionary.engine import (                               # noqa: E402
    MAX_YEAR, MIN_YEAR, compute_armenian_lectionary,
)

# What survives after the packed-companion repair (docs section 7b). Two groups remain,
# each needing evidence this ratchet is not the place to settle:
#
#   * 2 -- gordius_polyeuctus_and_grigoris, packed onto BOTH its occurrences and heading
#     neither, so there is no "own day" to keep and no readings signature to tell them
#     apart. The Second Volume does speak to it, but per year-type and in both directions
#     (p.558 prints Cyricus alone and "Monday. Of Vahan of Golthen, and Gordius"; p.574
#     and p.582 print Gordius WITH Cyricus and give Vahan a day beside Eugenia), so which
#     head absorbs this canon is stated data, not a derivable rule;
#   * 2 -- the "03-28" second-volume cycle placing a canon the validated table places
#     elsewhere: hermit_st_anton on 2027-07-24 (table has it 07-26) and
#     patriarchs_barlaam_anthimus_and on 2027-07-31 (table has it in late September).
#     Easter 2027 is the only supported year of its type, so
#     build_second_volume_cycles._drop_cache_contradicted has no cache year to filter
#     either entry against. Both duplicate a HEAD canon, not a companion, which is why no
#     packing rule reaches them. A dev/build_second_volume_cycles.py question.
MAX_DUPLICATE_COMMEMORATIONS = 4

# The post-Theophany pool canons engine._drop_owned_companions un-packs where the taregir
# gave them a day of their own (docs section 7b). Named individually rather than counted,
# so a regression says which canon came back.
REPAIRED_CANONS = (
    "mark_the_bishop_pionius",           # the pre-Lent cohort case, fixed first
    "hermit_sts_tryphon_barsauma",
    "andrew_the_general_and",
    "vahan_of_goghtn",
    "eugenia_the_virgin_her",
    "gregory_the_theologian",
)


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

    def test_the_repaired_canons_stay_repaired(self):
        """A companion is packed only where its own day is taken (docs section 7b)."""
        offenders = sorted({(sid, ly) for ly, sid, _ in findings()
                            if sid in REPAIRED_CANONS})
        self.assertEqual([], offenders)


class TestUnpackingMatchesTheSource(unittest.TestCase):
    """Days the repair changed, pinned by what they must now read.

    Source-independent like the ratchet above, so 2027 is covered here too. These are the
    three shapes the repair produces, one case each.
    """

    def _day(self, iso):
        return compute_armenian_lectionary(datetime.date.fromisoformat(iso))

    def test_companion_with_its_own_day_is_dropped(self):
        """2002-01-17: Tryphon holds 2002-08-01, so Anton's day names Anton alone.

        This is what sacredtradition.am prints there ("The Hermit Saints Anton") and what
        Second Volume p.574 does by hand when the year gives Tryphon room.
        """
        self.assertEqual("The Hermit St. Anton",
                         self._day("2002-01-17")["Liturgical Day"])

    def test_dropping_a_middle_companion_keeps_the_rest(self):
        """2016-07-28: Vahan heads 2016-08-01, so it goes and Gordius stays.

        The result is byte-identical to the source's own fuller line for that day -- the
        repair closes a duplicate and an EXPANSION at once.
        """
        self.assertEqual(
            "Sts. Cyricus and His Mother Julitta — Sts. Gordius, Polyeuctus and Grigoris",
            self._day("2016-07-28")["Liturgical Day"])

    def test_the_head_canon_is_never_dropped(self):
        """2027-07-24: Anton heads this day AND holds 2027-07-26, and still stays.

        A head owns its day, its id and its readings. That this day duplicates Anton is a
        second-volume-cycle laydown question (see MAX_DUPLICATE_COMMEMORATIONS), and
        letting a packing rule "fix" it by dropping the head would leave the day nameless.
        """
        self.assertEqual("The Hermit St. Anton",
                         self._day("2027-07-24")["Liturgical Day"])

    def test_the_year_scan_spans_the_supported_range_edges(self):
        """A January date sits in the PREVIOUS liturgical year, whose window opens in the
        November before -- one year below MIN_YEAR at the bottom edge.

        The scan reads that window through ``_compute_lectionary``, which has no range
        guard on purpose. Clamping it to the supported range instead would make a day's
        name depend on ``LECTIONARY_MIN_YEAR``, which is env-overridable by design.
        """
        for year in (MIN_YEAR, MAX_YEAR):
            d = datetime.date(year, 1, 1)
            while d.year == year:
                with self.subTest(d):
                    self.assertTrue(self._day(d.isoformat())["Liturgical Day"].strip())
                d += datetime.timedelta(days=1)

    def test_the_day_keeps_the_head_canons_propers(self):
        """A drop takes a name and nothing else: the readings stay the head canon's.

        Checked against the First Volume itself (p.461), which gives each canon its own
        four readings. That the served propers are still the HEAD's -- Anton's on the day
        Tryphon left, Vahan's on the day Eugenia left -- is what makes this a name change
        rather than a day changing hands.
        """
        anton = ["Proverbs 21.15-24", "Isaiah 19.19-21",
                 "St. Paul's Epistle to the Hebrews 11.32-40", "Matthew 10.37-42"]
        vahan = ["Proverbs 7.1-7", "Ezekiel 12.17-19",
                 "St. Paul's Epistle to the Romans 8.12-27", "Luke 9.23-27"]
        for iso, name, propers in (("2002-01-17", "The Hermit St. Anton", anton),
                                   ("2008-07-28", "St. Vahan of Goghtn", vahan),
                                   ("2027-07-29", "St. Vahan of Goghtn", vahan)):
            with self.subTest(iso):
                served = self._day(iso)
                self.assertEqual(name, served["Liturgical Day"])
                self.assertEqual(propers, served["ReadingsList"])


if __name__ == "__main__":
    unittest.main()
