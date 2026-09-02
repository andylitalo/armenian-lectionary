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
    MAX_YEAR, MIN_YEAR, _OBSERVANCE_SEP, _canons_with_own_day, compute_armenian_lectionary,
)
from tests._catalog_expectations import text                           # noqa: E402

# What survives after the packed-companion repair, the stated year-type override,
# transcribing taregir Ē's own summer march (docs section 7d), and the TrSaintB
# table-collision override (docs section 7e, engine._TR_SAINT_ID_OVERRIDES) that closed
# the last survivor: none.
MAX_DUPLICATE_COMMEMORATIONS = 0

# Canons whose double commemoration is closed, by whichever mechanism closed it (docs
# section 7b). Named individually rather than counted, so a regression says which canon
# came back.
REPAIRED_CANONS = (
    "mark_the_bishop_pionius",           # the pre-Lent cohort case, fixed first
    "gordius_polyeuctus_and_grigoris",   # by stated override, not by own-day detection
    "hermit_sts_tryphon_barsauma",
    "andrew_the_general_and_martyrs",
    "vahan_of_goghtn",
    "eugenia_the_virgin_and_family",
    "gregory_the_theologian",
    "hermit_st_anton",                   # closed by the TrSaintB override (docs 7e)
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
        Second Volume p.574 does by hand when the year gives Tryphon room. The day it was
        given is asserted too: a drop moves a name, it does not lose one.
        """
        self.assertEqual(text("hermit_st_anton"),
                         self._day("2002-01-17")["Liturgical Day"])
        self.assertEqual(text("hermit_sts_tryphon_barsauma"),
                         self._day("2002-08-01")["Liturgical Day"])

    def test_dropping_a_middle_companion_keeps_the_rest(self):
        """2016-07-28: Vahan heads 2016-08-01, so it goes and Gordius stays.

        The result is byte-identical to the source's own fuller line for that day -- the
        repair closes a duplicate and an EXPANSION at once.
        """
        self.assertEqual(
            text("cyricus_and_his_mother") + _OBSERVANCE_SEP + text("gordius_polyeuctus_and_grigoris"),
            self._day("2016-07-28")["Liturgical Day"])

    def test_the_head_canon_is_never_dropped(self):
        """2027-07-24: Anton heads this day and stays, unaffected by the TrSaintB
        override that fixes 07-26 (docs section 7e; the override touches only that one
        civil date, not 07-24's).

        A head owns its day, its id and its readings, so letting a packing rule "fix" a
        collision by dropping the head would leave the day nameless -- not the mechanism
        used here regardless.
        """
        self.assertEqual(text("hermit_st_anton"),
                         self._day("2027-07-24")["Liturgical Day"])

    def test_the_stated_override_withdraws_a_packing(self):
        """2010/2021: Ծ (pp.586-587) keeps Cyricus alone in January.

        The canon never heads a day, so no own-day rule reaches it; the year-type states
        the packing and engine._PACKING_OVERRIDES restates it. sacredtradition.am prints
        exactly this on both days.
        """
        for iso in ("2010-01-21", "2021-01-21"):
            with self.subTest(iso):
                self.assertEqual(text("cyricus_and_his_mother"),
                                 self._day(iso)["Liturgical Day"])

    def test_the_override_does_not_reach_the_other_head(self):
        """The same canon stays packed on the Vahan day, which is where Ծ puts it.

        p.587: "2. Monday. Vahan of Goghtn, Gordius, Polyeuctus, and Grigoris." The
        override is keyed by HEAD canon, so withdrawing a packing from Cyricus cannot
        disturb Vahan's.
        """
        for iso in ("2010-08-02", "2021-08-02"):
            with self.subTest(iso):
                self.assertEqual(
                    text("vahan_of_goghtn") + _OBSERVANCE_SEP + text("gordius_polyeuctus_and_grigoris"),
                    self._day(iso)["Liturgical Day"])

    def test_the_override_does_not_reach_other_year_types(self):
        """Year-types that pack Gordius with Cyricus keep it (pp.574/582/592/597).

        These read correctly before the override; pinned so a year-type key that was too
        loose fails here rather than passing silently.
        """
        for iso in ("2005-07-28", "2008-07-24", "2016-07-28"):
            with self.subTest(iso):
                self.assertIn("Gordius", self._day(iso)["Liturgical Day"])

    def test_taregir_e_march_matches_p571(self):
        """2027 (Gregorian Easter 03-28) is taregir Ē -- source-independent, so 2027 is
        covered even with no ground truth. p.571 lays out the whole July/August pool;
        this pins the two the matcher previously got wrong.

        27 was a second Theodosius (the matcher's plural/spelling bugs); the transcribed
        march now serves what p.571 actually prints: Cyricus alone (the stated override
        withdraws Gordius, which the page attaches to Vahan on the 29th instead -- see
        engine._PACKING_OVERRIDES). 31 was the September Barlaam canon, 54 days early;
        the march now serves Athanasius/Cyril, and Gregory the Theologian.
        """
        self.assertEqual(text("cyricus_and_his_mother"),
                         self._day("2027-07-27")["Liturgical Day"])
        self.assertEqual(
            text("fathers_athanasius_and_cyril") + _OBSERVANCE_SEP + text("gregory_the_theologian"),
            self._day("2027-07-31")["Liturgical Day"])

    def test_the_table_collision_is_closed(self):
        """2027-07-26: the table's own TrSaintB["0:cyricus_and_his"] entry (real, built
        from 2005/2016 ground truth) no longer aliases onto Ē's Monday.

        p.571 gives it to Theodosius, and engine._TR_SAINT_ID_OVERRIDES (docs section 7e)
        withdraws the mined "cyricus_and_his" identity for this one (Easter, civil-date)
        pair, so the second-volume-cycle tier -- not the table -- serves it.
        """
        served = self._day("2027-07-26")
        self.assertEqual(text("theodosius_and_the_children"),
                         served["Liturgical Day"])
        self.assertEqual("second-volume-cycle", served["Source"])

    def test_the_companion_pack_is_closed(self):
        """2027-07-29: p.571 packs Gordius/Polyeuctus/Grigoris onto Vahan's day
        ("29. Thursday. Vahan of Goghtn, and Gordius, Polyeuctus, and Gregory."), but the
        second-volume-cycle tier's own schema (one saint id per date) has no way to say so
        -- unlike the validated-table tier's packing, which stores the whole line as text.
        engine._TR_SAINT_COMPANION_OVERRIDES appends the companion's catalog text without
        touching readings, which stay Vahan's (docs section 7, "the day's readings are the
        head canon's"). Gordius/Polyeuctus/Grigoris are served on no other day of 2027.
        """
        served = self._day("2027-07-29")
        self.assertEqual(
            text("vahan_of_goghtn") + _OBSERVANCE_SEP + text("gordius_polyeuctus_and_grigoris"),
            served["Liturgical Day"])
        self.assertEqual(
            ["Proverbs 7.1-7", "Ezekiel 12.17-19",
             "St. Paul's Epistle to the Romans 8.12-27", "Luke 9.23-27"],
            served["ReadingsList"])
        self.assertEqual("second-volume-cycle", served["Source"])

    def test_the_year_scan_overshoots_the_supported_range_at_both_ends(self):
        """The scan window is Heesnak to Heesnak, so it leaves the range at both edges.

        A January date sits in the PREVIOUS liturgical year, opening in the November
        below ``MIN_YEAR``; ``MAX_YEAR``'s own window closes in the November above it.
        The scan reads both through ``_compute_lectionary``, which has no range guard on
        purpose -- clamping would make a day's name depend on ``LECTIONARY_MIN_YEAR``,
        which is env-overridable by design. Both windows are asserted on the scan itself;
        only the bottom one is reachable from a served day (2001-01-22 is packed and sits
        in liturgical year 2000), because no packed day falls between Heesnak MAX_YEAR and
        the end of MAX_YEAR -- which is what keeps the unvalidated top overshoot unread.
        """
        for ly in (MIN_YEAR - 1, MAX_YEAR):
            with self.subTest(ly):
                self.assertIsInstance(_canons_with_own_day(ly), frozenset)
        self.assertEqual(
            text("cyricus_and_his_mother") + _OBSERVANCE_SEP + text("gordius_polyeuctus_and_grigoris"),
            self._day("2001-01-22")["Liturgical Day"])

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
        for iso, name, propers in (("2002-01-17", text("hermit_st_anton"), anton),
                                   ("2008-07-28", text("vahan_of_goghtn"), vahan)):
            with self.subTest(iso):
                served = self._day(iso)
                self.assertEqual(name, served["Liturgical Day"])
                self.assertEqual(propers, served["ReadingsList"])


if __name__ == "__main__":
    unittest.main()
