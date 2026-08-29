"""Shared guard for the accuracy-lock tests that need the ground-truth cache.

The engine's exhaustive accuracy tests validate against ``dev/reference_data/`` --
~9,900 JSON files (~39 MB) scraped from sacredtradition.am. That cache is
git-ignored (large, and the third-party source data is not redistributed; see
README), so a fresh checkout does not have it. Decorate those test *classes* with
``@requires_reference_cache`` so they SKIP (rather than fail their coverage floors)
when the cache is absent; rebuild it with ``python dev/bulk_fetch.py``.

The source's *Armenian* is a second, separate cache (``dev/reference_data_hy/``) with its
own guard, ``@requires_reference_cache_hy``. It is a distinct witness, not a subset:
sacredtradition.am publishes each day in both languages independently, which is what makes
the Armenian an oracle for the English. It is also sampled differently -- 433 days, one
representative date per distinct English feast string (see ``dev/fetch_translations.py``),
not the full range -- so tests over it cover the distinct NAMES well and per-year calendar
behaviour thinly.
"""

import json
import os
import unittest

_DEV_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dev")

REF_DIR = os.path.join(_DEV_DIR, "reference_data")
REF_DIR_HY = os.path.join(_DEV_DIR, "reference_data_hy")


def _has_cache(path):
    return os.path.isdir(path) and any(
        name.endswith(".json") for name in os.listdir(path))


HAS_REFERENCE_CACHE = _has_cache(REF_DIR)
HAS_REFERENCE_CACHE_HY = _has_cache(REF_DIR_HY)

requires_reference_cache = unittest.skipUnless(
    HAS_REFERENCE_CACHE,
    "dev/reference_data/ ground-truth cache absent; run `python dev/bulk_fetch.py` "
    "to enable the accuracy-lock tests.")

requires_reference_cache_hy = unittest.skipUnless(
    HAS_REFERENCE_CACHE_HY,
    "dev/reference_data_hy/ Armenian ground-truth cache absent; run "
    "`python dev/fetch_translations.py` to enable the Armenian accuracy lock.")


def reference_day(iso):
    """Load and correct one cached reference day by its ISO date string.

    Single reader for every dev/reference_data/ consumer in test_regression.py: opens
    REF_DIR/{iso}.json and applies the same corrections dev.analyze.load_all applies to
    the full cache, so a test comparing against this can never drift from what the build
    itself treats as ground truth.
    """
    from dev.source_corrections import apply_source_corrections
    with open(os.path.join(REF_DIR, f"{iso}.json"), encoding="utf-8") as fh:
        day = json.load(fh)
    return apply_source_corrections(day)
