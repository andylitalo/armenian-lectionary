"""DEV-ONLY: resolve already-approved display text into observance_catalog.json ids.

Shared by every Phase-2 rewiring step (dev/build_table.py, dev/refresh_artifact_names.py)
so a component-to-id lookup is defined exactly once. Text handed to ``ids_for_text`` is
assumed ALREADY corrected/approved (the output of ``apply_source_corrections`` or
equivalent) -- this module only resolves identity, it does not fix spelling.
"""

import functools
import json
import os

from armenian_lectionary.engine import _FEAST_SEP

CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "armenian_lectionary", "data", "observance_catalog.json")


@functools.lru_cache(maxsize=1)
def _catalog():
    with open(CATALOG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=1)
def _text_to_id():
    """English component -> id.

    One entry per component: no two observances share an English text, an invariant
    dev/build_observance_catalog.py enforces. That is what lets a storage tier -- which has
    text and no date -- resolve identity on its own.
    """
    return {v["en"]: sid for sid, v in _catalog().items()}


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
