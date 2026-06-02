"""Table reproducibility & in-sync check.

Proves the shipped lectionary_data.json is exactly what the dev build pipeline
produces from the current code + ground truth (nobody hand-edited it, and the
runtime resolves keys with the same code the builder validated against).
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import load_all  # noqa: E402
from dev.build_table import build, validate  # noqa: E402
from lectionary import DATA_PATH  # noqa: E402


def _slim(tables):
    """Replicate export_table's slimming: string keys, {feast, readings} only."""
    out = {}
    for ks, entries in tables.items():
        out[ks] = {}
        for key, v in entries.items():
            keystr = key if isinstance(key, str) else str(key)
            out[ks][keystr] = {"feast": v["feast"], "readings": v["readings"]}
    return out


class TestTableBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = load_all()
        cls.tables, _ = build(cls.days)

    def test_build_self_validates_with_no_miss(self):
        ok, miss, nodata, total, _ = validate(self.days, self.tables)
        self.assertEqual(miss, 0, "freshly built table produced a wrong hit")
        self.assertGreater(ok, 0)

    def test_shipped_table_is_reproducible(self):
        with open(DATA_PATH, encoding="utf-8") as f:
            shipped = json.load(f)["tables"]
        self.assertEqual(_slim(self.tables), shipped,
                         "shipped lectionary_data.json differs from a fresh build")


if __name__ == "__main__":
    unittest.main()
