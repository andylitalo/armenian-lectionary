"""DEV-ONLY: push the registered source-text corrections into the shipped saint schedule.

``armenian_lectionary/data/saint_schedule.json`` is the only shipped artifact besides the
table and the hy maps that carries human-readable feast text: each ``sequence`` entry has a
``label`` the engine serves as ``"Liturgical Day"`` on generative-saint days, and
``aliases`` is keyed by the source's label. When a fix lands in
``dev/source_corrections`` those strings have to move with it, or the engine serves the
corrected name on table days and the uncorrected one on saint days.

Why this and not a full ``dev/saint_schedule.py`` rebuild: that generator does not
currently reproduce the checked-in artifact from the present cache -- regenerating it
also moves ``second_volume_cycles.json`` and changes which tier serves some days (e.g.
2016-07-30 falls from ``second-volume-cycle`` to ``generative-saint``). That drift is real
and predates this work, but it is a READINGS change and belongs in its own reviewed
commit. This script touches text only: ids, ordering, support counts and every reading
stay byte-identical, so a name fix cannot smuggle in a readings change.

Idempotent -- the correction chain is, so running this twice is a no-op.

Usage:
    python dev/refresh_artifact_names.py            # report what would change
    python dev/refresh_artifact_names.py --write    # apply
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.source_corrections import (                                  # noqa: E402
    normalize_confusables, normalize_feast_spelling,
)


def corrected(text):
    """The same text chain ``apply_source_corrections`` runs on a cached feast string,
    minus the date-scoped position-label fix (a schedule label is not date-scoped)."""
    return normalize_feast_spelling(normalize_confusables(text))

SCHEDULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "armenian_lectionary", "data", "saint_schedule.json")


def refresh(schedule):
    """Rewrite every feast label in ``schedule`` in place. Returns the list of changes."""
    changes = []
    for zone in schedule.values():
        for entry in zone.get("sequence", []):
            fixed = corrected(entry.get("label", ""))
            if fixed != entry.get("label"):
                changes.append((entry["label"], fixed))
                entry["label"] = fixed
        aliases = zone.get("aliases")
        if aliases is None:
            continue
        # Aliases are keyed by the SOURCE's label, so their keys move too -- and the fixed
        # form may collide with a key that was already correct, which is the point: the
        # two spellings were always the same feast.
        rebuilt = {}
        for key, sid in aliases.items():
            fixed = corrected(key)
            if fixed != key:
                changes.append((key, fixed))
            rebuilt[fixed] = sid
        zone["aliases"] = rebuilt
    return changes


def main():
    with open(SCHEDULE_PATH, encoding="utf-8") as fh:
        schedule = json.load(fh)
    changes = refresh(schedule)

    if not changes:
        print("saint_schedule.json already carries the corrected names; nothing to do.")
        return 0
    print(f"{len(changes)} label(s) to correct:")
    for before, after in changes:
        print(f"  - {before}")
        print(f"  + {after}")
    if "--write" not in sys.argv:
        print("\n(dry run; pass --write to apply)")
        return 0

    with open(SCHEDULE_PATH, "w", encoding="utf-8") as fh:
        json.dump(schedule, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print(f"\nwrote {SCHEDULE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
