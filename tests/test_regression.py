"""Accuracy/coverage lock over all cached ground truth.

Mirrors dev/compare_app.py but as hard assertions: the runtime engine must never
emit a WRONG table hit, and coverage may only ratchet upward.
"""

import datetime
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all  # noqa: E402
from dev.source_corrections import apply_cohort_corrections  # noqa: E402
from lectionary import compute_armenian_lectionary  # noqa: E402

# The structurally-validated tiers: a mismatch here breaks the strict-shipping
# 0-wrong contract. The generative/resolved tiers are labeled best-guesses,
# tracked separately and NOT bound by 0-wrong. first-volume-cohort ships the
# Tōnats'oyts First-Volume propers directly (source-authoritative).
VALIDATED = {"validated-table", "validated-composite", "first-volume-cohort"}


def _expected(res, readings):
    """Cache readings normalized for comparison: on a first-volume-cohort day the engine
    serves the source verse-ranges, so apply the reviewed source-vs-cache corrections to
    the oracle first (scoped to that tier)."""
    if res["Source"] == "first-volume-cohort":
        return apply_cohort_corrections(list(readings))
    return list(readings)

# Current baseline; regressions below this fail. Overridable via env so a
# pre-backfill checkout (smaller cache) can lower it without editing source.
# Counts VALIDATED-tier exact matches only (the provably-safe core).
COVERAGE_RATCHET = int(os.environ.get("COVERAGE_RATCHET", "9392"))


class TestRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_no_wrong_full_accuracy_and_coverage(self):
        validated_exact = validated_wrong = other = reference = 0
        for iso, day in self.days.items():
            if not day["readings"] and not day["feast"]:
                continue
            reference += 1
            res = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
            match = res["ReadingsList"] == _expected(res, day["readings"])
            if res["Source"] in VALIDATED:
                if match:
                    validated_exact += 1
                else:
                    validated_wrong += 1
            else:
                other += 1

        # Hard invariant: the validated tier NEVER ships a wrong reading.
        self.assertEqual(validated_wrong, 0,
                         "engine produced a wrong VALIDATED reading")
        # Coverage ratchet on the validated core: gains pass, regressions fail.
        self.assertGreaterEqual(validated_exact, COVERAGE_RATCHET)
        # No silent data loss: every reference day was processed.
        self.assertEqual(validated_exact + validated_wrong + other, reference)


class TestCocelebrationResolvers(unittest.TestCase):
    """Locks the Feb-13 (PrLE) and Nov-21 (HEB band) co-celebration recovery."""

    def test_presentation_eve_feb13_validated(self):
        # A recovered Presentation eve (Feb 13): shipped VALIDATED via the PrLE
        # Easter-offset keyspace, exact-matching the ground-truth cache.
        res = compute_armenian_lectionary(datetime.date(2002, 2, 13))
        self.assertEqual(res["Source"], "validated-table")
        self.assertTrue(res["ReadingsList"])
        self.assertEqual(res["Season"],
                         "Eve of the Presentation of the Lord")

    def test_presentation_theotokos_nov21_validated(self):
        # A non-collision Presentation-of-the-Theotokos (Nov 21) co-celebration:
        # shipped VALIDATED via the embedded proper ++ movable-slot composite.
        res = compute_armenian_lectionary(datetime.date(2005, 11, 21))
        self.assertEqual(res["Source"], "validated-composite")
        self.assertTrue(res["ReadingsList"])

    def test_nov21_advlen46_collision_recovered(self):
        # The three Heesnak-Sunday collision years (adv_len == 46, Nov 21 IS the
        # Advent Sunday) resolve via the Tonats'oyts co-celebration rule: the proper
        # ++ the "Eleventh Sunday after the Holy Cross" (band-47-validated) readings.
        # Exact-matches the ground-truth cache; see
        # docs/sources/tonatsooyts-presentation-theotokos.md.
        expected_tail = [
            "Isaiah 29.11-20",
            "St. Paul's Epistle to the Philippians 4.8-23",
            "Luke 11.1-13",
        ]
        ref_dir = os.path.join(os.path.dirname(__file__), os.pardir,
                               "dev", "reference_data")
        for year in (2004, 2010, 2021):
            res = compute_armenian_lectionary(datetime.date(year, 11, 21))
            self.assertEqual(res["Source"], "validated-composite",
                             f"{year}-11-21 should ship validated-composite")
            self.assertEqual(res["ReadingsList"][-3:], expected_tail,
                             f"{year}-11-21 tail should be the 11th Sunday readings")
            with open(os.path.join(ref_dir, f"{year}-11-21.json")) as fh:
                gt = json.load(fh)["readings"]
            self.assertEqual(res["ReadingsList"], gt,
                             f"{year}-11-21 should exact-match ground truth")


