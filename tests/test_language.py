"""Unit tests for the language kwarg and the English->Armenian localization layer.

Self-contained: the translation functions are exercised with small injected maps so
these pass without the scraped *_names_hy.json files present.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import compute_armenian_lectionary  # noqa: E402
from armenian_lectionary import engine  # noqa: E402
from dev import source_corrections  # noqa: E402
from dev.fetch_translations import OBSERVANCE_MAP_PATH  # noqa: E402


def _observance_names_hy():
    """The dev-tooling Armenian feast/fast map, loaded from disk.

    The engine never loads this at import -- nothing at runtime reads it since feast
    names resolve through the observance catalog, and it lives under dev/, not in the
    shipped package. The guards below check the FILE anyway (it's still a dev-time input
    to dev/observance_name_review.py and dev/audit_source_anomalies.py), so they read it
    themselves rather than keeping an unused module global alive to hang a test on.
    """
    return engine._load_json_map(OBSERVANCE_MAP_PATH)


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
        # _OBSERVANCE_NAMES_HY directly -- see _resolve_observance_names.
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
        maps = {**_observance_names_hy(), **engine._BOOK_NAMES_HY}
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
        keys = list(_observance_names_hy()) + list(engine._BOOK_NAMES_HY)
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
        feasts = _observance_names_hy()
        if not feasts:
            self.skipTest("feast map not present")
        for v in feasts.values():
            self.assertEqual(v, to_mashtots_names(v),
                             f"reformed proper noun survives in feast {v!r}")


class TestIlluminatorFastIsNamedInBothLanguages(unittest.TestCase):
    """The Fast of St. Gregory the Illuminator counts its five weekdays in BOTH languages.

    The source heads them "Ա/Բ/Գ/Դ/Ե օր Լուսաւորչի պահոց" in Armenian but prints a bare
    "Fast day" in English -- the same two words it uses on 2,139 ordinary fast days. One
    display string standing for six observances is what forced the engine to carry a
    date-scoped side channel to recover the distinction; saying in English what the source
    already says in Armenian retires it, so this pins the English as hard as the Armenian.

    Registered as a repair in source_corrections.illuminator_fast_label, on the standing
    justification that the source contradicts its own other-language statement of the same
    fact.
    """

    _ORDINALS = (("First", "Ա"), ("Second", "Բ"), ("Third", "Գ"),
                 ("Fourth", "Դ"), ("Fifth", "Ե"))

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def _pentecost(self, year):
        return (engine.calculate_gregorian_easter(year)
                + datetime.timedelta(days=49))

    def test_each_fast_day_carries_its_ordinal_in_both_languages(self):
        for year in (2001, 2014, 2026):
            pentecost = self._pentecost(year)
            for n, (word, letter) in enumerate(self._ORDINALS, start=1):
                day = pentecost + datetime.timedelta(days=21 + n)
                with self.subTest(year=year, ordinal=n):
                    en = compute_armenian_lectionary(day)["Liturgical Day"]
                    hy = compute_armenian_lectionary(
                        day, language="hy")["Liturgical Day"]
                    self.assertTrue(
                        en.startswith(
                            f"{word} day of the Fast of St. Gregory the Illuminator"),
                        f"{day} served {en!r}")
                    self.assertTrue(
                        hy.startswith(f"{letter} օր Լուսաւորչի պահոց"),
                        f"{day} served {hy!r}")

    def test_an_ordinary_fast_day_is_not_captured(self):
        """A Wednesday well outside the fast keeps the general, unnumbered label."""
        day = datetime.date(2026, 10, 7)          # ordinary-time Wednesday
        self.assertTrue(compute_armenian_lectionary(
            day, language="hy")["Liturgical Day"].startswith("Պահք"))
        self.assertTrue(compute_armenian_lectionary(
            day)["Liturgical Day"].startswith("Fast day"))

    def test_window_is_closed_at_both_ends(self):
        """The eve (Pentecost+21) and the Discovery of the Relics (+27) are not fast days."""
        pentecost = self._pentecost(2026)
        for offset in (21, 27):
            with self.subTest(offset=offset):
                self.assertIsNone(source_corrections.illuminator_fast_label(
                    (pentecost + datetime.timedelta(days=offset)).isoformat()))

    def test_no_two_observances_share_an_english_name(self):
        """What the repair buys: the catalog's English is now a key, not a hint.

        A duplicate here would mean some component cannot be identified from its text, and
        the engine would need a side channel to tell the collisions apart again.
        """
        seen = {}
        for sid, entry in engine._OBSERVANCE_CATALOG.items():
            self.assertNotIn(
                entry["en"], seen,
                f"{sid} and {seen.get(entry['en'])} share the English {entry['en']!r}")
            seen[entry["en"]] = sid

    def test_storage_tiers_get_the_general_id(self):
        """Text-keyed id resolution has no date, so it must yield the general id.

        If a date-scoped id leaked into dev/observance_ids, every ordinary fast day in the
        shipped table would be stamped with an Illuminator-fast id.
        """
        from dev.observance_ids import ids_for_text
        self.assertEqual(ids_for_text("Fast day"), ["fast_day"])


class TestGeneratedLabelsResolveThroughTheCatalog(unittest.TestCase):
    """A rename of a position/eve label is a TSV edit, not an engine.py edit.

    ``engine._position_label``/``_eve_label`` find a served observance's id from its own
    READINGS (see ``engine._observance_id_from_readings``/``_resolve_generated_text``),
    not from the literal template text -- so once ``observance_readings_index.json`` maps
    that id, editing the catalog's ``en`` for it (what a TSV rebuild does) is enough to
    change what ``compute_armenian_lectionary`` serves. This proves exactly that, with no
    change to ``armenian_lectionary/engine.py`` itself.
    """

    # Pentecost+23 = the fast's day 2 (the window opens at Pentecost+22).
    DAY = (engine.calculate_gregorian_easter(2026) + datetime.timedelta(days=49 + 23))

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG or not engine._OBSERVANCE_ID_BY_READINGS:
            self.skipTest("observance catalog or readings index not present")
        self._orig_catalog = engine._OBSERVANCE_CATALOG
        self.addCleanup(setattr, engine, "_OBSERVANCE_CATALOG", self._orig_catalog)

    def test_editing_the_catalog_changes_served_text_with_no_engine_change(self):
        before = compute_armenian_lectionary(self.DAY)["Liturgical Day"]
        self.assertIn("Second day of the Fast of St. Gregory the Illuminator", before)

        engine._OBSERVANCE_CATALOG = {
            **self._orig_catalog,
            "illuminator_fast_day_2": {
                **self._orig_catalog["illuminator_fast_day_2"],
                "en": "Second day of the Fast of the Renamed Illuminator",
            },
        }
        after = compute_armenian_lectionary(self.DAY)["Liturgical Day"]
        self.assertIn("Second day of the Fast of the Renamed Illuminator", after)
        self.assertNotIn("Second day of the Fast of St. Gregory the Illuminator", after)

    def test_an_uncatalogued_id_falls_back_to_the_literal_template(self):
        """Removing an id from the catalog degrades to the literal text, not a KeyError."""
        engine._OBSERVANCE_CATALOG = {
            sid: v for sid, v in self._orig_catalog.items()
            if sid != "illuminator_fast_day_2"}
        served = compute_armenian_lectionary(self.DAY)["Liturgical Day"]
        self.assertIn("Second day of the Fast of St. Gregory the Illuminator", served)


class TestEveryReadingsIndexedIdResolvesThroughTheCatalog(unittest.TestCase):
    """Every entry in observance_readings_index.json actually overrides, not just one.

    TestGeneratedLabelsResolveThroughTheCatalog proves the MECHANISM on a single
    hand-picked id (Illuminator day 2); this proves COVERAGE across the whole index. A gap
    here would mean dev/build_observance_catalog.py's stability checks let an entry
    through that does not actually round-trip at request time -- a hash collision the
    build-time check missed, or a date the build-time walk sampled that does not
    reproduce the same readings at request time.

    One pass over the full MIN_YEAR..MAX_YEAR range finds one representative date per
    indexed hash (mirroring how dev/build_observance_catalog.py's own walk works); the
    test itself then substitutes a sentinel English string for each entry's catalog id in
    turn and confirms that date's served text picks it up.
    """

    @classmethod
    def setUpClass(cls):
        if not engine._OBSERVANCE_CATALOG or not engine._OBSERVANCE_ID_BY_READINGS:
            raise unittest.SkipTest("observance catalog or readings index not present")
        target_hashes = set(engine._OBSERVANCE_ID_BY_READINGS)
        cls.date_for_hash = {}
        d = datetime.date(engine.MIN_YEAR, 1, 1)
        end = datetime.date(engine.MAX_YEAR, 12, 31)
        while d <= end and len(cls.date_for_hash) < len(target_hashes):
            readings = compute_armenian_lectionary(d).get("ReadingsList")
            if readings:
                # A hash is namespaced by "position" or "eve" (engine.
                # _observance_id_from_readings): a day's readings can match either kind's
                # hash, independently, so both must be tried.
                for kind in ("position", "eve"):
                    h = engine._observance_id_from_readings(readings, kind)
                    if h in target_hashes and h not in cls.date_for_hash:
                        cls.date_for_hash[h] = d
            else:
                # An aliturgical day has no readings to hash at all -- those entries are
                # keyed by calendar coordinate instead (engine._position_coordinate /
                # _observance_id_from_coordinate).
                coordinate = engine._position_coordinate(d)
                if coordinate:
                    h = engine._observance_id_from_coordinate(*coordinate)
                    if h in target_hashes and h not in cls.date_for_hash:
                        cls.date_for_hash[h] = d
            d += datetime.timedelta(days=1)

    def setUp(self):
        self._orig_catalog = engine._OBSERVANCE_CATALOG
        self.addCleanup(setattr, engine, "_OBSERVANCE_CATALOG", self._orig_catalog)

    def test_every_indexed_entry_has_a_representative_date(self):
        """The build-time walk and this test's walk must agree on what is reachable.

        An index entry with no representative date here would mean
        dev/build_observance_catalog.py minted it from a date range this test cannot
        reproduce (a different MIN_YEAR/MAX_YEAR, most likely) -- worth failing loudly on
        rather than silently skipping.
        """
        unreachable = set(engine._OBSERVANCE_ID_BY_READINGS) - set(self.date_for_hash)
        self.assertEqual(
            unreachable, set(),
            f"{len(unreachable)} readings-index id(s) have no date producing their hash "
            f"in {engine.MIN_YEAR}-{engine.MAX_YEAR}")

    def test_every_indexed_id_overrides_on_its_representative_date(self):
        failures = []
        for h, day in self.date_for_hash.items():
            sid = engine._OBSERVANCE_ID_BY_READINGS[h]
            if sid not in self._orig_catalog:
                failures.append((sid, day, "id not in observance catalog"))
                continue
            sentinel = f"RENAMED__{sid}"
            engine._OBSERVANCE_CATALOG = {
                **self._orig_catalog,
                sid: {**self._orig_catalog[sid], "en": sentinel},
            }
            with self.subTest(id=sid, date=day):
                served = compute_armenian_lectionary(day)["Liturgical Day"]
                if sentinel not in served:
                    failures.append((sid, day, served))
            engine._OBSERVANCE_CATALOG = self._orig_catalog
        self.assertEqual(
            failures, [],
            f"{len(failures)}/{len(self.date_for_hash)} readings-indexed id(s) did not "
            "override on their representative date")


if __name__ == "__main__":
    unittest.main()
