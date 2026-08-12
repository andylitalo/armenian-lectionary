"""Unit tests for the structured ``ReadingsRefs`` citation parser (engine.py).

Pure-function tests over ``_parse_citation_ref``/``_build_readings_refs``, plus a
corpus-wide smoke test over every citation the engine actually serves 2001-2027.
Self-contained: no ground-truth cache needed.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import compute_armenian_lectionary  # noqa: E402
from armenian_lectionary import engine  # noqa: E402


class TestParseCitationRef(unittest.TestCase):
    def test_single_verse(self):
        self.assertEqual(
            engine._parse_citation_ref("John 3.16"),
            [{"book": "John", "start_chapter": 3, "start_verse": 16,
              "end_chapter": 3, "end_verse": 16, "citation": "John 3.16"}])

    def test_same_chapter_range(self):
        self.assertEqual(
            engine._parse_citation_ref("Daniel 3.1-23"),
            [{"book": "Daniel", "start_chapter": 3, "start_verse": 1,
              "end_chapter": 3, "end_verse": 23, "citation": "Daniel 3.1-23"}])

    def test_cross_chapter_range(self):
        self.assertEqual(
            engine._parse_citation_ref("Job 9.1-10.2"),
            [{"book": "Job", "start_chapter": 9, "start_verse": 1,
              "end_chapter": 10, "end_verse": 2, "citation": "Job 9.1-10.2"}])

    def test_multiword_book_head(self):
        ref = engine._parse_citation_ref(
            "St. Paul's Epistle to the Hebrews 12.18-27")[0]
        self.assertEqual(ref["book"], "St. Paul's Epistle to the Hebrews")
        self.assertEqual((ref["start_chapter"], ref["start_verse"]), (12, 18))
        self.assertEqual((ref["end_chapter"], ref["end_verse"]), (12, 27))

    def test_azariah_composite_splits_and_shares_citation(self):
        citation = "Daniel 3.1-23, Azariah. 1-68"
        refs = engine._parse_citation_ref(citation)
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0]["book"], "Daniel")
        self.assertEqual((refs[0]["start_chapter"], refs[0]["start_verse"],
                          refs[0]["end_chapter"], refs[0]["end_verse"]), (3, 1, 3, 23))
        # Azariah is single-chapter: the bare "1-68" tail (no dot) defaults chapter to 1.
        self.assertEqual(refs[1]["book"], "Azariah")
        self.assertEqual((refs[1]["start_chapter"], refs[1]["start_verse"],
                          refs[1]["end_chapter"], refs[1]["end_verse"]), (1, 1, 1, 68))
        # Both sub-refs carry the original, unsplit citation as their back-pointer.
        self.assertEqual(refs[0]["citation"], citation)
        self.assertEqual(refs[1]["citation"], citation)

    def test_unrecognized_book_raises(self):
        with self.assertRaises(ValueError):
            engine._parse_citation_ref("Nonesuch 1.1")

    def test_unparseable_tail_raises(self):
        with self.assertRaises(ValueError):
            engine._parse_citation_ref("John chapter three")


class TestBuildReadingsRefs(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(engine._build_readings_refs([]), [])

    def test_flat_maps_multiple_citations(self):
        refs = engine._build_readings_refs(["John 3.16", "Mark 1.1-8"])
        self.assertEqual([r["book"] for r in refs], ["John", "Mark"])


class TestReadingsRefsCorpus(unittest.TestCase):
    """Every citation the engine actually serves, 2001-2027, must parse without error
    and stay aligned with ReadingsList -- mirrors the 1,125-citation audit done while
    designing this parser."""

    def test_every_served_citation_parses(self):
        d = datetime.date(2001, 1, 1)
        end = datetime.date(2027, 12, 31)
        one = datetime.timedelta(days=1)
        while d <= end:
            result = compute_armenian_lectionary(d)
            refs = result.get("ReadingsRefs", [])
            readings_list = result.get("ReadingsList", [])
            if not readings_list:
                self.assertEqual(refs, [], f"non-empty ReadingsRefs on aliturgical {d}")
            else:
                self.assertEqual({r["citation"] for r in refs}, set(readings_list),
                                  f"ReadingsRefs citations diverge from ReadingsList on {d}")
            d += one


class TestReadingsRefsLanguageIndependence(unittest.TestCase):
    DATE = datetime.date(2026, 4, 5)  # Easter: a validated-table day

    def test_book_stays_english_under_hy(self):
        en = compute_armenian_lectionary(self.DATE, language="en")
        hy = compute_armenian_lectionary(self.DATE, language="hy")
        self.assertEqual(en["ReadingsRefs"], hy["ReadingsRefs"])
        self.assertTrue(any("Աւետարան" in r for r in hy["ReadingsList"]))
        self.assertTrue(any(ref["book"] == "John" for ref in hy["ReadingsRefs"]))

    def test_aliturgical_day_yields_empty_refs(self):
        result = compute_armenian_lectionary(datetime.date(2001, 1, 1))
        if not result.get("ReadingsList"):
            self.assertEqual(result["ReadingsRefs"], [])


if __name__ == "__main__":
    unittest.main()
