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
        label = "Some Sunday" + engine._FEAST_SEP + \
            "Remembrance of the Armenian Genocide (1915)"
        self.assertEqual(
            engine._resolve_observance_names(label, "hy"),
            "Some Sunday" + engine._FEAST_SEP + "ՀՀ եղեռն")

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

    def test_feasts_use_mashtots_orthography(self):
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
        """A Wednesday well outside the fast gets the weekly split, not a named fast."""
        day = datetime.date(2026, 10, 7)          # ordinary-time Wednesday
        self.assertTrue(compute_armenian_lectionary(
            day, language="hy")["Liturgical Day"].startswith("Չորեքշաբթիի պահք"))
        self.assertTrue(compute_armenian_lectionary(
            day)["Liturgical Day"].startswith("Wednesday Fast"))

    def test_window_is_closed_at_both_ends(self):
        """The eve (Pentecost+21) and the Discovery of the Relics (+27) are not fast days."""
        pentecost = self._pentecost(2026)
        for offset in (21, 27):
            with self.subTest(offset=offset):
                self.assertIsNone(source_corrections.illuminator_fast_label(
                    (pentecost + datetime.timedelta(days=offset)).isoformat()))


class TestWeeklyFastWeekdaySplit(unittest.TestCase):
    """The ordinary-time Wed/Fri marker says which weekday's fast it is.

    The weakest-evidenced label in the engine, and the only one with no source witness of
    any kind: the source prints "Fast day"/"Պահք" on both weekdays and never distinguishes
    them. So what these tests guard is not fidelity to the source -- there is nothing to be
    faithful to -- but the SCOPE of the departure. The split must claim the weekly fast and
    nothing else; everywhere the marker means something other than "it is Wednesday" it has
    to survive untouched. See docs/feast-name-corrections.md section 6c.
    """

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def test_ordinary_time_splits_by_weekday_in_both_languages(self):
        for d, en, hy in ((datetime.date(2026, 10, 7), "Wednesday Fast", "Չորեքշաբթիի պահք"),
                          (datetime.date(2026, 10, 9), "Friday Fast", "Ուրբաթի պահք")):
            with self.subTest(date=d):
                self.assertTrue(
                    compute_armenian_lectionary(d)["Liturgical Day"].startswith(en))
                self.assertTrue(compute_armenian_lectionary(
                    d, language="hy")["Liturgical Day"].startswith(hy))

    def test_holy_week_keeps_the_bare_marker(self):
        """Great Wednesday and Great Friday are not the weekly fast.

        They are inside Holy Week, which the source marks on every one of its days --
        Sunday through Saturday, not just Wed/Fri. Calling them the weekly fast would be
        false, and they would fall through to the split without the explicit entry that
        heads them off.
        """
        for d in (datetime.date(2026, 4, 1), datetime.date(2026, 4, 3)):
            with self.subTest(date=d):
                served = compute_armenian_lectionary(d)["Liturgical Day"]
                self.assertIn("Fast day", served)
                for split in ("Wednesday Fast", "Friday Fast"):
                    self.assertNotIn(split, served, served)

    def test_a_named_fast_outranks_the_split(self):
        """A Wed/Fri inside a named fast is a day OF that fast, not a weekly fast day."""
        for d in (datetime.date(2026, 9, 9),     # Fast of the Holy Cross, a Wednesday
                  datetime.date(2026, 12, 9)):   # Fast of St. James of Nisibis, a Wednesday
            with self.subTest(date=d):
                served = compute_armenian_lectionary(d)["Liturgical Day"]
                self.assertNotIn("Wednesday Fast", served, served)
                self.assertIn("day of the Fast of", served)

    def test_the_stored_marker_does_not_suppress_the_split(self):
        """A day whose whole STORED name is the marker still gets the split.

        The marker satisfies ``_POSITION_COMPONENT_RE``, so before the supersede step in
        ``_apply_position_label`` it was returned as an already-resolved position and the
        split never ran -- on 16 summer Wed/Fri days across the supported range.
        """
        for d in (datetime.date(2026, 8, 5), datetime.date(2026, 8, 7)):
            with self.subTest(date=d):
                served = compute_armenian_lectionary(d)["Liturgical Day"]
                self.assertNotIn("Fast day", served, served)
                self.assertTrue(served.startswith(("Wednesday Fast", "Friday Fast")), served)

    def test_the_marker_still_reaches_days_the_split_does_not_claim(self):
        """The 518 instances the split does not claim, most beside the source's own day count.

        "Fourth day of the Assumption — Fast day" is the source's own wording, and the
        second component is not redundant with the first. Dropping it would be an omission,
        not a cleanup -- which is why the supersede step is scoped to the split.

        Note this particular day is one of the 108 that ARE the weekly fast (Aug 19 2026 is
        a Wednesday, inside no named fast) and are left unsplit only because the position
        slot is held by stored text. It is asserted here as an is-not-a-will-be: docs 6c
        declares it a loose end, so if a later change splits it, this test should be the
        thing that notices.
        """
        served = compute_armenian_lectionary(
            datetime.date(2026, 8, 19))["Liturgical Day"]
        self.assertIn("Fast day", served)
        self.assertIn("day of the Assumption", served)


