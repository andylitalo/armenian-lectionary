"""DEV-ONLY: verify armenian_lectionary/data/observance_catalog.json against every
display-text component currently shipped or live-generated.

Two directions, both must be empty:

  * ORPHAN COMPONENTS -- a component the table / saint schedule / a hardcoded engine.py
    literal actually serves, with no catalog entry. This is the dangerous direction: it
    means Phase 2 (rewiring storage to reference ids) would have nowhere to point.
  * UNUSED CATALOG ENTRIES -- a catalog id nothing currently serves. Not dangerous, but
    worth knowing about (a stale/typo'd id, or a component that only appears in years the
    checks below don't cover).

Sources of "currently shipped or live-generated" text, matching dev/build_observance_
catalog.py's own sources so the two scripts stay honest about what they cover:
  - every table entry's "feast" string (armenian_lectionary/data/lectionary_data.json)
  - every saint_schedule.json sequence label
  - _position_label / _eve_label, enumerated across the full supported date range
  - _PRELENT_COHORT's labels
  - _EMBEDDED_FEAST's labels
Excluded: _PLACEHOLDER_LABELS and the "day not yet in validated table" fallback --
internal absence-markers, not observances (see dev/build_observance_catalog.py).

Usage:
    python dev/verify_observance_catalog.py
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import (                               # noqa: E402
    DATA_PATH, _DATE_SCOPED_OBSERVANCE_IDS, _EMBEDDED_FEAST, _FEAST_SEP,
    _PRELENT_COHORT, _date_scoped_observance_id, _eve_label, _position_label,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                             "observance_catalog.json")
SCHEDULE_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                              "saint_schedule.json")

MIN_YEAR, MAX_YEAR = 2001, 2027


def components_of(feast_str):
    return [c.strip() for c in (feast_str or "").split(_FEAST_SEP) if c.strip()]


def table_components():
    with open(DATA_PATH, encoding="utf-8") as fh:
        tables = json.load(fh)["tables"]
    seen = set()
    for entries in tables.values():
        for entry in entries.values():
            seen.update(components_of(entry.get("feast", "")))
    return seen


def schedule_components():
    with open(SCHEDULE_PATH, encoding="utf-8") as fh:
        schedule = json.load(fh)
    seen = set()
    for zone in schedule.values():
        for entry in zone.get("sequence", []):
            seen.update(components_of(entry.get("label", "")))
    return seen


def live_generated_components():
    seen = set()
    d = datetime.date(MIN_YEAR, 1, 1)
    end = datetime.date(MAX_YEAR, 12, 31)
    one_day = datetime.timedelta(days=1)
    while d <= end:
        p = _position_label(d)
        if p:
            seen.add(p)
        e = _eve_label(d)
        if e:
            seen.add(e)
        d += one_day
    return seen


def prelent_components():
    return {label for _sid, _off, _may_shift, label, _reads in _PRELENT_COHORT}


def embedded_components():
    return set(_EMBEDDED_FEAST.values())


def date_scoped_ids_reached():
    """Every date-scoped id the engine actually resolves somewhere in the range.

    The text-set checks above are blind to these: five ids all read "Fast day" in English,
    so they collapse to one served string and can never be reported unused, however wrong
    the date rule is. Enumerating the rule itself is what catches an id that never fires --
    an off-by-one in the ordinal window would silently strand the first or last day of the
    fast on the general "Պահք" it used to get.
    """
    reached = set()
    d = datetime.date(MIN_YEAR, 1, 1)
    end = datetime.date(MAX_YEAR, 12, 31)
    one_day = datetime.timedelta(days=1)
    while d <= end:
        for component in ("Fast day",):
            sid = _date_scoped_observance_id(component, d)
            if sid:
                reached.add(sid)
        d += one_day
    return reached


def main():
    with open(CATALOG_PATH, encoding="utf-8") as fh:
        catalog = json.load(fh)
    catalog_texts = {v["en"] for v in catalog.values()}

    served = (table_components() | schedule_components() | live_generated_components()
              | prelent_components() | embedded_components())

    orphans = sorted(served - catalog_texts)
    unused = sorted(catalog_texts - served)

    if orphans:
        print(f"{len(orphans)} ORPHAN component(s) served with no catalog entry:")
        for text in orphans:
            print(f"  - {text!r}")
    else:
        print("0 orphan components.")

    if unused:
        print(f"\n{len(unused)} UNUSED catalog entr(y/ies) (not currently served):")
        for text in unused:
            print(f"  - {text!r}")
    else:
        print("0 unused catalog entries.")

    # Date-scoped ids, checked by id rather than by text -- see date_scoped_ids_reached.
    declared = set(_DATE_SCOPED_OBSERVANCE_IDS)
    missing_entry = sorted(declared - set(catalog))
    never_reached = sorted(declared - date_scoped_ids_reached())
    if missing_entry:
        print(f"\n{len(missing_entry)} date-scoped id(s) with NO catalog entry:")
        for sid in missing_entry:
            print(f"  - {sid}")
    if never_reached:
        print(f"\n{len(never_reached)} date-scoped id(s) the engine never resolves "
              f"in {MIN_YEAR}-{MAX_YEAR}:")
        for sid in never_reached:
            print(f"  - {sid}")
    if not missing_entry and not never_reached:
        print(f"\n{len(declared)} date-scoped id(s), all present and all reached.")

    print(f"\n{len(catalog)} catalog entries; {len(served)} distinct components served.")
    return 1 if (orphans or missing_entry or never_reached) else 0


if __name__ == "__main__":
    sys.exit(main())
