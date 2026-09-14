"""Unit and corpus tests for the versification alignment first pass (engine.py).

Covers four things the spec makes contractual:

  1. **The data file loads what it claims** -- exactly 3 ``realigned`` and 5 ``misaligned``
     records, ``mapped`` present on the former and absent on the latter.
  2. **Each of the 8 records produces the expected ``alignment`` block** on the ref it keys,
     and a ref with no record carries **no ``alignment`` key at all** -- absence is the
     encoding of "no known issue", so an empty-or-null block would be a different contract.
  3. **The 99% is untouched.** Over 2001-2027, ``alignment`` is the ONLY key any ref gains
     and no other field moves; the flagged set is exactly the 8 spans.
  4. **Every ``mapped`` span exists in KJV.** The chapter lengths below are transcribed from
     the Copenhagen Alliance ``eng.json`` ``maxVerses`` table (see the class docstring);
     they are literals here because that file is not shipped with this package and the
     suite is self-contained.

Self-contained: no ground-truth cache, no network.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary import compute_armenian_lectionary  # noqa: E402
from armenian_lectionary import engine  # noqa: E402


# (book, start_chapter, start_verse, end_chapter, end_verse) exactly as ReadingsRefs
# spells it, per record. The spec keys on this tuple and NOT on the citation string:
# "Daniel 3.1-23, Azariah. 1-68" is one citation over two refs, and only the Azariah half
# diverges.
REALIGNED = {
    ("Hosea", 14, 6, 14, 7): ("HOS-14-6-7-endshift", (14, 5, 14, 6)),
    ("Hosea", 14, 9, 14, 10): ("HOS-14-9-10-endshift", (14, 8, 14, 9)),
    ("Joel", 3, 9, 3, 22): ("JOL-3-9-22-endshift", (3, 9, 3, 21)),
}

MISALIGNED = {
    ("Esther", 10, 4, 10, 9): ("EST-10-4-9-relocation", "relocation"),
    ("St. Paul's Epistle to the Romans", 13, 11, 14, 26):
        ("ROM-13-11-14-26-relocation", "relocation"),
    ("St. Paul's Epistle to the Romans", 16, 17, 16, 27):
        ("ROM-16-17-27-reordering", "reordering"),
    ("Song of Solomon", 6, 9, 8, 13): ("SNG-6-9-8-13-reordering", "reordering"),
    ("Azariah", 1, 1, 1, 68): ("AZA-1-1-68-composite", "composite"),
}

ALL_FLAGGED = set(REALIGNED) | set(MISALIGNED)


class TestAlignmentDataFile(unittest.TestCase):
    """The shipped table itself, before any ref touches it."""

    def test_counts(self):
        records = engine._VERSE_ALIGNMENT["records"]
        self.assertEqual(len(records), 8)
        by_status = {}
        for r in records:
            by_status.setdefault(r["status"], []).append(r)
        self.assertEqual(sorted(by_status), ["misaligned", "realigned"])
        self.assertEqual(len(by_status["realigned"]), 3)
        self.assertEqual(len(by_status["misaligned"]), 5)

    def test_status_vocabulary_excludes_aligned(self):
        """``"aligned"`` is never a stored status -- it is the absence of a record."""
        for r in engine._VERSE_ALIGNMENT["records"]:
            self.assertIn(r["status"], ("realigned", "misaligned"))

    def test_mapped_present_exactly_on_realigned(self):
        for r in engine._VERSE_ALIGNMENT["records"]:
            self.assertEqual("mapped" in r, r["status"] == "realigned", r["id"])

    def test_ids_are_unique(self):
        ids = [r["id"] for r in engine._VERSE_ALIGNMENT["records"]]
        self.assertEqual(len(set(ids)), len(ids))

    def test_every_record_carries_provenance(self):
        for r in engine._VERSE_ALIGNMENT["records"]:
            self.assertTrue(r["note"].strip(), r["id"])
            self.assertTrue(r["evidence"].strip(), r["id"])
            self.assertIsInstance(r["confirmed"], bool)

    def test_song_of_solomon_is_not_claimed_as_confirmed(self):
        """Record 7 was flagged by automated comparison and never read against the text.
        Claiming otherwise is the exact mistake the evidence rules exist to prevent."""
        record = next(r for r in engine._VERSE_ALIGNMENT["records"]
                      if r["book"] == "Song of Solomon")
        self.assertFalse(record["confirmed"])

    def test_index_is_keyed_on_the_span_tuple(self):
        self.assertEqual(set(engine._ALIGNMENT_BY_SPAN), ALL_FLAGGED)


class TestMappedSpansExistInKjv(unittest.TestCase):
    """Every corrected span must address verses KJV actually has.

    Chapter lengths transcribed from the Copenhagen Alliance standard mapping
    ``eng.json`` (``maxVerses``): the authority for what a KJV verse address means. Only
    the books this pass realigns are listed.
    """
    KJV_CHAPTER_VERSES = {
        "Hosea": {14: 9},
        "Joel": {3: 21},
    }

    def test_mapped_spans_fit_their_chapter(self):
        for record in engine._VERSE_ALIGNMENT["records"]:
            if record["status"] != "realigned":
                continue
            lengths = self.KJV_CHAPTER_VERSES[record["book"]]
            m = record["mapped"]
            for ch, vs in ((m["start_chapter"], m["start_verse"]),
                           (m["end_chapter"], m["end_verse"])):
                self.assertLessEqual(vs, lengths[ch],
                                     f"{record['id']} maps past the end of KJV "
                                     f"{record['book']} {ch}")

    def test_the_originals_are_what_needed_fixing(self):
        """Joel 3.22 and Hosea 14.10 overshoot their KJV chapter outright; Hosea 14.6-7
        does NOT -- it sits inside the chapter and fetches the wrong two verses in
        silence. That asymmetry is why the notice refuses to call unflagged readings
        verified."""
        lengths = self.KJV_CHAPTER_VERSES
        self.assertGreater(22, lengths["Joel"][3])
        self.assertGreater(10, lengths["Hosea"][14])
        self.assertLessEqual(7, lengths["Hosea"][14])


class TestAlignmentBlockShape(unittest.TestCase):
    """Each record, as served on the ref it keys."""

    def _block(self, key):
        book, sc, sv, ec, ev = key
        return engine._ALIGNMENT_BY_SPAN[engine._span_key(
            {"book": book, "start_chapter": sc, "start_verse": sv,
             "end_chapter": ec, "end_verse": ev})]

    def test_realigned_blocks(self):
        for key, (rid, mapped) in REALIGNED.items():
            block = self._block(key)
            self.assertEqual(block["status"], "realigned", rid)
            self.assertEqual(block["id"], rid)
            self.assertEqual(block["kind"], "endpoint-shift", rid)
            self.assertEqual(block["target"], "kjv", rid)
            self.assertEqual(
                (block["mapped"]["start_chapter"], block["mapped"]["start_verse"],
                 block["mapped"]["end_chapter"], block["mapped"]["end_verse"]),
                mapped, rid)

    def test_misaligned_blocks_carry_no_mapped_span(self):
        for key, (rid, kind) in MISALIGNED.items():
            block = self._block(key)
            self.assertEqual(block["status"], "misaligned", rid)
            self.assertEqual(block["id"], rid)
            self.assertEqual(block["kind"], kind, rid)
            self.assertEqual(block["target"], "kjv", rid)
            self.assertNotIn("mapped", block, rid)

    def test_hosea_both_readings_shift_by_one(self):
        """The whole Grabar chapter runs one ahead of KJV, so both readings move by -1 --
        the fact that makes these an endpoint shift rather than two coincidences."""
        for key, (_rid, mapped) in REALIGNED.items():
            if key[0] != "Hosea":
                continue
            self.assertEqual((mapped[1], mapped[3]), (key[2] - 1, key[4] - 1))

    def test_joel_start_is_identity_only_the_end_moves(self):
        key = ("Joel", 3, 9, 3, 22)
        _rid, mapped = REALIGNED[key]
        self.assertEqual((mapped[0], mapped[1]), (key[1], key[2]))
        self.assertEqual(mapped[3], key[4] - 1)


class TestAlignmentOnServedRefs(unittest.TestCase):
    def test_flagged_ref_gains_the_block(self):
        refs = engine._build_readings_refs(["Hosea 14.9-10"])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["alignment"]["id"], "HOS-14-9-10-endshift")
        self.assertEqual(refs[0]["alignment"]["mapped"],
                         {"start_chapter": 14, "start_verse": 8,
                          "end_chapter": 14, "end_verse": 9})

    def test_original_span_is_never_rewritten(self):
        ref = engine._build_readings_refs(["Hosea 14.9-10"])[0]
        self.assertEqual((ref["start_chapter"], ref["start_verse"],
                          ref["end_chapter"], ref["end_verse"]), (14, 9, 14, 10))
        self.assertEqual(ref["citation"], "Hosea 14.9-10")

    def test_unflagged_ref_has_no_alignment_key_at_all(self):
        """Absent, not null and not empty: an absent key is what "no known issue" means."""
        ref = engine._build_readings_refs(["John 3.16"])[0]
        self.assertNotIn("alignment", ref)

    def test_composite_flags_only_the_azariah_half(self):
        refs = engine._build_readings_refs(["Daniel 3.1-23, Azariah. 1-68"])
        self.assertEqual([r["book"] for r in refs], ["Daniel", "Azariah"])
        self.assertNotIn("alignment", refs[0])
        self.assertEqual(refs[1]["alignment"]["id"], "AZA-1-1-68-composite")

    def test_joel_3_1_8_is_identity_and_unflagged(self):
        """Checked and found to be true identity. Its neighbour Joel 3.9-22 is not."""
        self.assertNotIn("alignment", engine._build_readings_refs(["Joel 3.1-8"])[0])

    def test_blocks_are_copies_not_the_shared_index_entry(self):
        """One import-scoped index entry must not be aliased into every result, or a
        consumer editing one day's alignment edits every other day's."""
        a = engine._build_readings_refs(["Hosea 14.9-10"])[0]["alignment"]
        b = engine._build_readings_refs(["Hosea 14.9-10"])[0]["alignment"]
        self.assertEqual(a, b)
        self.assertIsNot(a, b)
        self.assertIsNot(a["mapped"], b["mapped"])
        a["mapped"]["start_verse"] = 999
        self.assertEqual(
            engine._build_readings_refs(["Hosea 14.9-10"])[0]
            ["alignment"]["mapped"]["start_verse"], 8)


class TestThinCheckoutDegradesToNothingFlagged(unittest.TestCase):
    """An absent data file is a supported state for every shipped data file here. The
    alignment table is no exception: no record loads, no ref is flagged, and the notice
    still ships -- which is the right answer, since without the table nothing IS known."""

    def test_absent_file_loads_as_empty(self):
        missing = os.path.join(os.path.dirname(engine.VERSE_ALIGNMENT_PATH),
                               "no-such-verse-alignment.json")
        self.assertFalse(os.path.exists(missing))
        self.assertEqual(engine._load_json_map(missing), {})
        self.assertEqual(engine._build_alignment_index({}), {})

    def test_empty_index_flags_nothing_and_counts_zero(self):
        refs = [{"book": "Hosea", "start_chapter": 14, "start_verse": 9,
                 "end_chapter": 14, "end_verse": 10, "citation": "Hosea 14.9-10"}]
        self.assertEqual(engine._versification_notice(refs)["counts"],
                         {"realigned": 0, "misaligned": 0})


class TestVersificationNotice(unittest.TestCase):
    DATE = datetime.date(2026, 4, 5)  # Easter: a validated-table day

    def test_present_on_every_result(self):
        notice = compute_armenian_lectionary(self.DATE)["VersificationNotice"]
        self.assertEqual(notice["source"], "grabar-tonatsoyts")
        self.assertEqual(notice["target"], "kjv")
        self.assertEqual(notice["policy"], "endpoint-shift-only")

    def test_detail_keeps_the_not_exhaustive_sentence(self):
        """Load-bearing and not to be softened: Hosea 14.6-7 is silently wrong while
        overshooting nothing, so an unflagged reading is unflagged, never verified."""
        detail = compute_armenian_lectionary(self.DATE)["VersificationNotice"]["detail"]
        self.assertIn("best-effort and not exhaustive", detail)
        self.assertIn("unflagged, not verified", detail)

    def test_counts_describe_this_day(self):
        refs = engine._build_readings_refs(
            ["Hosea 14.9-10", "Joel 3.9-22", "Esther 10.4-9", "John 3.16"])
        self.assertEqual(engine._versification_notice(refs)["counts"],
                         {"realigned": 2, "misaligned": 1})

    def test_counts_are_zero_when_nothing_is_flagged(self):
        self.assertEqual(
            engine._versification_notice(engine._build_readings_refs(["John 3.16"]))
            ["counts"], {"realigned": 0, "misaligned": 0})

    def test_notice_is_not_shared_between_results(self):
        a = compute_armenian_lectionary(self.DATE)["VersificationNotice"]
        b = compute_armenian_lectionary(self.DATE)["VersificationNotice"]
        self.assertIsNot(a, b)
        self.assertIsNot(a["counts"], b["counts"])


class TestAlignmentStaysEnglishUnderHy(unittest.TestCase):
    """Alignment text is an engine annotation about two numbering systems, not scraped
    source text -- the same class as ``Source``/``Note``, which ``_localize`` leaves
    alone."""
    DATE = datetime.date(2026, 4, 5)

    def test_readings_refs_identical_across_languages(self):
        en = compute_armenian_lectionary(self.DATE, language="en")
        hy = compute_armenian_lectionary(self.DATE, language="hy")
        self.assertEqual(en["ReadingsRefs"], hy["ReadingsRefs"])
        self.assertEqual(en["VersificationNotice"], hy["VersificationNotice"])


class TestCorpusIsOtherwiseUntouched(unittest.TestCase):
    """The guard that the ~99% did not move: over the full supported range, ``alignment``
    is the only key any ref gains, and exactly the 8 specced spans carry it."""

    def test_only_the_eight_spans_are_flagged(self):
        d = datetime.date(2001, 1, 1)
        end = datetime.date(2027, 12, 31)
        one = datetime.timedelta(days=1)
        seen = set()
        while d <= end:
            result = compute_armenian_lectionary(d)
            for ref in result["ReadingsRefs"]:
                span = (ref["book"], ref["start_chapter"], ref["start_verse"],
                        ref["end_chapter"], ref["end_verse"])
                self.assertEqual(sorted(ref),
                                 sorted(["book", "start_chapter", "start_verse",
                                         "end_chapter", "end_verse", "citation"]
                                        + (["alignment"] if span in ALL_FLAGGED else [])),
                                 f"unexpected ReadingsRefs keys on {d} for {span}")
                if "alignment" in ref:
                    seen.add(span)
            d += one
        self.assertEqual(seen, ALL_FLAGGED)


if __name__ == "__main__":
    unittest.main()