class TestLeapSummerParity(unittest.TestCase):
    """Locks the Second-Volume leap-parity summer split: the same Easter date (03-27)
    ships a distinct saint on the shared civil date in a leap vs a non-leap year, per the
    documented ՍՌ rubric. Before the split the drop-guard had to withhold both, leaving the
    days best-effort; now each ships exact from the cycle tier."""

    def _readings(self, y, m, d):
        ref = os.path.join(os.path.dirname(__file__), os.pardir, "dev",
                           "reference_data", f"{y:04d}-{m:02d}-{d:02d}.json")
        with open(ref) as fh:
            return json.load(fh)["readings"]

    def test_2005_common_vs_2016_leap_diverge_and_match(self):
        # 2005 (common) and 2016 (leap) share Gregorian Easter 03-27.
        for y, iso_days in ((2005, ((7, 23), (7, 30))), (2016, ((7, 23), (7, 30)))):
            for m, d in iso_days:
                res = compute_armenian_lectionary(datetime.date(y, m, d))
                self.assertEqual(res["Source"], "second-volume-cycle",
                                 f"{y}-{m:02d}-{d:02d} should ship from the cycle tier")
                self.assertEqual(res["ReadingsList"], list(self._readings(y, m, d)),
                                 f"{y}-{m:02d}-{d:02d} should exact-match ground truth")
        # The first summer Saturday genuinely differs by leap parity (Peter vs Athanasius).
        self.assertNotEqual(
            compute_armenian_lectionary(datetime.date(2005, 7, 23))["ReadingsList"],
            compute_armenian_lectionary(datetime.date(2016, 7, 23))["ReadingsList"])


class TestWinterMarch(unittest.TestCase):
    """Locks the post-Nativity winter march: the long-window (2011) tail saints that the
    generative laydown mis-placed now ship exact from the cycle tier."""

    def _readings(self, y, m, d):
        ref = os.path.join(os.path.dirname(__file__), os.pardir, "dev",
                           "reference_data", f"{y:04d}-{m:02d}-{d:02d}.json")
        with open(ref) as fh:
            return json.load(fh)["readings"]

    def test_2011_winter_tail_saints_exact(self):
        # Cyprian / Athenogenes / Forefathers / Thaddeus, previously generative misses.
        for m, d in ((1, 31), (2, 1), (2, 3), (2, 12)):
            res = compute_armenian_lectionary(datetime.date(2011, m, d))
            self.assertEqual(res["Source"], "second-volume-cycle",
                             f"2011-{m:02d}-{d:02d} should ship from the cycle tier")
            self.assertEqual(res["ReadingsList"], list(self._readings(2011, m, d)),
                             f"2011-{m:02d}-{d:02d} should exact-match ground truth")


def _ref_readings(y, m, d):
    ref = os.path.join(os.path.dirname(__file__), os.pardir, "dev",
                       "reference_data", f"{y:04d}-{m:02d}-{d:02d}.json")
    with open(ref) as fh:
        return json.load(fh)["readings"]


