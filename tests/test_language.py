"""Unit tests for the language kwarg and the English->Armenian localization layer.

Self-contained: the translation functions are exercised with small injected maps so
these pass without the scraped *_names_hy.json files present.
"""
import datetime
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import compute_armenian_lectionary  # noqa: E402
from armenian_lectionary import engine  # noqa: E402
from armenian_lectionary.observance_catalog import ObservanceCatalog  # noqa: E402
from dev import source_corrections  # noqa: E402
from dev.fetch_translations import OBSERVANCE_MAP_PATH  # noqa: E402
from tests._catalog_expectations import bare_en, bare_hy, text  # noqa: E402


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
        # One assignment, not two: the catalog builds its own reverse index, so a
        # substituted catalog cannot disagree with the index used to read it -- which a
        # hand-built pair could, and which is why the engine needed a staleness check.
        self._orig = engine._OBSERVANCE_CATALOG
        engine._OBSERVANCE_CATALOG = ObservanceCatalog(self.CATALOG)
        self.addCleanup(setattr, engine, "_OBSERVANCE_CATALOG", self._orig)

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
        orig_cat = engine._OBSERVANCE_CATALOG
        orig_b = engine._BOOK_NAMES_HY
        engine._OBSERVANCE_CATALOG = ObservanceCatalog({
            "resurrection": {
                "en": "RESURRECTION OF OUR LORD JESUS CHRIST (Easter Sunday)",
                "hy": "ՅԱՐՈՒԹԻՒՆ"}})
        engine._BOOK_NAMES_HY = {"John": "Ավետարան ըստ Հովհաննեսի",
                                 "Acts of the Apostles": "Գործք առաքելոց",
                                 "Mark": "Ավետարան ըստ Մարկոսի",
                                 "Luke": "Ավետարան ըստ Ղուկասի",
                                 "Matthew": "Ավետարան ըստ Մատթէոսի"}
        try:
            result = compute_armenian_lectionary(self.DATE, language="hy")
        finally:
            engine._OBSERVANCE_CATALOG = orig_cat
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

    Registered as a repair in source_corrections.named_fast_label, on the standing
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
                        en.startswith(f"{word} day of {bare_en('illuminator_fast_day_1')}"),
                        f"{day} served {en!r}")
                    self.assertTrue(
                        hy.startswith(f"{letter} օր {bare_hy('illuminator_fast_day_1')}"),
                        f"{day} served {hy!r}")

    def test_an_ordinary_fast_day_is_not_captured(self):
        """A Wednesday well outside the fast gets no ordinal of the Illuminator's.

        It is not the bare marker any more -- section 6c gives it its weekday -- but that
        is still the *general* label, carrying no day count of a named fast. What this
        guards is the window, so it asserts the ordinary label rather than merely the
        absence of the Illuminator's.
        """
        day = datetime.date(2026, 10, 7)          # ordinary-time Wednesday
        self.assertEqual(compute_armenian_lectionary(
            day, language="hy")["Liturgical Day"], text("wednesday_fast", "hy"))
        self.assertEqual(compute_armenian_lectionary(
            day)["Liturgical Day"], text("wednesday_fast"))

    def test_window_is_closed_at_both_ends(self):
        """The eve (Pentecost+21) and the Discovery of the Relics (+27) are not fast days."""
        pentecost = self._pentecost(2026)
        for offset in (21, 27):
            with self.subTest(offset=offset):
                self.assertIsNone(source_corrections.named_fast_label(
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


class TestNisibisFastIsNamedInBothLanguages(unittest.TestCase):
    """The Fast of St. James the bishop of Nisibis counts its five weekdays, like the
    Illuminator fast above -- but with one witness fewer.

    The source heads all five days "Fast day" in English AND a bare "Պահք" in Armenian, so
    unlike the Illuminator there is no other-language statement to appeal to. What names
    the fast is the source's own EVE on the Sunday before, in both languages, and the
    window is fixed independently by the cache every year (eve at Heesnak+21, saint-fixed
    text on +22..+26, the saint's own commemoration at +27). Registered as a section 6b
    disambiguation in ``source_corrections.named_fast_label`` /
    ``named_fast_label_hy``; this pins the served result of both halves.
    """

    _ORDINALS = (("First", "Ա"), ("Second", "Բ"), ("Third", "Գ"),
                 ("Fourth", "Դ"), ("Fifth", "Ե"))

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def _heesnak(self, year):
        return engine.sunday_closest_to(year, 11, 18)

    def test_each_fast_day_carries_its_ordinal_in_both_languages(self):
        for year in (2001, 2015, 2026):
            heesnak = self._heesnak(year)
            for n, (word, letter) in enumerate(self._ORDINALS, start=1):
                day = heesnak + datetime.timedelta(days=21 + n)
                with self.subTest(year=year, ordinal=n):
                    en = compute_armenian_lectionary(day)["Liturgical Day"]
                    hy = compute_armenian_lectionary(
                        day, language="hy")["Liturgical Day"]
                    self.assertTrue(
                        en.startswith(f"{word} day of {bare_en('james_nisibis_day_1')}"),
                        f"{day} served {en!r}")
                    self.assertTrue(
                        hy.startswith(f"{letter} օր {bare_hy('james_nisibis_day_1')}"),
                        f"{day} served {hy!r}")

    def test_the_day_count_matches_the_eve_that_names_the_fast(self):
        """The eve and the days it opens must read as ONE fast, in both languages.

        This is the whole warrant for the wording: the label is not independently
        attested, it is the eve's own name for the fast carried onto the days it opens. If
        the two ever drift apart, the justification is gone -- and a consumer grouping a
        fast by name would no longer see the eve and its days as the same thing.
        """
        heesnak = self._heesnak(2026)
        eve = heesnak + datetime.timedelta(days=21)
        for lang, fast in (("en", bare_en("james_nisibis_day_1")),
                           ("hy", bare_hy("james_nisibis_day_1"))):
            with self.subTest(lang=lang):
                eve_label = compute_armenian_lectionary(
                    eve, language=lang)["Liturgical Day"]
                self.assertIn(fast, eve_label, f"eve served {eve_label!r}")
                for n in range(1, 6):
                    day = heesnak + datetime.timedelta(days=21 + n)
                    served = compute_armenian_lectionary(
                        day, language=lang)["Liturgical Day"]
                    self.assertIn(fast, served, f"{day} served {served!r}")

    def test_window_is_closed_at_both_ends(self):
        """Heesnak+21 is the eve and +27 is the saint's own day; neither is a fast day."""
        heesnak = self._heesnak(2026)
        for offset in (21, 27):
            with self.subTest(offset=offset):
                iso = (heesnak + datetime.timedelta(days=offset)).isoformat()
                self.assertIsNone(source_corrections.named_fast_label(iso))
                self.assertIsNone(source_corrections.named_fast_label_hy(iso))

    def test_december_ninth_keeps_its_place_in_the_count(self):
        """Dec 9 inside the window is a day of this fast, not an exception to it.

        Suppressing it there would leave the ordinal with a hole in 12 of the 27 supported
        years; the Conception feast rides alongside instead. Mirrored, for the served
        English, by tests/test_observance.TestDecemberNinthFastMarker.
        """
        for year in (2013, 2014, 2015):
            with self.subTest(year=year):
                served = compute_armenian_lectionary(
                    datetime.date(year, 12, 9), language="hy")["Liturgical Day"]
                self.assertIn(f"օր {bare_hy('james_nisibis_day_1')}", served)


class TestProphetElijahFastIsNamedInBothLanguages(unittest.TestCase):
    """The week after Pentecost is the Fast of Prophet Elijah, and now says so.

    The source counts these days "Nth day of Pentecost" / "Ն օր Հոգեգալստեան" -- true, and
    it does not say which fast the reader is in. Its own eve on Pentecost itself does
    ("Eve of Fast of Prophet Elijah" / "Բարեկենդան Եղիական պահոց"), and the Sunday that
    closes the week is the Remembrance of Prophet Elijah, so the fast is named for the
    saint it ends on -- the same shape as the Illuminator and Nisibis fasts.

    Registered on the review rows themselves (``approved_en``/``approved_hy`` on the five
    ``*_of_pentecost`` rows), which is why their ids do NOT move: same observance, more
    specific name.

    The fast is Mon-Fri only: the source marks each of those five days "-- Fast day" in
    English and carries no such marker on the Saturday that follows ("Seventh day of
    Pentecost", bare, in every sampled year) -- so Saturday keeps its plain count instead
    of being renamed into a fast it is not marked as observing. See
    docs/observance-name-corrections.md section 6b.
    """

    # Ordinal ids in order, for offsets 1-5 from Pentecost (Mon-Fri).
    _IDS = ("second_day_of_pentecost", "third_day_of_pentecost", "fourth_day_of_pentecost",
            "fifth_day_of_pentecost", "sixth_day_of_pentecost")

    # Elijah's shape is "Nth day of Pentecost (Fast of the Prophet Elijah)" -- unlike the
    # Illuminator/Nisibis/Varag families' plain "Nth day of X", it keeps the source's own
    # day-of-Pentecost count AND parenthesizes the more specific name (see the class
    # docstring), so the shared bare_en/bare_hy helpers -- which strip "Nth day of " and
    # expect the remainder to be a plain trailing "X"/"...պահոց" -- don't fit. Compared
    # against the catalog's own full text per id instead.
    _PAREN_RE = re.compile(r"\((.+)\)$")

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def _pentecost(self, year):
        return engine.calculate_gregorian_easter(year) + datetime.timedelta(days=49)

    def test_each_fast_day_carries_its_ordinal_in_both_languages(self):
        for year in (2001, 2014, 2026):
            pentecost = self._pentecost(year)
            for offset, sid in enumerate(self._IDS, start=1):
                day = pentecost + datetime.timedelta(days=offset)
                with self.subTest(year=year, offset=offset):
                    en = compute_armenian_lectionary(day)["Liturgical Day"]
                    hy = compute_armenian_lectionary(
                        day, language="hy")["Liturgical Day"]
                    self.assertTrue(
                        en.startswith(text(sid, "en")), f"{day} served {en!r}")
                    self.assertTrue(
                        hy.startswith(text(sid, "hy")), f"{day} served {hy!r}")

    def test_the_day_count_matches_the_eve_that_names_the_fast(self):
        for lang in ("en", "hy"):
            fast = self._PAREN_RE.search(text("second_day_of_pentecost", lang)).group(1)
            with self.subTest(lang=lang):
                pentecost = self._pentecost(2026)
                eve = compute_armenian_lectionary(
                    pentecost, language=lang)["Liturgical Day"]
                self.assertIn(fast, eve, f"eve served {eve!r}")
                for offset in range(1, 6):
                    day = pentecost + datetime.timedelta(days=offset)
                    served = compute_armenian_lectionary(
                        day, language=lang)["Liturgical Day"]
                    self.assertIn(fast, served, f"{day} served {served!r}")

    def test_the_rename_did_not_move_the_ids(self):
        """The point of the whole exercise: correcting a name must not restate the key.

        A consumer that persisted ``second_day_of_pentecost`` for the Monday after
        Pentecost must still resolve it after the rename. Minting a new id here instead
        would strand exactly what 1.3.0 stranded.
        """
        from dev.observance_ids import ids_for_text
        for word, slug in (("Second", "second_day_of_pentecost"),
                           ("Sixth", "sixth_day_of_pentecost")):
            with self.subTest(word=word):
                self.assertEqual(
                    ids_for_text(f"{word} day of {bare_en('second_day_of_pentecost')}"), [slug])


class TestVaragFastIsNamedInBothLanguages(unittest.TestCase):
    """The last fast eve whose days the source left unnamed (docs §6d).

    Nine of the ten fast eves in ``engine._EVE_FAMILIES`` are followed by a named day
    count. The Fast of the Holy Cross of Varag was the tenth: the source names it on its
    own eve and then heads all five days it opens with a bare "Fast day" / "Պահք".

    Two of those five are a Wednesday and a Friday, so before this family existed they fell
    through to the weekly split and were served as the ORDINARY weekly fast -- a day of a
    named fast wearing the name of a different one. That is what the last test here guards,
    and it is the reason this class is not merely cosmetic.
    """

    ORDINALS = (("First", "Ա"), ("Second", "Բ"), ("Third", "Գ"),
                ("Fourth", "Դ"), ("Fifth", "Ե"))

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def _eve(self, year):
        """The Sunday at EX+7 -- the eve the fast's five weekdays follow."""
        return engine._POSITION_ANCHORS["EX"](
            datetime.date(year, 9, 14)) + datetime.timedelta(days=7)

    def test_five_weekdays_are_named_in_both_languages(self):
        for year in (2001, 2015, 2026):
            eve = self._eve(year)
            for k, (word, letter) in enumerate(self.ORDINALS, start=1):
                d = eve + datetime.timedelta(days=k)
                with self.subTest(date=d):
                    en = compute_armenian_lectionary(d)["Liturgical Day"]
                    hy = compute_armenian_lectionary(
                        d, language="hy")["Liturgical Day"]
                    self.assertTrue(
                        en.startswith(f"{word} day of {bare_en('cross_varag_day_1')}"),
                        f"{d} served {en!r}")
                    self.assertTrue(
                        hy.startswith(f"{letter} օր {bare_hy('cross_varag_day_1')}"),
                        f"{d} served {hy!r}")

    def test_the_eve_still_names_the_fast(self):
        """The witness the day labels are taken from, asserted so it cannot quietly move.

        Calls ``engine._eve_label`` directly -- the raw, pre-catalog-override literal --
        so this checks a substring rather than exact equality: once
        tests/test_coordinate_index.py compares by id (not text), this literal's exact
        wording is no longer required to track a rename (it is never actually reachable by
        a real request for a covered family; see that file's docstring). What still
        matters, and what this still catches, is that the raw template names *some* Varag
        fast eve at all.
        """
        for year in (2001, 2026):
            eve = self._eve(year)
            with self.subTest(date=eve):
                self.assertIn(text("eve_of_fast_of_holy_cross_of_varag"), engine._eve_label(eve))

    def test_its_wednesday_and_friday_are_not_the_weekly_fast(self):
        """The defect §6d fixed: two days of this fast were served as the weekly one."""
        for year in (2001, 2015, 2026):
            eve = self._eve(year)
            for k in (3, 5):                      # the Wednesday and the Friday
                d = eve + datetime.timedelta(days=k)
                with self.subTest(date=d):
                    self.assertIn(d.weekday(), (2, 4))
                    served = compute_armenian_lectionary(d)["Liturgical Day"]
                    for split in ("Wednesday Fast", "Friday Fast"):
                        self.assertNotIn(split, served, served)


class TestWeeklyFastWeekdaySplit(unittest.TestCase):
    """The ordinary-time Wed/Fri marker says which weekday's fast it is.

    The weakest-evidenced label in the engine, and the only one with no source witness of
    any kind: the source prints "Fast day"/"Պահք" on both weekdays and never distinguishes
    them. So what these tests guard is not fidelity to the source -- there is nothing to be
    faithful to -- but the SCOPE of the departure. The split must claim the weekly fast and
    nothing else; everywhere the marker means something other than "it is Wednesday" it has
    to survive untouched. See docs/observance-name-corrections.md section 6c.
    """

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def test_ordinary_time_splits_by_weekday_in_both_languages(self):
        for d, en, hy in ((datetime.date(2026, 10, 7),
                           text("wednesday_fast"), text("wednesday_fast", "hy")),
                          (datetime.date(2026, 10, 9),
                           text("friday_fast"), text("friday_fast", "hy"))):
            with self.subTest(date=d):
                self.assertTrue(
                    compute_armenian_lectionary(d)["Liturgical Day"].startswith(en))
                self.assertTrue(compute_armenian_lectionary(
                    d, language="hy")["Liturgical Day"].startswith(hy))

    def test_holy_week_is_not_called_the_weekly_fast(self):
        """Great Wednesday and Great Friday are not the weekly fast.

        They are inside Holy Week, which the source marks on every one of its days --
        Sunday through Saturday, not just Wed/Fri. Calling them the weekly fast would be
        false, and they would fall through to the split without the explicit entry that
        heads them off.

        That entry still matches and still emits "Fast day"; the marker is then dropped as
        a declared decline (docs §6e), so what reaches the reader is the Holy Week name
        alone. Both halves are asserted -- the day is not the weekly fast, and it carries no
        marker restating what "Great Wednesday" already says.
        """
        for d in (datetime.date(2026, 4, 1), datetime.date(2026, 4, 3)):
            with self.subTest(date=d):
                served = compute_armenian_lectionary(d)["Liturgical Day"]
                self.assertTrue(served.startswith("Great "), served)
                for absent in (text("wednesday_fast"), text("friday_fast"), "Fast day"):
                    self.assertNotIn(absent, served, served)

    def test_a_named_fast_outranks_the_split(self):
        """A Wed/Fri inside a named fast is a day OF that fast, not a weekly fast day."""
        for d in (datetime.date(2026, 9, 9),     # Fast of the Holy Cross, a Wednesday
                  datetime.date(2026, 12, 9)):   # Fast of St. James of Nisibis, a Wednesday
            with self.subTest(date=d):
                served = compute_armenian_lectionary(d)["Liturgical Day"]
                self.assertNotIn(text("wednesday_fast"), served, served)
                self.assertIn("day of the Fast of", served)

    def test_the_generative_continua_tier_does_not_suppress_the_split(self):
        """The one tier that named a calendar-derived component in its own words.

        ``_generative_continua`` returned a frozen "Fast day" for the Fast-of-the-Assumption
        Wed/Fri tail. The marker satisfies ``_POSITION_COMPONENT_RE``, so it was taken for
        an already-resolved position and the split never ran -- on 16 summer Wed/Fri days
        across the supported range. The tier now asks ``_position_label``, so it cannot
        disagree with the rule that names every other Wed/Fri (``test_coordinate_index``
        checks that agreement across the whole range).
        """
        for d in (datetime.date(2026, 8, 5), datetime.date(2026, 8, 7)):
            with self.subTest(date=d):
                served = compute_armenian_lectionary(d)["Liturgical Day"]
                self.assertNotIn("Fast day", served, served)
                self.assertTrue(
                    served.startswith((text("wednesday_fast"), text("friday_fast"))), served)

    def test_a_day_the_split_does_not_claim_keeps_its_own_day_count(self):
        """The split is scoped to the terminal fallthrough; it never rewrites a day count.

        Aug 19 2026 is a Wednesday inside no named fast, so it IS the weekly fast -- but the
        source's own "Fourth day of the Assumption" holds the position slot, and that is the
        component a reader needs. The split must not replace it, and the bare marker beside
        it is not served (docs §6e), so the day is its day count and nothing else.

        Asserting the day count is present is the point: this is the test that fails if the
        split ever starts claiming days whose position the source already stated.
        """
        served = compute_armenian_lectionary(
            datetime.date(2026, 8, 19))["Liturgical Day"]
        self.assertEqual(served, text("fourth_day_of_assumption"))
        for absent in (text("wednesday_fast"), text("friday_fast"), "Fast day"):
            self.assertNotIn(absent, served, served)


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

        engine._OBSERVANCE_CATALOG = self._orig_catalog.replacing(
            "illuminator_fast_day_2",
            en="Second day of the Fast of the Renamed Illuminator")
        after = compute_armenian_lectionary(self.DAY)["Liturgical Day"]
        self.assertIn("Second day of the Fast of the Renamed Illuminator", after)
        self.assertNotIn("Second day of the Fast of St. Gregory the Illuminator", after)

    def test_an_uncatalogued_id_falls_back_to_the_literal_template(self):
        """Removing an id from the catalog degrades to the literal text, not a KeyError."""
        engine._OBSERVANCE_CATALOG = ObservanceCatalog(
            {sid: v for sid, v in self._orig_catalog.items()
             if sid != "illuminator_fast_day_2"})
        served = compute_armenian_lectionary(self.DAY)["Liturgical Day"]
        self.assertIn("Second day of the Fast of St. Gregory the Illuminator", served)


class TestNisibisAndElijahRenamesResolveThroughTheCatalog(unittest.TestCase):
    """The specific promise CLAUDE.md makes for these two fasts: a future rename is a
    ``dev/observance_name_review.tsv`` edit (``approved_en``/``approved_hy``) plus a
    rebuild (``build_ground_truth.py`` then ``build_observance_catalog.py``) -- not an
    ``engine.py`` change -- for EVERY day of EITHER fast, not just one hand-picked example.

    Simulates the rebuild's end effect directly, the same way
    ``TestGeneratedLabelsResolveThroughTheCatalog`` does for the Illuminator fast: a TSV
    edit ultimately only changes what ``dev/build_observance_catalog.py`` writes into
    ``observance_catalog.json``, so patching the loaded catalog in place and re-requesting
    the date proves the same mechanism without shelling out to the rebuild scripts.
    """

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG or not engine._OBSERVANCE_ID_BY_READINGS:
            self.skipTest("observance catalog or readings index not present")
        self._orig_catalog = engine._OBSERVANCE_CATALOG
        self.addCleanup(setattr, engine, "_OBSERVANCE_CATALOG", self._orig_catalog)

    @staticmethod
    def _heesnak(year):
        return engine.sunday_closest_to(year, 11, 18)

    @staticmethod
    def _pentecost(year):
        return engine.calculate_gregorian_easter(year) + datetime.timedelta(days=49)

    def _nisibis_cases(self):
        # 2017: Dec 9 (Sat, Heesnak+20) falls OUTSIDE the fast window in every year sharing
        # its weekday, so none of these five days is a Dec-9/Conception composite -- the
        # tier the readings index deliberately excludes from a label's signature (CLAUDE.md
        # "A rename is a TSV edit"). A composite year would fail here for the right reason
        # (that occurrence isn't index-covered), not a wrong one; picking a clean year keeps
        # this test about the rename mechanism, not about composite-day tier exclusion.
        heesnak = self._heesnak(2017)
        ids = ("james_nisibis_day_1", "james_nisibis_day_2", "james_nisibis_day_3",
               "james_nisibis_day_4", "james_nisibis_day_5")
        for n, sid in enumerate(ids, start=1):
            yield sid, heesnak + datetime.timedelta(days=21 + n)

    def _elijah_cases(self):
        pentecost = self._pentecost(2026)
        ids = ("second_day_of_pentecost", "third_day_of_pentecost", "fourth_day_of_pentecost",
               "fifth_day_of_pentecost", "sixth_day_of_pentecost")
        for n, sid in enumerate(ids, start=1):
            yield sid, pentecost + datetime.timedelta(days=n)

    def test_renaming_every_nisibis_or_elijah_id_changes_what_is_served(self):
        for sid, day in list(self._nisibis_cases()) + list(self._elijah_cases()):
            with self.subTest(id=sid):
                original_en = self._orig_catalog[sid]["en"]
                before = compute_armenian_lectionary(day)["Liturgical Day"]
                self.assertIn(original_en, before, f"{day} served {before!r}")

                renamed_en = f"RENAMED {sid}"
                engine._OBSERVANCE_CATALOG = self._orig_catalog.replacing(
                    sid, en=renamed_en)
                after = compute_armenian_lectionary(day)["Liturgical Day"]
                self.assertIn(renamed_en, after, f"{day} served {after!r}")
                self.assertNotIn(original_en, after, f"{day} served {after!r}")

                engine._OBSERVANCE_CATALOG = self._orig_catalog  # restore before next id

    def test_renaming_the_armenian_propagates_too(self):
        """The TSV's ``approved_hy`` column, not just ``approved_en``, reaches ``language="hy"``.

        This is the half that needed ``dev/source_corrections.normalize_position_label_hy``
        to exist at all for Nisibis: unlike the Illuminator fast, the source's own Armenian
        for these days is no more specific than its English, so nothing but the catalog
        entry can supply the served ``hy`` text.
        """
        heesnak = self._heesnak(2017)      # clean year -- see _nisibis_cases
        nisibis_day = heesnak + datetime.timedelta(days=21 + 2)      # james_nisibis_day_2
        pentecost = self._pentecost(2026)
        elijah_day = pentecost + datetime.timedelta(days=1)          # second_day_of_pentecost

        for sid, day in (("james_nisibis_day_2", nisibis_day),
                         ("second_day_of_pentecost", elijah_day)):
            with self.subTest(id=sid):
                original_hy = self._orig_catalog[sid]["hy"]
                before = compute_armenian_lectionary(day, language="hy")["Liturgical Day"]
                self.assertIn(original_hy, before, f"{day} served {before!r}")

                renamed_hy = f"ՎԵՐԱՆՈՒԱՆՈՒԱԾ {sid}"
                engine._OBSERVANCE_CATALOG = self._orig_catalog.replacing(
                    sid, hy=renamed_hy)
                after = compute_armenian_lectionary(day, language="hy")["Liturgical Day"]
                self.assertIn(renamed_hy, after, f"{day} served {after!r}")
                self.assertNotIn(original_hy, after, f"{day} served {after!r}")

                engine._OBSERVANCE_CATALOG = self._orig_catalog  # restore before next id


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
            # A hash is namespaced by "position" or "eve" (engine.
            # _observance_id_from_readings): a day's readings can match either kind's
            # hash, independently, so both must be tried.
            #
            # Both routes are tried on every day, not readings-first-else-coordinate: a
            # coordinate entry is no longer only the aliturgical fallback it once was
            # (engine._position_coordinate / _eve_coordinate), so a day can carry
            # readings and still be some entry's only representative.
            coordinates = {"position": engine._position_coordinate(d),
                           "eve": engine._eve_coordinate(d)}
            for kind in ("position", "eve"):
                hashes = []
                if readings:
                    hashes.append(engine._observance_id_from_readings(readings, kind))
                if coordinates[kind]:
                    hashes.append(engine._observance_id_from_coordinate(
                        *coordinates[kind], kind=kind))
                for h in hashes:
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
            engine._OBSERVANCE_CATALOG = self._orig_catalog.replacing(sid, en=sentinel)
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
