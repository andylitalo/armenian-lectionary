"""Shared guard for the accuracy-lock tests that need the ground-truth cache.

The engine's exhaustive accuracy tests validate against ``dev/reference_data/`` --
~9,900 JSON files (~39 MB) scraped from sacredtradition.am. That cache is
git-ignored (large, and the third-party source data is not redistributed; see
README), so a fresh checkout does not have it. Decorate those test *classes* with
``@requires_reference_cache`` so they SKIP (rather than fail their coverage floors)
when the cache is absent; rebuild it with ``python dev/bulk_fetch.py``.
"""

import os
import unittest

REF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dev", "reference_data")

HAS_REFERENCE_CACHE = os.path.isdir(REF_DIR) and any(
    name.endswith(".json") for name in os.listdir(REF_DIR))

requires_reference_cache = unittest.skipUnless(
    HAS_REFERENCE_CACHE,
    "dev/reference_data/ ground-truth cache absent; run `python dev/bulk_fetch.py` "
    "to enable the accuracy-lock tests.")
