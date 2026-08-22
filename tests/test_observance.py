"""Accuracy lock over the engine's feast/fast NAME of the day.

The engine serves a liturgical-day name as ``compute_armenian_lectionary(...)
["Liturgical Day"]`` (returned verbatim by the web ``/readings`` endpoint). This is
the same value the downstream ``bahk`` project scrapes from sacredtradition.am's
``<div class=dname>`` and feeds to its AI-context generation -- the end goal being to
serve it from this package so bahk can drop its scraping dependency. Readings are locked
by test_full_dataset.py; this locks the NAME.

The scrape mashes several ``<br>``-separated components (a year-varying "Nth day of
<Season>" position label, the commemoration, an "Eve of <Fast>" status note) into one
string. This test compares only the COMMEMORATION component
(dev/observance_names.commemoration_of), canonicalized on BOTH sides
(dev/source_corrections.canonical_commem) to reconcile reviewed companion-enumeration
variants: every day's engine commemoration equals the scraped commemoration across
2001-2026.

That contract holds of the PROJECTION, not of the name. Because the position and eve
components are stripped from both sides, over half the corpus reduces to ``"" == ""`` and
is asserted about only vacuously -- which is how the engine came to ship a name the source
contradicted on 41 days without this test noticing. ``tests/test_observance_name_raw.py`` locks
the unprojected string that downstream actually stores, and ``tests/test_observance_contract.py``
adds the source-independent invariants; this file is now the narrowest of the three.
Audit residual mismatches with ``python dev/observance_audit.py``, and see
the full inventory (``python dev/observance_discrepancy_report.py``).
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                        # noqa: E402
from dev.observance_names import commemoration_of                           # noqa: E402
from dev.observance_ids import is_added_text                           # noqa: E402
from dev.source_corrections import canonical_commem                     # noqa: E402
from armenian_lectionary.engine import (                                # noqa: E402
    _OBSERVANCE_SEP, compute_armenian_lectionary,
)
from tests._reference_cache import requires_reference_cache             # noqa: E402

# Lower bound on processed reference days; guards against silent data loss.
EXPECTED_TOTAL_DAYS = int(os.environ.get("EXPECTED_TOTAL_DAYS", "9495"))

# Ceiling on days where BOTH commemorations are empty, so the comparison is vacuous.
# Over half the corpus is a pure position/eve day with no commemoration, and this test
# says nothing about those; tests/test_observance_name_raw.py is what actually locks them.
# Monotonic DOWN -- if the projection starts discarding more, that is a regression.
VACUOUS_CEILING = int(os.environ.get("FEAST_VACUOUS_CEILING", "5100"))


def _commem(feast_str):
    """Canonical, casefolded commemoration for comparison (applied to both sides).

    Declared fixed-date additions are dropped first. They sit in the commemoration position
    but the source's English names them on no day at all, so leaving them in would make
    every Jan 1 read as a mismatch here -- a fact already counted, once, by
    tests/test_observance_name_raw.OBSERVANCE_ADDITION_DAYS. Dropping them keeps this test measuring
    what it is for: whether the commemoration the source DID print is the one we serve.
    """
    return canonical_commem(commemoration_of(_strip_added(feast_str))).casefold()


def _strip_added(feast_str):
    """The feast string without any declared fixed-date addition.

    Must run BEFORE commemoration_of, which mashes the component separator away -- strip it
    after and the addition fuses onto the saint beside it.
    """
    return _OBSERVANCE_SEP.join(c for c in (feast_str or "").split(_OBSERVANCE_SEP)
                           if c and not is_added_text(c))


@requires_reference_cache
class TestObservanceCommemoration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_commemoration_matches_source(self):
        total = 0
        vacuous = 0               # both sides reduce to "" -- the comparison asserts nothing
        mismatches = []           # engine commemoration != scrape commemoration
        unsegmented = []          # extractor left an unrecognized-prefix sentinel
        for iso in sorted(self.days):
            feast = (self.days[iso].get("feast") or "").strip()
            if not feast:
                continue
            total += 1
            src = canonical_commem(commemoration_of(_strip_added(feast)))
            if "\x00" in src:
                unsegmented.append((iso, feast))
            got = compute_armenian_lectionary(
                datetime.date.fromisoformat(iso))["Liturgical Day"]
            if not _commem(feast) and not _commem(got):
                vacuous += 1
            elif _commem(feast) != _commem(got):
                mismatches.append(
                    (iso, src, canonical_commem(commemoration_of(_strip_added(got)))))

        # No silent data loss.
        self.assertGreaterEqual(
            total, EXPECTED_TOTAL_DAYS,
            f"only {total} reference days processed (< {EXPECTED_TOTAL_DAYS})")
        # Every scraped feast string must fully segment into position/eve/commemoration.
        self.assertEqual(
            unsegmented, [],
            f"{len(unsegmented)} feast strings did not segment: {unsegmented[:5]}")
        # The contract: every engine commemoration matches the scrape (2001-2026).
        self.assertEqual(
            mismatches, [],
            f"{len(mismatches)} engine feast names disagree with the scrape "
            f"(first 10): {mismatches[:10]}")
        # Report the blind spot rather than hide it. Days whose commemoration is empty on
        # both sides (a pure position/eve day) are compared, but the comparison is
        # vacuous -- it is satisfied by ANY pair of such names, which is how a placeholder
        # and a real label once matched. Those days are covered for real by
        # test_observance_name_raw.py, which compares the unprojected string. Keep this ceiling
        # so the projection cannot quietly widen.
        self.assertLessEqual(
            vacuous, VACUOUS_CEILING,
            f"{vacuous} of {total} days compare \"\" == \"\" here (ceiling "
            f"{VACUOUS_CEILING}); this test asserts nothing about them")


class TestCommemorationExtractor(unittest.TestCase):
    """Pin the commemoration extractor so its stripping stays faithful."""

    def test_strips_position_and_eve(self):
        # Pure ordinal + eve -> no commemoration.
        self.assertEqual(
            commemoration_of(
                "Fifth Sunday after the AssumptionEve of Fast of Exaltation of Holy Cross"),
            "")

    def test_keeps_commemoration_between_position_and_eve(self):
        self.assertEqual(
            commemoration_of(
                "Fourth Sunday after AssumptionFeast of the Birth of Holy Virgin Mary "
                "from AnnaEve of Fast of Exaltation of Holy Cross"),
            "Feast of the Birth of Holy Virgin Mary from Anna")

    def test_strips_fast_day_marker(self):
        self.assertEqual(
            commemoration_of("Fast dayPRESENTATION OF OUR LORD TO THE TEMPLE"),
            "PRESENTATION OF OUR LORD TO THE TEMPLE")

    def test_keeps_genocide_remembrance(self):
        self.assertEqual(
            commemoration_of(
                "Ninth day of EastertideRemembrance of the Armenian Genocide (1915)"),
            "Remembrance of the Armenian Genocide (1915)")

    def test_plain_commemoration_unchanged(self):
        self.assertEqual(
            commemoration_of("Saints Hripsime and her companions"),
            "Saints Hripsime and her companions")

    def test_engine_placeholder_survives_extraction(self):
        """A placeholder must NOT reduce to "" -- that is what hid six defective days.

        Collapsing it made "(movable ordinary-time reading)" compare equal to any
        pure-position source label, which also collapses to "". Kept verbatim, a
        placeholder can only match another placeholder.
        """
        self.assertEqual(commemoration_of("(movable ordinary-time reading)"),
                         "(movable ordinary-time reading)")
        self.assertEqual(commemoration_of("(commemoration)"), "(commemoration)")
        self.assertNotEqual(commemoration_of("(movable ordinary-time reading)"),
                            commemoration_of("Fast day"))


class TestConfusables(unittest.TestCase):
    def test_folds_cyrillic_homoglyphs(self):
        from dev.source_corrections import normalize_confusables
        # Cyrillic Е (U+0415) and о (U+043E) -> Latin E / o.
        self.assertEqual(normalize_confusables("Еighth day of Nativity"),
                         "Eighth day of Nativity")
        self.assertEqual(normalize_confusables("Tatоul"), "Tatoul")

    def test_idempotent_and_pure_ascii_result(self):
        from dev.source_corrections import normalize_confusables
        once = normalize_confusables("Еighth day, Tatоul")
        self.assertEqual(once, normalize_confusables(once))
        self.assertTrue(once.isascii(), f"residual non-ASCII in {once!r}")

    def test_unexpected_chars_detector(self):
        from dev.source_corrections import unexpected_chars
        # Flags contaminants the fold map does not (yet) cover.
        self.assertEqual(unexpected_chars("Tatоul"), ["о"])       # Cyrillic o (U+043E)
        self.assertEqual(unexpected_chars("Оrder"), ["О"])        # Cyrillic O (U+041E)
        self.assertEqual(unexpected_chars("Ηoly"), ["Η"])         # Greek Eta (U+0397)
        # Passes everything legitimately in the data: English, the em-dash OBSERVANCE_SEP,
        # Armenian script, and the Latin digits/parens the hy names carry.
        self.assertEqual(unexpected_chars("Eighth day of Nativity"), [])
        self.assertEqual(unexpected_chars("A — B"), [])           # U+2014 OBSERVANCE_SEP
        self.assertEqual(unexpected_chars("Ը օր Ս. Ծննդեան"), [])
        self.assertEqual(unexpected_chars("… (381 թ.)".replace("…", "")), [])
        self.assertEqual(unexpected_chars(""), [])

    def test_shipped_table_feasts_have_no_unexpected_chars(self):
        import json
        from armenian_lectionary.engine import DATA_PATH
        from dev.source_corrections import unexpected_chars
        with open(DATA_PATH, encoding="utf-8") as f:
            tables = json.load(f)["tables"]
        for ks, entries in tables.items():
            for key, entry in entries.items():
                bad = unexpected_chars(entry.get("feast", ""))
                self.assertEqual(bad, [], f"unexpected {bad} in {ks}/{key} feast")


class TestObservanceSpelling(unittest.TestCase):
    """Locks the English feast-name misspelling fixes (source shipped e.g. 'Theordore';
    the engine now serves the canonical 'Theodore'). Self-contained -- no reference cache."""

    _TYPOS = ("Staint", "Theordore", "Transifiguration", "Grogoris", "Marcarius",
              "Hermongenes", "Alerius", "Canditus", "Eugraphius", "Fiest")

    def test_every_typo_resolves_through_a_review_row(self):
        """Each misspelling is corrected by the ROW that carries it, not by its word.

        These were a word-level fold once, applied to any text containing the letters.
        That reached past the evidence: "Marcarius" -> "Macarius" was established on three
        named components and applied to every component in the corpus. As rows, a fix
        lands exactly where a reviewer looked.
        """
        import json
        import os
        gt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "dev", "observance_name_ground_truth.json")
        with open(gt_path, encoding="utf-8") as fh:
            ground_truth = json.load(fh)
        for typo in self._TYPOS:
            rows = [src for src in ground_truth if typo in src]
            self.assertTrue(rows, f"no review row carries the source typo {typo!r}")
            unfixed = [src for src in rows if typo in ground_truth[src]["approved_en"]]
            self.assertEqual(unfixed, [],
                             f"{typo!r} survives into approved_en on {len(unfixed)} row(s)")

    def test_lookup_is_whole_component_and_idempotent(self):
        """The fold cannot fire inside a longer name that merely starts the same way."""
        from dev.source_corrections import apply_ground_truth
        self.assertEqual(apply_ground_truth("Feast day"), "Fast day")
        # The Belt feast is correctly published and starts with the same two words.
        belt = "Feast day of the Discovery of the Belt of the Holy Mother of God"
        self.assertEqual(apply_ground_truth(belt), belt)
        once = apply_ground_truth("Saint Theodoron the Martyr")
        self.assertEqual(once, apply_ground_truth(once))

    def test_shipped_data_files_carry_no_typo(self):
        import glob
        import os
        from armenian_lectionary.engine import DATA_PATH
        data_dir = os.path.dirname(DATA_PATH)
        for path in glob.glob(os.path.join(data_dir, "*.json")):
            text = open(path, encoding="utf-8").read()
            for typo in self._TYPOS:
                self.assertNotIn(typo, text,
                                 f"{os.path.basename(path)} still carries {typo!r}")

    def test_runtime_liturgical_day_is_corrected(self):
        # Dates whose feast surfaced a typo before the fix (validated + generative tiers).
        cases = {
            datetime.date(2026, 6, 6): "St. Gregory the Illuminator's coming out of Pit",
            datetime.date(2026, 7, 10): "Fifth day of the Fast of the Transfiguration",
            datetime.date(2026, 8, 6):
                "Sts. Adrian and his wife Natalia, and Theodore Stratelates "
                "and Eleutherius the Martyrs",
        }
        for d, expected in cases.items():
            label = compute_armenian_lectionary(d)["Liturgical Day"]
            self.assertEqual(label, expected, d)
            for typo in self._TYPOS:
                self.assertNotIn(typo, label, f"{d} leaked {typo!r}")


class TestDecemberNinthFastMarker(unittest.TestCase):
    """The Conception of the Theotokos (Dec 9) carries a FAST marker, not a feast one.

    The source prints "Feast day" there, which is its own typo for "Fast day" -- the marker
    tracks the Advent-fast weekday set (present Mon/Tue/Wed/Fri, absent Thu/Sat) rather than
    the feast, which is the same feast every year; and the source's own Armenian reads
    "Պահք". See docs/observance-name-corrections.md section 1.

    This pins both halves of the fix together: the engine template
    (``_POSITION_FAMILIES``'s Dec-9 entry) and the source-side fold that keeps the raw-name
    comparison honest. Editing one without the other reopens the contradiction.
    Self-contained -- no reference cache.
    """

    _CONCEPTION = "Feast of the Conception of the Holy Virgin Mary by Anna"

    def test_marker_is_fast_on_advent_fast_weekdays(self):
        # Mon, Tue, Wed, Fri Dec 9ths across the supported window.
        for year in (2013, 2014, 2015, 2016):
            with self.subTest(year=year):
                label = compute_armenian_lectionary(
                    datetime.date(year, 12, 9))["Liturgical Day"]
                self.assertEqual(label, f"Fast day — {self._CONCEPTION}")

    def test_no_marker_on_thursday_or_saturday(self):
        for year in (2017, 2021):        # Sat, Thu
            with self.subTest(year=year):
                label = compute_armenian_lectionary(
                    datetime.date(year, 12, 9))["Liturgical Day"]
                self.assertEqual(label, self._CONCEPTION)

    def test_feast_day_marker_is_gone_everywhere(self):
        """No day in the supported window may serve the mistyped marker."""
        day = datetime.date(2001, 1, 1)
        end = datetime.date(2027, 12, 31)
        while day <= end:
            label = compute_armenian_lectionary(day)["Liturgical Day"]
            self.assertNotIn("Feast day —", label, day)
            day += datetime.timedelta(days=1)

    def test_the_belt_feast_is_not_collateral_damage(self):
        """A different feast whose name merely STARTS with the mistyped marker.

        "Feast day of the Discovery of the Belt of the Holy Mother of God" is correct as
        published, on 26 days. The fold is component-exact precisely so it cannot reach
        inside this one; an unanchored substring replace turned it into "Fast day of the
        Discovery ..." when this fix was first written.
        """
        from dev.source_corrections import apply_ground_truth
        belt = "Feast day of the Discovery of the Belt of the Holy Mother of God"
        self.assertEqual(apply_ground_truth(belt), belt)
        self.assertEqual(
            apply_ground_truth(f"Feast day — {self._CONCEPTION}"),
            f"Fast day — {self._CONCEPTION}")


if __name__ == "__main__":
    unittest.main()