class TestSummerSourceMarch(unittest.TestCase):
    """Locks the source-derived per-canon summer marches (Tonatsoyts Second Volume canons
    Ր and Թ) that replace the truncated generic sequence. These are the cross-validatable
    saint days the disagreements report mis-labeled as unpredictable tail saints; each ships
    exact from the cycle tier now that the full/compressed canon order is transcribed and
    keyed by the Gregorian Easter its taregir-years actually query."""

    def test_canon_R_08_05_eugenios(self):
        # Cluster 1 -- taregir Ր (Greg Easter 03-31): the full 17-saint march lands
        # Eugenios/Makarios/Valerian on 08-05, cross-validated across 2002/2013/2024.
        for y in (2002, 2013, 2024):
            res = compute_armenian_lectionary(datetime.date(y, 8, 5))
            self.assertEqual(res["Source"], "second-volume-cycle",
                             f"{y}-08-05 should ship from the cycle tier")
            self.assertEqual(res["ReadingsList"], list(_ref_readings(y, 8, 5)),
                             f"{y}-08-05 should exact-match ground truth")

    def test_canon_T_andrew_adrian(self):
        # Cluster 2 -- taregir Թ (Greg Easter 04-05): the COMPRESSED march lands Andrew the
        # General on 08-04 and Adrian on 08-06, cross-validated across 2015/2026.
        for y in (2015, 2026):
            for (m, d) in ((8, 4), (8, 6)):
                res = compute_armenian_lectionary(datetime.date(y, m, d))
                self.assertEqual(res["Source"], "second-volume-cycle",
                                 f"{y}-{m:02d}-{d:02d} should ship from the cycle tier")
                self.assertEqual(res["ReadingsList"], list(_ref_readings(y, m, d)),
                                 f"{y}-{m:02d}-{d:02d} should exact-match ground truth")

    def test_canon_ChVo_2008_eugenia_eugenios(self):
        # Cluster 3 -- taregir ՉՈ (2008, Greg Easter 03-23): the leap year pushes Eugenia and
        # Eugenios into the summer window (the p.610 rubric moves them to the lower letter Ո,
        # after Vardavar). The full 21-saint march lands Eugenia 07-31 and Eugenios 08-04.
        for (m, d) in ((7, 31), (8, 4)):
            res = compute_armenian_lectionary(datetime.date(2008, m, d))
            self.assertEqual(res["Source"], "second-volume-cycle",
                             f"2008-{m:02d}-{d:02d} should ship from the cycle tier")
            self.assertEqual(res["ReadingsList"], list(_ref_readings(2008, m, d)),
                             f"2008-{m:02d}-{d:02d} should exact-match ground truth")


class TestAutumnSolarMarch(unittest.TestCase):
    """Locks the solar-anchored autumn triplet (Andrew / Adrian / Abraham & Khoren). These
    cross-validate across DIFFERENT taregirs that share a Gregorian Easter (2010 Ա, 2021 Ս),
    confirming they are solar- not Easter-keyed; anchored to the Heesnak (Advent-eve) Sunday
    per the Ս 'after the tenth Sunday' rubric, they land Nov 16 (Adrian) / Nov 18 (Abraham &
    Khoren) and ship exact from the cycle tier."""

    def test_2010_2021_adrian_abraham_exact(self):
        for y in (2010, 2021):
            for (m, d) in ((11, 16), (11, 18)):
                res = compute_armenian_lectionary(datetime.date(y, m, d))
                self.assertEqual(res["Source"], "second-volume-cycle",
                                 f"{y}-{m:02d}-{d:02d} should ship from the cycle tier")
                self.assertEqual(res["ReadingsList"], list(_ref_readings(y, m, d)),
                                 f"{y}-{m:02d}-{d:02d} should exact-match ground truth")

    def test_2004_leap_autumn_order(self):
        # taregir ԹԸ (2004, leap, Greg Easter 04-11): the triplet order differs from the
        # non-leap taregirs -- Abraham & Khoren 11-15 then Andrew 11-16 (vs Andrew first).
        for (m, d) in ((11, 15), (11, 16)):
            res = compute_armenian_lectionary(datetime.date(2004, m, d))
            self.assertEqual(res["Source"], "second-volume-cycle",
                             f"2004-{m:02d}-{d:02d} should ship from the cycle tier")
            self.assertEqual(res["ReadingsList"], list(_ref_readings(2004, m, d)),
                             f"2004-{m:02d}-{d:02d} should exact-match ground truth")


class TestWinterSourceMarch(unittest.TestCase):
    """Locks the per-taregir post-Nativity (winter) sequences that replace the generic march
    for taregirs whose January laydown differs: ԹԸ (2004) inserts Eugenia between Vahan and
    Eugenios, and Հ (2009) compresses (Vahan absorbs Eugenia, Eugenios absorbs Andrew) then
    closes with Adrian. Each ships exact from the cycle tier; the parity-split validation keeps
    the leap cache year of the same Gregorian Easter (2020 for 04-12) from dropping them."""

    def test_2004_eugenia_eugenios(self):
        # ԹԸ (2004, Greg Easter 04-11): Eugenia 01-27, Eugenios 01-29.
        for (m, d) in ((1, 27), (1, 29)):
            res = compute_armenian_lectionary(datetime.date(2004, m, d))
            self.assertEqual(res["Source"], "second-volume-cycle",
                             f"2004-{m:02d}-{d:02d} should ship from the cycle tier")
            self.assertEqual(res["ReadingsList"], list(_ref_readings(2004, m, d)),
                             f"2004-{m:02d}-{d:02d} should exact-match ground truth")

    def test_2009_adrian_exact(self):
        # Հ (2009, Greg Easter 04-12): Adrian & Natalia closes the compressed window on 01-29.
        res = compute_armenian_lectionary(datetime.date(2009, 1, 29))
        self.assertEqual(res["Source"], "second-volume-cycle",
                         "2009-01-29 should ship from the cycle tier")
        self.assertEqual(res["ReadingsList"], list(_ref_readings(2009, 1, 29)),
                         "2009-01-29 should exact-match ground truth")