class TestNisibisFastIsNamedInBothLanguages(unittest.TestCase):
    """The Fast of St. James the bishop of Nisibis counts its five weekdays, like the
    Illuminator fast above -- but with one witness fewer.

    The source heads all five days "Fast day" in English AND a bare "Պահք" in Armenian, so
    unlike the Illuminator there is no other-language statement to appeal to. What names
    the fast is the source's own EVE on the Sunday before, in both languages, and the
    window is fixed independently by the cache every year (eve at Heesnak+21, saint-fixed
    text on +22..+26, the saint's own commemoration at +27). Registered as a section 6
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
                        en.startswith(
                            f"{word} day of the Fast of St. James the bishop of Nisibis"),
                        f"{day} served {en!r}")
                    self.assertTrue(
                        hy.startswith(f"{letter} օր Ս. Յակովբայ պահոց"),
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
        for lang, fast in (("en", "Fast of St. James the bishop of Nisibis"),
                           ("hy", "Ս. Յակովբայ պահոց")):
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
        English, by tests/test_feast.TestDecemberNinthFastMarker.
        """
        for year in (2015, 2020, 2026):
            with self.subTest(year=year):
                served = compute_armenian_lectionary(
                    datetime.date(year, 12, 9), language="hy")["Liturgical Day"]
                self.assertIn("օր Ս. Յակովբայ պահոց", served)


class TestProphetElijahFastIsNamedInBothLanguages(unittest.TestCase):
    """The week after Pentecost is the Fast of Prophet Elijah, and now says so.

    The source counts these days "Nth day of Pentecost" / "Ն օր Հոգեգալստեան" -- true, and
    it does not say which fast the reader is in. Its own eve on Pentecost itself does
    ("Eve of Fast of Prophet Elijah" / "Բարեկենդան Եղիական պահոց"), and the Sunday that
    closes the week is the Remembrance of Prophet Elijah, so the fast is named for the
    saint it ends on -- the same shape as the Illuminator and Nisibis fasts.

    Registered on the review rows themselves (``approved_en``/``approved_hy`` on the six
    ``*_of_pentecost`` rows), which is why their ids do NOT move: same observance, more
    specific name. ``tests/test_observance_ids`` would catch it if they did.
    """

    _ORDINALS = (("Second", "Բ"), ("Third", "Գ"), ("Fourth", "Դ"),
                 ("Fifth", "Ե"), ("Sixth", "Զ"), ("Seventh", "Է"))

    def setUp(self):
        if not engine._OBSERVANCE_CATALOG:
            self.skipTest("observance catalog not present")

    def _pentecost(self, year):
        return engine.calculate_gregorian_easter(year) + datetime.timedelta(days=49)

    def test_each_fast_day_carries_its_ordinal_in_both_languages(self):
        for year in (2001, 2014, 2026):
            pentecost = self._pentecost(year)
            for offset, (word, letter) in enumerate(self._ORDINALS, start=1):
                day = pentecost + datetime.timedelta(days=offset)
                with self.subTest(year=year, offset=offset):
                    en = compute_armenian_lectionary(day)["Liturgical Day"]
                    hy = compute_armenian_lectionary(
                        day, language="hy")["Liturgical Day"]
                    self.assertTrue(
                        en.startswith(f"{word} day of the Fast of Prophet Elijah"),
                        f"{day} served {en!r}")
                    self.assertTrue(hy.startswith(f"{letter} օր Եղիական պահոց"),
                                    f"{day} served {hy!r}")

    def test_the_day_count_matches_the_eve_that_names_the_fast(self):
        for lang, fast in (("en", "Fast of Prophet Elijah"), ("hy", "Եղիական պահոց")):
            with self.subTest(lang=lang):
                pentecost = self._pentecost(2026)
                eve = compute_armenian_lectionary(
                    pentecost, language=lang)["Liturgical Day"]
                self.assertIn(fast, eve, f"eve served {eve!r}")
                for offset in range(1, 7):
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
                           ("Seventh", "seventh_day_of_pentecost")):
            with self.subTest(word=word):
                self.assertEqual(
                    ids_for_text(f"{word} day of the Fast of Prophet Elijah"), [slug])
        # ...and the pre-rename display text must NOT resolve to a second id. It is
        # retired wording, not a second live observance -- the duplicate row that would
        # have created one is what dev/feast_name_review.build_rows now suppresses.
        with self.assertRaises(KeyError):
            ids_for_text("Second day of Pentecost")

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


if __name__ == "__main__":
    unittest.main()
