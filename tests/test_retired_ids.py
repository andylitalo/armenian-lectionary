"""``_RETIRED_IDS``' "renamed to X" / "merged into X" reasons are prose, not a machine
contract: nothing parses them, so a typo'd or stale redirect would sit undetected unless
some OTHER code path still references the retired id -- which then raises loudly through
``dev.observance_ids``' catalog lookup, but only for a redirect something still exercises.
A redirect that simply names the WRONG id (real, but not the one the observance actually
became) raises nothing anywhere; it is only ever caught by reading the table.

Needs no ground-truth cache; runs in CI.
"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev import build_observance_catalog as build                          # noqa: E402

_REDIRECT = re.compile(r"^(?:renamed to|merged into) ([a-z0-9_]+)\b")


class TestRetiredIdRedirectsResolve(unittest.TestCase):
    """Every declared "renamed to"/"merged into" redirect must land on a live catalog id --
    the audit trail is only as good as the id it points to."""

    @classmethod
    def setUpClass(cls):
        with open(build.CATALOG_PATH, encoding="utf-8") as fh:
            cls.catalog = json.load(fh)
        cls.redirects = {
            old: m.group(1)
            for old, reason in build._RETIRED_IDS.items()
            if (m := _REDIRECT.match(reason))
        }

    def test_there_are_redirects_to_check(self):
        """A parsing regression that matched nothing would make every test below vacuous."""
        self.assertGreater(len(self.redirects), 0)

    def test_every_redirect_target_is_a_live_id(self):
        dangling = {old: new for old, new in self.redirects.items()
                    if new not in self.catalog}
        self.assertEqual(dangling, {}, f"redirect(s) point to a nonexistent id: {dangling}")

    def test_a_redirect_does_not_target_itself(self):
        selfies = [old for old, new in self.redirects.items() if old == new]
        self.assertEqual(selfies, [])

    def test_a_redirect_does_not_target_another_retired_id(self):
        """A redirect should land on the live id directly, not on a second retired id --
        otherwise following it to the actual observance takes two hops instead of one."""
        chained = {old: new for old, new in self.redirects.items()
                   if new in build._RETIRED_IDS}
        self.assertEqual(chained, {},
                         f"redirect(s) chain through another retired id: {chained}")


if __name__ == "__main__":
    unittest.main()