class TestAssumptionFastContinua(unittest.TestCase):
    """Locks the Easter-md banding of the Fast-of-the-Assumption Wed/Fri continua: at span-28
    index 7 the same (span, idx, wd) bucket conflated 2Tim 2.20-26 (Easter 04-05, taregir Թ)
    with 1Tim 5.17-6.5 (Easter 04-04); the modal shipped the wrong one to 2015/2026. Banding
    by Gregorian Easter date separates them."""

    def test_2015_2026_08_05_continua(self):
        expected = ["St. Paul's Second Epistle to Timothy 2.20-26", "John 6.48-54"]
        for y in (2015, 2026):
            res = compute_armenian_lectionary(datetime.date(y, 8, 5))
            self.assertEqual(res["Source"], "generative-continua",
                             f"{y}-08-05 should ship from the continua tier")
            self.assertEqual(res["ReadingsList"], expected)
            self.assertEqual(res["ReadingsList"], list(_ref_readings(y, 8, 5)),
                             f"{y}-08-05 should exact-match ground truth")


class TestAnnunciationCompositeCompleteness(unittest.TestCase):
    """Locks the Apr-7 Annunciation collision composite. The flat E/EB slots carry no
    service structure, so the published calendar's co-celebration REDUCTIONS cannot be
    reproduced; the composite instead guarantees COMPLETENESS -- it never drops a reading
    the calendar keeps (GT is a subset of the output), erring toward a superset. Two
    faithful rule fixes close the only two cases that previously dropped a key reading:
    a deep-Lent SUNDAY co-celebrates its Liturgy (2019, Luke 21.5-38), and Eastertide
    appends the eve's resurrection Gospel (2018, John 21.1-14)."""

    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_no_apr7_collision_drops_a_reading(self):
        # Core invariant: every cached Apr-7 has GT as a subset of the engine output.
        for y in range(2001, 2027):
            iso = f"{y}-04-07"
            day = self.days.get(iso)
            if not day or not day["readings"]:
                continue
            out = set(compute_armenian_lectionary(datetime.date(y, 4, 7))["ReadingsList"])
            missing = [r for r in day["readings"] if r not in out]
            self.assertEqual(missing, [], f"{iso} dropped calendar reading(s): {missing}")

    def test_2019_lenten_sunday_keeps_its_gospel(self):
        # Deep-Lent SUNDAY: the day has a Liturgy, so it co-celebrates (was: proper alone).
        out = compute_armenian_lectionary(datetime.date(2019, 4, 7))["ReadingsList"]
        self.assertIn("Luke 21.5-38", out)

    def test_2018_eastertide_keeps_eve_resurrection_gospel(self):
        # Bright-week eve (Apr 6 = 6th day of Easter) resurrection Gospel co-read.
        out = compute_armenian_lectionary(datetime.date(2018, 4, 7))["ReadingsList"]
        self.assertIn("John 21.1-14", out)

    def test_deep_lent_weekday_ferias_stay_proper_only(self):
        # The Sunday exception must NOT fire for aliturgical weekday ferias, which stay
        # exact proper-only matches (2011 offset -17, 2022 offset -10).
        for y in (2011, 2022):
            res = compute_armenian_lectionary(datetime.date(y, 4, 7))
            self.assertEqual(res["ReadingsList"], list(_ref_readings(y, 4, 7)),
                             f"{y}-04-07 should stay an exact proper-only match")

    def test_previously_exact_composites_unregressed(self):
        # Great Wednesday (2004) and Great Friday (2023) already exact-matched; the new
        # branches must not disturb them.
        for y in (2004, 2023):
            res = compute_armenian_lectionary(datetime.date(y, 4, 7))
            self.assertEqual(res["ReadingsList"], list(_ref_readings(y, 4, 7)),
                             f"{y}-04-07 should remain an exact match")


