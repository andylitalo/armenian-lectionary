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
from dev.build_table import build, validate, slim_tables, _dates_by_entry  # noqa: E402
from armenian_lectionary.engine import DATA_PATH  # noqa: E402
from tests._reference_cache import requires_reference_cache  # noqa: E402


@requires_reference_cache
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
        # Slimmed by the export's OWN function, dates and all, so this compares a fresh
        # build against the shipped file rather than against a second implementation of
        # the export that can drift from it.
        with open(DATA_PATH, encoding="utf-8") as f:
            shipped = json.load(f)["tables"]
        fresh = slim_tables(self.tables, _dates_by_entry(self.days, self.tables))
        self.assertEqual(fresh, shipped,
                         "shipped lectionary_data.json differs from a fresh build")


if __name__ == "__main__":
    unittest.main()
