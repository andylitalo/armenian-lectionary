"""Offline lock for all source-positive calendar facts in the reviewed corpus."""

import datetime
import hashlib
import json
import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from armenian_lectionary import compute_armenian_lectionary  # noqa: E402


FIXTURE_PATH = os.path.join(
    ROOT, "tests", "fixtures", "oratsouyts_calendar_expectations.json"
)
MANIFEST_PATH = os.path.join(
    ROOT, "dev", "oratsouyts", "source_manifest.json"
)
RECONCILIATION_ALLOWLIST_PATH = os.path.join(
    ROOT, "dev", "oratsouyts", "runtime_reconciliation_allowlist.json"
)


class TestOratsouytsCalendarExpectations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE_PATH, encoding="utf-8") as source:
            cls.fixture = json.load(source)

    def test_fixture_is_tied_to_exact_source_manifest(self):
        with open(MANIFEST_PATH, "rb") as source:
            manifest_hash = hashlib.sha256(source.read()).hexdigest()

        self.assertEqual(self.fixture["schema_version"], 1)
        self.assertEqual(
            self.fixture["source_manifest_sha256"], manifest_hash
        )
        with open(RECONCILIATION_ALLOWLIST_PATH, "rb") as source:
            allowlist_hash = hashlib.sha256(source.read()).hexdigest()
        self.assertEqual(
            self.fixture["reconciliation_allowlist_sha256"], allowlist_hash
        )
        dates = [case["date"] for case in self.fixture["cases"]]
        self.assertEqual(len(dates), len(set(dates)))

    def test_every_source_positive_fact_or_known_reconciliation(self):
        mismatches = []
        for case in self.fixture["cases"]:
            date = datetime.date.fromisoformat(case["date"])
            runtime = compute_armenian_lectionary(date)["Calendar"]
            for field, source_value in case["expected"].items():
                runtime_value = runtime[field]
                if field == "Saint Classes":
                    agrees = set(source_value) <= set(runtime_value)
                else:
                    agrees = runtime_value == source_value
                if not agrees:
                    mismatches.append(
                        {
                            "date": case["date"],
                            "field": field,
                            "source_value": source_value,
                            "runtime_value": runtime_value,
                        }
                    )

        self.assertEqual(
            mismatches,
            self.fixture["accepted_reconciliation"],
        )


if __name__ == "__main__":
    unittest.main()
