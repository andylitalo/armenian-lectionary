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
from dev import source_corrections  # noqa: E402


def _feast_names_hy():
    """The shipped Armenian feast map, loaded from disk.

    The engine no longer loads this at import -- nothing at runtime reads it since feast
    names resolve through the observance catalog. The guards below check the shipped FILE,
    which is still a dev-time input to dev/build_observance_catalog.py, so they read it
    themselves rather than keeping an unused module global alive to hang a test on.
    """
    return engine._load_json_map(engine.FEAST_NAMES_HY_PATH)


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


class TestResolveObservanceNames(unittest.TestCase):
    """Resolution semantics, on the function that actually serves them.

    These previously exercised ``_translate_feast``, the pre-catalog whole-string
    translator, which stopped being reachable at runtime when #18 moved resolution onto the
    id catalog. Testing a function nothing calls proves nothing, so they now cover
    ``_resolve_observance_names`` -- same three behaviours, real code path.
    """

    CATALOG = {
        "nativity_5": {"en": "Fifth day of Nativity", "hy": "Ե օր Ս. Ծննդեան"},
        "genocide": {"en": "Remembrance of the Armenian Genocide (1915)",
                     "hy": "ՀՀ եղեռն"},
    }

    def setUp(self):
        self._orig = (engine._OBSERVANCE_CATALOG, engine._TEXT_TO_OBSERVANCE_ID)
        engine._OBSERVANCE_CATALOG = self.CATALOG
        engine._TEXT_TO_OBSERVANCE_ID = {
            v["en"]: sid for sid, v in self.CATALOG.items()}
        self.addCleanup(self._restore)

    def _restore(self):
        engine._OBSERVANCE_CATALOG, engine._TEXT_TO_OBSERVANCE_ID = self._orig

    def test_single_component(self):
        self.assertEqual(
            engine._resolve_observance_names("Fifth day of Nativity", "hy"),
            "Ե օր Ս. Ծննդեան")

    def test_composite_resolves_component_by_component(self):
        """Unknown components stay English rather than dropping the whole name."""
        label = "Some Sunday" + engine._OBSERVANCE_SEP + \
            "Remembrance of the Armenian Genocide (1915)"
        self.assertEqual(
            engine._resolve_observance_names(label, "hy"),
            "Some Sunday" + engine._OBSERVANCE_SEP + "ՀՀ եղեռն")

    def test_unknown_unchanged(self):
        self.assertEqual(engine._resolve_observance_names("Mystery", "hy"), "Mystery")


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
        # "Liturgical Day" resolves via the id-based observance catalog, not
        # _FEAST_NAMES_HY directly -- see _resolve_observance_names.
        orig_cat, orig_ids = engine._OBSERVANCE_CATALOG, engine._TEXT_TO_OBSERVANCE_ID
        orig_b = engine._BOOK_NAMES_HY
        engine._OBSERVANCE_CATALOG = {
            "resurrection": {
                "en": "RESURRECTION OF OUR LORD JESUS CHRIST (Easter Sunday)",
                "hy": "ՅԱՐՈՒԹԻՒՆ"}}
        engine._TEXT_TO_OBSERVANCE_ID = {
            "RESURRECTION OF OUR LORD JESUS CHRIST (Easter Sunday)": "resurrection"}
        engine._BOOK_NAMES_HY = {"John": "Ավետարան ըստ Հովհաննեսի",
                                 "Acts of the Apostles": "Գործք առաքելոց",
                                 "Mark": "Ավետարան ըստ Մարկոսի",
                                 "Luke": "Ավետարան ըստ Ղուկասի",
                                 "Matthew": "Ավետարան ըստ Մատթէոսի"}
        try:
            result = compute_armenian_lectionary(self.DATE, language="hy")
        finally:
            engine._OBSERVANCE_CATALOG, engine._TEXT_TO_OBSERVANCE_ID = orig_cat, orig_ids
            engine._BOOK_NAMES_HY = orig_b

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

    def test_second_sunday_after_pentecost_ordinal(self):
        """Locks a real fix the observance-catalog resolver surfaced: the OLD whole-
        string _translate_feast could return "Ա" (First) for "Second Sunday after
        Pentecost" depending on which composite happened to be scraped whole, even
        though English never has a "First Sunday after Pentecost" (the count floors at
        2 -- see engine._POSITION_FAMILIES). The catalog resolves this English text to
        one canonical, correct "Բ" (Second) everywhere. Self-contained: skips if the
        shipped catalog is absent."""
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")
        result = compute_armenian_lectionary(datetime.date(2001, 6, 17), language="hy")
        self.assertEqual(
            result["Liturgical Day"],
            "Բ կիւրակէ զկնի Հոգեգալստեան — Տօն Կաթուղիկէ Սուրբ Էջմիածնի")


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
        maps = {**_feast_names_hy(), **engine._BOOK_NAMES_HY}
        if not maps:
            self.skipTest("hy maps not present")
        for v in maps.values():
            stray = self._non_armenian_letters(v)
            self.assertEqual(stray, [], f"non-Armenian letters {stray} in {v!r}")

    def test_map_keys_have_no_unexpected_chars(self):
        # The English keys are the lookup surface: a homoglyph here (as the source typed
        # into some feast names) silently fails to translate. Guard them against ANY
        # contaminant, not just the two folded so far.
        from dev.source_corrections import unexpected_chars
        keys = list(_feast_names_hy()) + list(engine._BOOK_NAMES_HY)
        if not keys:
            self.skipTest("hy maps not present")
        for k in keys:
            bad = unexpected_chars(k)
            self.assertEqual(bad, [], f"unexpected {bad} in hy map key {k!r}")

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
            self.assertNotIn("օրենք", v, f"reformed 'օրենք' (want 'օրէնք') in {v!r}")
            # General vew guard: in this data classical վ (U+057E) only ever follows
            # ա or ո (աւ/ոււ diphthongs). A վ after any other letter is a reform
            # leftover where classical writes ւ (e.g. "Թվեր" for "Թիւեր").
            for i, ch in enumerate(v):
                if ch == "վ":
                    prev = v[i - 1] if i else ""
                    self.assertIn(prev, "աո",
                                  f"reformed 'վ' after {prev!r} (want 'ւ') in {v!r}")
        # The maintainer's canonical example.
        self.assertEqual(books.get("John"), "Աւետարան ըստ Յովհաննէսի")

    def test_observances_use_mashtots_orthography(self):
        # Feast titles are entered in traditional orthography at the source but carry a
        # few proper-noun reform slips (Դանիել/Եզեկիել/Անգե, հավատ). The shipped map must
        # be a fixed point of the specific-word reversal that dev applies on a re-scrape:
        # re-running it changes nothing, so no reformed proper noun can ship unnoticed.
        from dev.fetch_translations import to_mashtots_names
        feasts = _feast_names_hy()
        if not feasts:
            self.skipTest("feast map not present")
        for v in feasts.values():
            self.assertEqual(v, to_mashtots_names(v),
                             f"reformed proper noun survives in feast {v!r}")


