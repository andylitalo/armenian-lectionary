"""Regression tests for deterministic annual Oratsouyts extraction."""

import datetime
import unittest
from pathlib import Path
from unittest import mock

from dev.oratsouyts.extract import (
    LogicalChunk,
    PageSize,
    SourceSpec,
    WEEKDAY_CODES,
    build_records,
    extract_heading,
    heading_comparison_key,
    _mode_for_date,
    normalize_entry,
    scan_headers,
    select_new_calendar_headers,
)


class TestOratsouytsExtraction(unittest.TestCase):
    def test_mode_validation_uses_tone_from_structured_mode(self):
        self.assertEqual(_mode_for_date(datetime.date(2026, 7, 29)), "ԲԿ")

    def test_soft_hyphen_fragments_are_rejoined_across_whitespace(self):
        source = "1 † Շբ. ԱՁ. Գ օր Ս. Ծնն\u00ad դեան պա\u00ad\nհոց:"
        self.assertEqual(
            normalize_entry(source, legacy_encoding=False),
            "1 † Շբ. ԱՁ. Գ օր Ս. Ծննդեան պահոց:",
        )

    def test_raw_header_accepts_marginal_lunar_day_and_tight_holy_week(self):
        chunk = LogicalChunk(
            logical_index=0,
            physical_page=23,
            column="left",
            raw_text="18 † Աւագ Եշ. ԳԿ. Պահք:",
            raw_order_text="13 18 † Ա\u00ad ւագԵշ. ԳԿ. Պահք:",
        )

        layout = scan_headers([chunk], False, extraction_mode="layout")
        raw = scan_headers([chunk], False, extraction_mode="raw")

        self.assertEqual(len(layout), 1)
        self.assertEqual(len(raw), 1)
        self.assertEqual(raw[0].day, 18)
        self.assertEqual(raw[0].marginal_lunar_day, 13)
        self.assertTrue(raw[0].holy_week)
        self.assertEqual(raw[0].weekday, "Եշ")
        self.assertEqual(raw[0].mode, "ԳԿ")
        self.assertTrue(raw[0].mode_period)

    def test_mode_without_printed_period_remains_a_mode(self):
        chunk = LogicalChunk(
            logical_index=0,
            physical_page=156,
            column="whole",
            raw_text="13 Եշ. ԱՁ Սրբոցն Դիոնէսիոսի:",
            raw_order_text="13 Եշ. ԱՁ Սրբոցն Դիոնէսիոսի:",
        )

        header = scan_headers([chunk], False, extraction_mode="raw")[0]

        self.assertEqual(header.mode, "ԱՁ")
        self.assertFalse(header.mode_period)

    def test_both_extraction_modes_can_align_a_complete_year(self):
        layout_lines = []
        raw_lines = []
        day = datetime.date(2019, 1, 1)
        while day.year == 2019:
            weekday = WEEKDAY_CODES[day.weekday()]
            layout_lines.append("%d %s. ԱՁ. Պահք:" % (day.day, weekday))
            if day == datetime.date(2019, 4, 18):
                raw_lines.append(
                    "13 18 † Աւագ%s. ԱՁ. Պահք:" % weekday
                )
            else:
                raw_lines.append(
                    "%d %s. ԱՁ. Պահք:" % (day.day, weekday)
                )
            day += datetime.timedelta(days=1)
        chunk = LogicalChunk(
            logical_index=0,
            physical_page=1,
            column="whole",
            raw_text="\n".join(layout_lines),
            raw_order_text="\n".join(raw_lines),
        )

        layout, layout_runs = select_new_calendar_headers(
            2019, scan_headers([chunk], False, extraction_mode="layout")
        )
        raw, raw_runs = select_new_calendar_headers(
            2019, scan_headers([chunk], False, extraction_mode="raw")
        )

        self.assertEqual(len(layout), 365)
        self.assertEqual(len(raw), 365)
        self.assertEqual(layout_runs, [0])
        self.assertEqual(raw_runs, [0])

    def test_raw_calendar_clause_wins_and_layout_disagreement_is_preserved(self):
        layout_lines = []
        raw_lines = []
        day = datetime.date(2022, 1, 1)
        while day.year == 2022:
            weekday = WEEKDAY_CODES[day.weekday()]
            if day == datetime.date(2022, 1, 1):
                # Mirrors the Poppler -layout omission in the 2022 source.
                layout_lines.append(
                    "1 † %s. ԱՁ. Գ օր Ս. Ծնն\n"
                    "Սրբոցն Բարսղի Հայրապետին: Օրհ. աձ. Շարական:" % weekday
                )
                raw_lines.append(
                    "1 † %s. ԱՁ. Գ օր Ս. Ծնն\u00ad դեան պա\u00ad հոց: "
                    "Օրհ. աձ. Շարական:"
                    % weekday
                )
            else:
                line = "%d %s. ԱՁ. Պահք:" % (day.day, weekday)
                layout_lines.append(line)
                raw_lines.append(line)
            day += datetime.timedelta(days=1)
        chunk = LogicalChunk(
            logical_index=0,
            physical_page=1,
            column="whole",
            raw_text="\n".join(layout_lines),
            raw_order_text="\n".join(raw_lines),
        )
        source = SourceSpec(
            year=2022,
            path=Path("/private/tmp/fixture.pdf"),
            sha256="fixture",
            page_sizes=(PageSize(physical_page=1, width=248, height=354),),
            legacy_encoding=False,
        )

        with mock.patch(
            "dev.oratsouyts.extract._mode_for_date", return_value="ԱՁ"
        ):
            extracted = build_records(source, [chunk])

        january_first = extracted["records"][0]
        self.assertEqual(
            january_first["calendar_clause"], "Գ օր Ս. Ծննդեան պահոց:"
        )
        self.assertEqual(january_first["semantic_source"], "poppler_raw")
        self.assertIn(
            "calendar_clause_text", january_first["extraction_disagreements"]
        )
        self.assertIn(
            "Սրբոցն Բարսղի",
            january_first["extraction_variants"]["poppler_layout"][
                "calendar_clause"
            ],
        )
        self.assertNotEqual(
            heading_comparison_key(
                january_first["extraction_variants"]["poppler_layout"][
                    "calendar_clause"
                ]
            ),
            heading_comparison_key(january_first["calendar_clause"]),
        )
        self.assertEqual(
            extract_heading(january_first["normalized_text"]),
            january_first["calendar_clause"],
        )

    def test_calendar_clause_preserves_overlapping_fast_and_marian_facts(self):
        entry = (
            "9 † Դշ. ԱՁ. Պահք: Յղութիւն Ս. Աստուածածնի յԱննայէ: "
            "Զկնի Ռահ գործեալին երգ: Օրհ. գկ. Երգեցէք որդիք:"
        )

        self.assertEqual(
            extract_heading(entry),
            "Պահք: Յղութիւն Ս. Աստուածածնի յԱննայէ: "
            "Զկնի Ռահ գործեալին երգ:",
        )


if __name__ == "__main__":
    unittest.main()
