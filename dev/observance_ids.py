"""DEV-ONLY: resolve already-approved display text into observance_catalog.json ids.

Shared by every Phase-2 rewiring step (dev/build_table.py, dev/refresh_artifact_names.py)
so a component-to-id lookup is defined exactly once. Text handed to ``ids_for_text`` is
assumed ALREADY corrected/approved (the output of ``apply_source_corrections`` or
equivalent) -- this module only resolves identity, it does not fix spelling.
"""

import functools
import json
import os

from armenian_lectionary.engine import _DATE_SCOPED_OBSERVANCE_IDS, _FEAST_SEP

CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "armenian_lectionary", "data", "observance_catalog.json")


@functools.lru_cache(maxsize=1)
def _catalog():
    with open(CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=1)
def _text_to_id():
    """English component -> id, excluding the date-scoped ids.

    Those deliberately share their English text with a general component (five ids all read
    "Fast day"), so including them would make this mapping depend on catalog iteration order
    and could stamp an Illuminator-fast id onto any of the 2,139 ordinary fast days. Storage
    tiers key on text alone and have no date to disambiguate with, so they get the general
    id; the engine applies the date-scoped one at resolution time
    (engine._date_scoped_observance_id).
    """
    return {v["en"]: sid for sid, v in _catalog().items()
            if sid not in _DATE_SCOPED_OBSERVANCE_IDS}


def ids_for_text(text):
    """Ordered list of observance ids for a (possibly _FEAST_SEP-joined) served string.

    Raises KeyError, naming the missing component, rather than silently dropping it --
    an unresolvable component here means observance_catalog.json has drifted out of date
    with what's actually served; that must be caught, not swallowed. Run
    dev/build_observance_catalog.py (and dev/verify_observance_catalog.py) again first.
    """
    by_text = _text_to_id()
    ids = []
    for component in [c.strip() for c in (text or "").split(_FEAST_SEP) if c.strip()]:
        if component not in by_text:
            raise KeyError(
                f"no observance_catalog.json entry for component {component!r}; "
                "rerun dev/build_observance_catalog.py")
        ids.append(by_text[component])
    return ids