class TestNamedFastDayCountLabels(unittest.TestCase):
    """The Fast of St. Gregory the Illuminator and the Fast of St. James of Nisibis
    each carry their own day-count label in English now ("Nth day of the Fast of ..."),
    rather than a bare "Fast day" -- so the id is recoverable from the English text
    alone, with no date-scoping needed (contrast the previous design, which resolved a
    shared "Fast day" text from the date; see docs/observance-name-corrections.md).

    Neither fast's per-day wording is attested in the source (English or Armenian); both
    are a deliberate, documented invention. Armenian does not distinguish the day within
    either fast (or the renamed Fast of Prophet Elijah): each fast serves ONE fixed
    Armenian phrase for all its days, supplied directly in the TSV's ``approved_hy``
    rather than sourced (see docs/observance-name-corrections.md section 10). This is an
    explicit override of the Illuminator fast's own source-attested per-day ordinal
    (still recorded as ``source_hy`` -- see ``source_corrections.illuminator_fast_label``
    and section 5), not an absence of one.
    """

    _ORDINALS = ("First", "Second", "Third", "Fourth", "Fifth")

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def _pentecost(self, year):
        return engine.calculate_gregorian_easter(year) + datetime.timedelta(days=49)

    def test_window_is_closed_at_both_ends(self):
        """The eve (Pentecost+21) and the Discovery of the Relics (+27) are not fast days."""
        pentecost = self._pentecost(2026)
        for offset in (21, 27):
            with self.subTest(offset=offset):
                self.assertIsNone(source_corrections.illuminator_fast_label(
                    (pentecost + datetime.timedelta(days=offset)).isoformat()))

    def _heesnak(self, year):
        return engine.sunday_closest_to(year, 11, 18)

    def test_illuminator_fast_carries_its_ordinal_in_english(self):
        for year in (2001, 2014, 2026):
            pentecost = self._pentecost(year)
            for n, ordinal in enumerate(self._ORDINALS, start=1):
                day = pentecost + datetime.timedelta(days=21 + n)
                with self.subTest(year=year, ordinal=n):
                    en = compute_armenian_lectionary(day)["Liturgical Day"]
                    hy = compute_armenian_lectionary(day, language="hy")["Liturgical Day"]
                    self.assertTrue(
                        en.startswith(
                            f"{ordinal} day of the Fast of St. Gregory the Illuminator"),
                        f"{day} served {en!r}")
                    self.assertTrue(hy.startswith("Սուրբ Գրիգոր Լուսավորչի պահք"),
                                    f"{day} served {hy!r}")

    def test_nisibis_fast_carries_its_ordinal_in_english(self):
        # Years chosen so Dec 9 (a separate, higher-precedence suppression -- see
        # TestDecemberNinthFastMarker) does not fall inside this window and mask it.
        for year in (2001, 2010, 2023):
            heesnak = self._heesnak(year)
            for n, ordinal in enumerate(self._ORDINALS, start=1):
                day = heesnak + datetime.timedelta(days=21 + n)
                with self.subTest(year=year, ordinal=n):
                    en = compute_armenian_lectionary(day)["Liturgical Day"]
                    hy = compute_armenian_lectionary(day, language="hy")["Liturgical Day"]
                    self.assertTrue(
                        en.startswith(
                            f"{ordinal} day of the Fast of St. James of Nisibis"),
                        f"{day} served {en!r}")
                    self.assertTrue(hy.startswith("Սուրբ Հակոբի պահք"),
                                    f"{day} served {hy!r}")

    def test_elijah_fast_carries_its_fixed_armenian_phrase(self):
        for year in (2001, 2014, 2026):
            pentecost = self._pentecost(year)
            for offset in (1, 3, 6):        # Mon, Wed, Sat -- a spread across the week
                day = pentecost + datetime.timedelta(days=offset)
                with self.subTest(year=year, offset=offset):
                    en = compute_armenian_lectionary(day)["Liturgical Day"]
                    hy = compute_armenian_lectionary(day, language="hy")["Liturgical Day"]
                    self.assertTrue(en.endswith("day of the Fast of Prophet Elijah"),
                                    f"{day} served {en!r}")
                    self.assertTrue(hy.startswith("Եղիական պահք"), f"{day} served {hy!r}")

    def test_an_ordinary_fast_day_is_not_captured(self):
        """A Wednesday well outside any named fast gets the weekday split, not a
        named-fast label and not the old bare "Fast day"/"Պահք"."""
        day = datetime.date(2026, 10, 7)          # ordinary-time Wednesday
        en = compute_armenian_lectionary(day)["Liturgical Day"]
        hy = compute_armenian_lectionary(day, language="hy")["Liturgical Day"]
        self.assertTrue(en.startswith("Wednesday Fast"), en)
        self.assertTrue(hy.startswith("Չորեքշաբթիի պահք"), hy)

    def test_storage_tiers_get_a_dedicated_id(self):
        """Text-keyed id resolution recovers each fast's own id directly -- no
        date-scoping needed now that English carries the ordinal. (The exact id string
        is not pinned here -- dev/build_observance_catalog.py's slug collision
        resolution numbers it among the many "Nth day of the Fast of ..." components --
        only that a single, stable id comes back and that it differs per fast/ordinal.)
        """
        from dev.observance_ids import ids_for_text
        illum = ids_for_text("First day of the Fast of St. Gregory the Illuminator")
        nisibis = ids_for_text("First day of the Fast of St. James of Nisibis")
        self.assertEqual(len(illum), 1)
        self.assertEqual(len(nisibis), 1)
        self.assertNotEqual(illum, nisibis)
        self.assertEqual(ids_for_text("Wednesday Fast"), ["wednesday_fast"])
        self.assertEqual(ids_for_text("Friday Fast"), ["friday_fast"])


if __name__ == "__main__":
    unittest.main()
