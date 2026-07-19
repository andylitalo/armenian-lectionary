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
variants. The contract is:

  * every day's engine commemoration equals the scraped commemoration, EXCEPT the
    enumerated KNOWN_FEAST_DIVERGENCES (a small generative-best-guess residue), and
  * that allowlist is exact -- a listed day that stops diverging also fails, so the
    allowlist can't rot.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all                                        # noqa: E402
from dev.feast_names import commemoration_of                           # noqa: E402
from dev.source_corrections import (                                    # noqa: E402
    canonical_commem, KNOWN_FEAST_DIVERGENCES)
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
        unlisted = []             # engine != scrape and NOT an accounted divergence
        listed_but_matching = []  # in KNOWN_FEAST_DIVERGENCES yet actually matches
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
            matches = _commem(feast) == _commem(got)
            if iso in KNOWN_FEAST_DIVERGENCES:
                if matches:
                    listed_but_matching.append(iso)
            elif not matches:
                unlisted.append((iso, src, canonical_commem(commemoration_of(got))))

        # No silent data loss.
        self.assertGreaterEqual(
            total, EXPECTED_TOTAL_DAYS,
            f"only {total} reference days processed (< {EXPECTED_TOTAL_DAYS})")
        # Every scraped feast string must fully segment into position/eve/commemoration.
        self.assertEqual(
            unsegmented, [],
            f"{len(unsegmented)} feast strings did not segment: {unsegmented[:5]}")
        # The allowlist must be exact: no stale entries that no longer diverge.
        self.assertEqual(
            listed_but_matching, [],
            "KNOWN_FEAST_DIVERGENCES entries that now match (remove them): "
            f"{listed_but_matching}")
        # The contract: no unaccounted-for feast-name mismatch.
        self.assertEqual(
            unlisted, [],
            f"{len(unlisted)} engine feast names disagree with the scrape "
            f"(first 10): {unlisted[:10]}")


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


if __name__ == "__main__":
    unittest.main()