class TestNativityOctaveEncroachment(unittest.TestCase):
    """Locks the p.464 Fast-of-Catechumens encroachment on the mid-January octave, the
    extreme-early-Easter case (2008, Easter Mar 23) where the fast reaches back to Jan 14.
    Two days that previously blanked (the winter grid's post-Nativity window is empty that
    year) are now served:
      * Jan 19 -- Nativity of John the Forerunner (nominal Jan 14) transferred out of the
        aliturgical fast week; byte-EXACT vs GT via the validated PnJohn proper.
      * Jan 13 -- octave/eve co-celebration; a COMPLETENESS superset (GT is a subset)."""

    def test_2008_john_forerunner_transferred_exact(self):
        res = compute_armenian_lectionary(datetime.date(2008, 1, 19))
        self.assertEqual(res["Source"], "validated-composite")
        self.assertEqual(res["ReadingsList"], list(_ref_readings(2008, 1, 19)))

    def test_2008_octave_eve_superset_covers_gt(self):
        out = compute_armenian_lectionary(datetime.date(2008, 1, 13))
        self.assertEqual(out["Source"], "generative-composite")
        missing = [r for r in _ref_readings(2008, 1, 13)
                   if r not in out["ReadingsList"]]
        self.assertEqual(missing, [], f"octave composite dropped GT reading(s): {missing}")

    def test_normal_year_january_untouched(self):
        # The encroachment rule must fire ONLY in the extreme year: a normal-Easter year
        # (2019, Easter Apr 21) has its full post-Nativity window, so neither Jan 13 nor
        # Jan 19 may be claimed by these composites.
        for dd in (13, 19):
            res = compute_armenian_lectionary(datetime.date(2019, 1, dd))
            self.assertNotIn(res["Source"], {"generative-composite"},
                             f"2019-01-{dd:02d} wrongly claimed by an octave composite")


class TestPreLentCohort(unittest.TestCase):
    """Locks the pre-Lent martyr cohort (Sargis/Atom/Sukias/Voskian/Ghevond) served from
    the Tōnats'oyts First Volume pp.464-465. Readings follow the SOURCE verse-ranges (a few
    differ from the cache by a versification convention, reconciled via source_corrections).
    Covers the two rank-based displacement collisions and the source-faithful ranges."""

    def test_all_cohort_days_match_source_corrected_cache(self):
        # Every cohort-tier day over the cache equals the source-corrected oracle, 0 wrong.
        days = load_all()
        wrong = []
        for iso, day in days.items():
            if not day["readings"]:
                continue                      # held-out/empty day: no oracle to compare
            res = compute_armenian_lectionary(datetime.date.fromisoformat(iso))
            if res["Source"] != "first-volume-cohort":
                continue
            if res["ReadingsList"] != _expected(res, day["readings"]):
                wrong.append(iso)
        self.assertEqual(wrong, [], f"cohort tier disagreed with source-corrected cache: {wrong}")

    def test_2008_john_collision_sargis_wins(self):
        # Extreme-early Easter: John (transferred to Sargis's Saturday, Jan 19) pushes
        # Sargis onto Atom's Monday (Jan 21); the senior general wins the merge.
        res = compute_armenian_lectionary(datetime.date(2008, 1, 21))
        self.assertEqual(res["Source"], "first-volume-cohort")
        self.assertIn("St. Sargis", res["Liturgical Day"])
        self.assertEqual(res["ReadingsList"], list(_ref_readings(2008, 1, 21)))

    def test_2022_presentation_collision_atom_wins(self):
        # The Presentation of the Lord (Feb 14) takes Atom's Monday; Atom shifts to
        # Sukias's Tuesday (Feb 15) and wins the merge.
        res = compute_armenian_lectionary(datetime.date(2022, 2, 15))
        self.assertEqual(res["Source"], "first-volume-cohort")
        self.assertIn("Atomian", res["Liturgical Day"])

    def test_source_verse_ranges_served(self):
        # The engine serves the SOURCE ranges, not the cache's (Atom Wisdom 6.12-21 /
        # John 16.1-5), per the reviewed corrections.
        res = compute_armenian_lectionary(datetime.date(2011, 2, 21))  # Atom, clean year
        self.assertIn("Wisdom 6.12-21", res["ReadingsList"])
        self.assertIn("John 16.1-5", res["ReadingsList"])

    def test_forward_year_served_without_oracle(self):
        # The whole point of source-derivation: a forward year (no cache) still ships the
        # cohort. 2027 Sargis is the Saturday at Easter-64 (2027 Easter = Mar 28 → Jan 23),
        # shipped from the fixed offset regardless of any cache.
        res = compute_armenian_lectionary(datetime.date(2027, 1, 23))  # Sargis 2027 (E-64)
        self.assertEqual(res["Source"], "first-volume-cohort")
        self.assertIn("St. Sargis", res["Liturgical Day"])


if __name__ == "__main__":
    unittest.main()
