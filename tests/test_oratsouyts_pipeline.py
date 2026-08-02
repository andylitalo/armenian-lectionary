"""Acceptance-gate contracts for the local multi-year corpus builder."""

import json
from pathlib import Path
import tempfile
import unittest

from dev.oratsouyts.pipeline import (
    PipelineError,
    RUNTIME_RECONCILIATION_PATH,
    SOURCE_MANIFEST_PATH,
    _json_text,
    discover_sources,
    load_runtime_reconciliation_allowlist,
    load_source_manifest,
)


class TestOratsouytsPipeline(unittest.TestCase):
    def test_reviewed_source_and_reconciliation_manifests(self):
        sources = load_source_manifest(SOURCE_MANIFEST_PATH)
        self.assertEqual(
            sorted(sources),
            [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020,
             2022, 2023, 2024, 2025, 2026],
        )
        self.assertTrue(all(len(row["sha256"]) == 64 for row in sources.values()))

        reconciliations = load_runtime_reconciliation_allowlist(
            RUNTIME_RECONCILIATION_PATH
        )
        self.assertEqual(
            [(row["date"], row["field"]) for row in reconciliations],
            [("2018-07-28", "saint_classes")],
        )

    def test_source_discovery_rejects_missing_extra_and_renamed_years(self):
        manifest = {
            2025: {
                "year": 2025,
                "filename": "2025 Օրացույց.pdf",
                "sha256": "0" * 64,
                "page_count": 1,
            }
        }
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            with self.assertRaises(PipelineError):
                discover_sources(directory, manifest)

            (directory / "2025 renamed.pdf").touch()
            with self.assertRaisesRegex(PipelineError, "filenames differ"):
                discover_sources(directory, manifest)

            (directory / "2025 renamed.pdf").unlink()
            (directory / "2025 Օրացույց.pdf").touch()
            (directory / "2026 Օրացույց.pdf").touch()
            with self.assertRaisesRegex(PipelineError, "unexpected"):
                discover_sources(directory, manifest)

    def test_json_serialization_is_stable_and_sorted(self):
        first = _json_text({"z": [2, 1], "a": {"բ": 1}})
        second = _json_text(json.loads(first))
        self.assertEqual(first, second)
        self.assertLess(first.index('"a"'), first.index('"z"'))


if __name__ == "__main__":
    unittest.main()
