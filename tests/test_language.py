"""Unit tests for the language kwarg and the English->Armenian localization layer.

Self-contained: the translation functions are exercised with small injected maps so
these pass without the scraped data/*_names_hy.json files present.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import compute_armenian_lectionary  # noqa: E402
from armenian_lectionary import engine  # noqa: E402


class TestTranslateReading(unittest.TestCase):
    BOOKS = {"John": "Ավետարան ըստ Հովհաննեսի",
             "St. Paul's Epistle to the Hebrews": "Թուղթ եբրայեցիներին"}

    def test_swaps_head_keeps_tail(self):
        self.assertEqual(
            engine._translate_reading("John 20.1-18", self.BOOKS),
            "Ավետարան ըստ Հովհաննեսի 20.1-18")

    def test_multiword_head(self):
        self.assertEqual(
            engine._translate_reading(
                "St. Paul's Epistle to the Hebrews 12.18-27", self.BOOKS),
            "Թուղթ եբրայեցիներին 12.18-27")

    def test_unknown_book_unchanged(self):
        self.assertEqual(
            engine._translate_reading("Nonesuch 1.1", self.BOOKS), "Nonesuch 1.1")

    def test_no_verse_tail_unchanged(self):
        self.assertEqual(engine._translate_reading("John", self.BOOKS), "John")

    def test_colon_tail(self):
        # The engine's own reading style uses "chapter:verse"; still translatable.
        self.assertEqual(
            engine._translate_reading("John 3:16", self.BOOKS),
            "Ավետարան ըստ Հովհաննեսի 3:16")


class TestTranslateFeast(unittest.TestCase):
    FEASTS = {"Fifth day of Nativity": "Ե օր Ս. Ծննդեան",
              "Remembrance of the Armenian Genocide (1915)": "ՀՀ եղեռն"}

    def test_whole_string(self):
        self.assertEqual(
            engine._translate_feast("Fifth day of Nativity", self.FEASTS),
            "Ե օր Ս. Ծննդեան")

    def test_component_fallback(self):
        # A composite never seen whole still translates component-by-component,
        # leaving unknown components in English.
        label = "Some Sunday" + engine._FEAST_SEP + \
            "Remembrance of the Armenian Genocide (1915)"
        self.assertEqual(
            engine._translate_feast(label, self.FEASTS),
            "Some Sunday" + engine._FEAST_SEP + "ՀՀ եղեռն")

    def test_unknown_unchanged(self):
        self.assertEqual(engine._translate_feast("Mystery", self.FEASTS), "Mystery")


class TestLanguageKwarg(unittest.TestCase):
    DATE = datetime.date(2026, 4, 5)  # Easter: a validated-table day

    def test_default_is_english_and_unlocalized(self):
        result = compute_armenian_lectionary(self.DATE)
        self.assertIn("RESURRECTION", result["Liturgical Day"].upper())
        # The result names its language even in the English default.
        self.assertEqual(result["Language"], "en")

    def test_explicit_en_matches_default(self):
        self.assertEqual(
            compute_armenian_lectionary(self.DATE),
            compute_armenian_lectionary(self.DATE, language="en"))

    def test_invalid_language_raises(self):
        with self.assertRaises(ValueError):
            compute_armenian_lectionary(self.DATE, language="fr")

    def test_hy_localizes_names_only(self):
        # Inject known maps so the test is deterministic regardless of scraped data.
        orig_f, orig_b = engine._FEAST_NAMES_HY, engine._BOOK_NAMES_HY
        engine._FEAST_NAMES_HY = {
            "RESURRECTION OF OUR LORD JESUS CHRIST (Easter Sunday)": "ՅԱՐՈՒԹԻՒՆ"}
        engine._BOOK_NAMES_HY = {"John": "Ավետարան ըստ Հովհաննեսի",
                                 "Acts of the Apostles": "Գործք առաքելոց",
                                 "Mark": "Ավետարան ըստ Մարկոսի",
                                 "Luke": "Ավետարան ըստ Ղուկասի",
                                 "Matthew": "Ավետարան ըստ Մատթէոսի"}
        try:
            result = compute_armenian_lectionary(self.DATE, language="hy")
        finally:
            engine._FEAST_NAMES_HY, engine._BOOK_NAMES_HY = orig_f, orig_b

        self.assertEqual(result["Liturgical Day"], "ՅԱՐՈՒԹԻՒՆ")
        self.assertEqual(result["Language"], "hy")
        # Every mapped reading is translated; the chapter.verse tails are preserved.
        flat = result["ReadingsList"]
        self.assertIn("Ավետարան ըստ Հովհաննեսի 20.1-18", flat)
        self.assertIn("Գործք առաքելոց 1.1-8", flat)
        # Grouping sections stay in English (metadata), values are Armenian.
        self.assertIn("Gospel", result["Readings"])
        self.assertTrue(any("Ավետարան" in r for r in result["Readings"]["Gospel"]))
        # Provenance metadata is not translated.
        self.assertEqual(result["Source"], "validated-table")


class TestShippedMapsOrthography(unittest.TestCase):
    """Guard the shipped hy maps: pure Armenian script (no Cyrillic/Latin lookalikes)
    and traditional (Mashtots) orthography for the book names. Skips if a map is absent
    (keeps the rest of this module self-contained)."""

    @staticmethod
    def _non_armenian_letters(s):
        out = []
        for ch in s:
            if ch.isalpha() and not (0x0530 <= ord(ch) <= 0x058F
                                     or 0xFB13 <= ord(ch) <= 0xFB17):
                out.append(ch)
        return out

    def test_no_cyrillic_or_latin_letters(self):
        maps = {**engine._FEAST_NAMES_HY, **engine._BOOK_NAMES_HY}
        if not maps:
            self.skipTest("hy maps not present")
        for v in maps.values():
            stray = self._non_armenian_letters(v)
            self.assertEqual(stray, [], f"non-Armenian letters {stray} in {v!r}")

    def test_books_use_mashtots_orthography(self):
        books = engine._BOOK_NAMES_HY
        if not books:
            self.skipTest("book map not present")
        for v in books.values():
            # Reformed markers that must not survive: the -ություն suffix, the ligature և,
            # and vew (U+057E) in the /aw/ diphthong "Աւ" (would be "Ավ" if unreformed).
            self.assertNotIn("ություն", v, f"reformed suffix in {v!r}")
            self.assertNotIn("և", v, f"reformed ligature in {v!r}")
            self.assertNotIn("Ավ", v, f"reformed 'Ավ' (want 'Աւ') in {v!r}")
        # The maintainer's canonical example.
        self.assertEqual(books.get("John"), "Աւետարան ըստ Յովհաննէսի")


if __name__ == "__main__":
    unittest.main()
