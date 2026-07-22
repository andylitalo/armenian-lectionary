"""Accuracy lock over the engine's feast/fast NAME of the day.

The engine serves a liturgical-day name as ``compute_armenian_lectionary(...)
["Liturgical Day"]`` (returned verbatim by the web ``/readings`` endpoint). This is
the same value the downstream ``bahk`` project scrapes from sacredtradition.am's
``<div class=dname>`` and feeds to its AI-context generation -- the end goal being to
serve it from this package so bahk can drop its scraping dependency. Readings are locked
by test_full_dataset.py; this locks the NAME.

The scrape mashes several ``<br>``-separated components (a year-varying "Nth day of
<Season>" position label, the commemoration, an "Eve of <Fast>" status note) into one
separatorless string, and a static engine cannot byte-reproduce the year-varying
position label. So -- per design -- this compares only the COMMEMORATION component
(dev/feast_names.commemoration_of), canonicalized on BOTH sides
(dev/source_corrections.canonical_commem) to reconcile reviewed companion-enumeration
variants. The contract is simple: every day's engine commemoration equals the scraped
commemoration across 2001-2026, with no exceptions.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                        # noqa: E402
from dev.feast_names import commemoration_of                           # noqa: E402
from dev.source_corrections import canonical_commem                     # noqa: E402
from armenian_lectionary.engine import compute_armenian_lectionary      # noqa: E402

# Lower bound on processed reference days; guards against silent data loss.
EXPECTED_TOTAL_DAYS = int(os.environ.get("EXPECTED_TOTAL_DAYS", "9495"))


def _commem(feast_str):
    """Canonical, casefolded commemoration for comparison (applied to both sides)."""
    return canonical_commem(commemoration_of(feast_str)).casefold()


class TestFeastCommemoration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()

    def test_commemoration_matches_source(self):
        total = 0
        mismatches = []           # engine commemoration != scrape commemoration
        unsegmented = []          # extractor left an unrecognized-prefix sentinel
        for iso in sorted(self.days):
            feast = (self.days[iso].get("feast") or "").strip()
            if not feast:
                continue
            total += 1
            src = canonical_commem(commemoration_of(feast))
            if "\x00" in src:
                unsegmented.append((iso, feast))
            got = compute_armenian_lectionary(
                datetime.date.fromisoformat(iso))["Liturgical Day"]
            if _commem(feast) != _commem(got):
                mismatches.append((iso, src, canonical_commem(commemoration_of(got))))

        # No silent data loss.
        self.assertGreaterEqual(
            total, EXPECTED_TOTAL_DAYS,
            f"only {total} reference days processed (< {EXPECTED_TOTAL_DAYS})")
        # Every scraped feast string must fully segment into position/eve/commemoration.
        self.assertEqual(
            unsegmented, [],
            f"{len(unsegmented)} feast strings did not segment: {unsegmented[:5]}")
        # The contract: every engine feast name matches the scrape (2001-2026).
        self.assertEqual(
            mismatches, [],
            f"{len(mismatches)} engine feast names disagree with the scrape "
            f"(first 10): {mismatches[:10]}")


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

    def test_engine_placeholder_is_empty(self):
        self.assertEqual(commemoration_of("(movable ordinary-time reading)"), "")
        self.assertEqual(commemoration_of("(commemoration)"), "")


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

    def test_shipped_table_feasts_have_no_cyrillic(self):
        import json
        from armenian_lectionary.engine import DATA_PATH
        tables = json.load(open(DATA_PATH, encoding="utf-8"))["tables"]
        for ks, entries in tables.items():
            for key, entry in entries.items():
                for ch in entry.get("feast", ""):
                    self.assertFalse(0x0400 <= ord(ch) <= 0x04FF,
                                     f"Cyrillic {ch!r} in {ks}/{key} feast")


if __name__ == "__main__":
    unittest.main()
