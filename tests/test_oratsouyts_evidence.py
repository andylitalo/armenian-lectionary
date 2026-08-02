"""Contracts for conservative Oratsouyts calendar evidence."""

import unittest

from dev.oratsouyts.evidence import (
    augment_saint_classes_from_aligned_layout,
    classify_explicit_record,
    resolve_year_fast_contexts,
)


def _classify(date, clause, *, holy_week=False):
    return classify_explicit_record(
        {
            "date": date,
            "calendar_clause": clause,
            "header": {"dagger": False, "holy_week_prefix": holy_week},
        }
    )


class TestOratsouytsEvidence(unittest.TestCase):
    def test_varaga_fast_emits_only_its_specific_occurrence(self):
        evidence = _classify(
            "2026-09-21", "Ա օր Վարագայ Սրբոյ Խաչի պահոց:"
        )

        self.assertEqual(
            evidence["facts"]["fast_context"]["value"],
            "fast_of_varaga_cross",
        )
        self.assertEqual(
            [item["id"] for item in evidence["occurrences"]],
            ["fast:varaga_cross"],
        )

    def test_layout_can_restore_class_but_not_create_saints_day(self):
        raw_saint = _classify(
            "2026-08-01",
            "Սրբոց հայրապետացն Աթանասի եւ Կիւրղի եւ Գրիգորի Աս տուածաբանին:",
        )
        layout_saint = _classify(
            "2026-08-01",
            "Սրբոց հայրապետացն Աթանասի եւ Կիւրղի եւ Գրիգորի Աստուածաբանին:",
        )
        augment_saint_classes_from_aligned_layout(raw_saint, layout_saint)

        self.assertEqual(
            raw_saint["facts"]["saint_classes"]["value"],
            ["hierarch", "vartapet"],
        )

        raw_marian = _classify(
            "2026-09-08",
            "Տօն Ծննդեան Սրբուհւոյ Կուսին Մարիամու յԱննայէ:",
        )
        broken_layout = _classify(
            "2026-09-08",
            "Տօն Ծննդեան Սրբուհւոյ 18 Կուսին Մարիամու յԱննայէ:",
        )
        augment_saint_classes_from_aligned_layout(raw_marian, broken_layout)

        self.assertIsNone(raw_marian["facts"]["is_saints_day"]["value"])
        self.assertIsNone(raw_marian["facts"]["saint_classes"]["value"])

    def test_descriptor_survives_a_running_header_inside_hyphenation(self):
        evidence = _classify(
            "2016-12-17",
            "Սրբոցն Յակովբայ Մծբնայ հայրապետին, Մարուգէի "
            "ճգնաւո- 180 ԴԵԿՏԵՄԲԵՐ Օ Լ 18 19 20 րին եւ Մելիտոսի "
            "եպիսկոպոսին:",
        )

        self.assertEqual(
            evidence["facts"]["saint_classes"]["value"],
            ["hierarch", "monastic"],
        )

    def test_holy_week_emits_context_and_canonical_occurrence(self):
        evidence = classify_explicit_record(
            {
                "date": "2026-03-30",
                "calendar_clause": "Պահք:",
                "normalized_text": "30 Աւագ Բշ. ԴԿ. Պահք:",
                "header": {"holy_week_prefix": True, "dagger": False},
            }
        )

        self.assertTrue(evidence["facts"]["is_fast_day"]["value"])
        self.assertEqual(evidence["facts"]["fast_context"]["value"], "holy_week")
        self.assertIn(
            "fast:holy_week",
            {occurrence["id"] for occurrence in evidence["occurrences"]},
        )

    def test_named_fast_survives_missing_extraction_spaces(self):
        evidence = classify_explicit_record(
            {
                "date": "2014-11-20",
                "calendar_clause": "ԴօրՅիսնակացպահոց:",
                "normalized_text": "20 Եշ. ԴՁ. ԴօրՅիսնակացպահոց:",
                "header": {"holy_week_prefix": False, "dagger": False},
            }
        )

        self.assertTrue(evidence["facts"]["is_fast_day"]["value"])
        self.assertEqual(
            evidence["facts"]["fast_context"]["value"], "fast_of_advent"
        )

    def test_collision_preserves_fast_and_marian_identities(self):
        evidence = _classify(
            "2026-09-08",
            "Բ օր Խաչի պահոց: "
            "Տօն Ծննդեան Սրբուհւոյ Կուսին Մարիամու յԱննայէ:",
        )

        self.assertTrue(evidence["facts"]["is_fast_day"]["value"])
        self.assertEqual(
            evidence["facts"]["fast_context"]["value"],
            "fast_of_holy_cross",
        )
        self.assertTrue(evidence["facts"]["is_marian_feast"]["value"])
        self.assertIsNone(evidence["facts"]["is_saints_day"]["value"])
        self.assertEqual(
            {item["id"] for item in evidence["occurrences"]},
            {"fast:holy_cross", "feast:marian:nativity_theotokos"},
        )

    def test_fast_named_for_saint_is_not_a_saints_day(self):
        evidence = _classify(
            "2026-06-16", "Բ օր Ս. Գրիգոր Լուսաւորչի պահոց:"
        )

        self.assertEqual(
            evidence["facts"]["fast_context"]["value"],
            "fast_of_saint_gregory",
        )
        self.assertIsNone(evidence["facts"]["is_saints_day"]["value"])
        self.assertIsNone(evidence["facts"]["saint_classes"]["value"])

    def test_explicit_saint_descriptors_are_positive_evidence(self):
        evidence = _classify(
            "2026-10-24", "Սրբոց երկոտասանից վարդապետացն:"
        )

        self.assertTrue(evidence["facts"]["is_saints_day"]["value"])
        self.assertEqual(
            evidence["facts"]["saint_classes"]["value"], ["vartapet"]
        )

    def test_source_silence_is_unknown_not_false(self):
        evidence = _classify("2026-01-12", "Բ օր Ծննդեան:")

        for field in (
            "is_fast_day",
            "is_saints_day",
            "is_cross_feast",
            "is_marian_feast",
            "is_memorial",
        ):
            self.assertIsNone(evidence["facts"][field]["value"], field)

    def test_dagger_does_not_set_dominical(self):
        evidence = classify_explicit_record(
            {
                "date": "2026-01-01",
                "calendar_clause": "Գ օր Ս. Ծննդեան պահոց:",
                "header": {"dagger": True, "holy_week_prefix": False},
            }
        )

        self.assertTrue(evidence["source_has_dagger"])
        self.assertIsNone(evidence["facts"]["is_dominical"]["value"])

    def test_plain_fast_is_resolved_from_source_barekendan_window(self):
        records = [
            classify_explicit_record(
                {
                    "date": "2026-05-24",
                    "calendar_clause": "Բ կիր. զկնի Հոգեգալստեան:",
                    "normalized_text": (
                        "24 Կիր. Բ կիր. զկնի Հոգեգալստեան: Օրհ. աձ. "
                        "Բարեկենդան Եղիական պահոց:"
                    ),
                    "header": {"dagger": True, "holy_week_prefix": False},
                }
            )
        ]
        for day in range(25, 30):
            records.append(_classify("2026-05-%02d" % day, "Պահք:"))

        resolve_year_fast_contexts(records)

        self.assertEqual(
            [record["facts"]["fast_context"]["value"] for record in records[1:]],
            ["fast_of_prophet_elijah"] * 5,
        )

    def test_unnamed_fast_falls_back_only_after_window_resolution(self):
        record = _classify("2026-01-14", "Պահք:")

        resolve_year_fast_contexts([record])

        self.assertEqual(
            record["facts"]["fast_context"]["value"], "weekly_fast"
        )


if __name__ == "__main__":
    unittest.main()
