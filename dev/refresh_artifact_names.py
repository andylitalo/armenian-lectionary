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

A ``sequence`` entry's label is resolved ID-FIRST, not text-first, whenever it already
carries ``observance_ids`` (every entry does, as of this writing). An id never moves
(CLAUDE.md), so :func:`dev.observance_ids.text_for_id` -- ask the catalog what THIS id is
called now -- stays correct no matter how many times the observance has been renamed.
Matching on the currently stored TEXT, via :func:`dev.source_corrections.apply_ground_truth`,
only ever recognizes the ORIGINAL source spelling: it is keyed by ``source_en``, so it
resolves a label correctly the first time it is corrected and then silently no-ops on
every correction after that, because the stored label is by then neither ``source_en`` nor
necessarily today's ``approved_en``. The prior run then leaves this script's own id lookup
looking for text the catalog no longer has, and it crashes naming that stale text rather
than the entry that needs fixing. Text-matching is kept only as the fallback for an entry
that has never been assigned an id at all -- a brand-new schedule entry this script has
never touched, and the one case with no id to anchor on yet.

Idempotent -- id-anchored resolution always is; the text-anchored fallback is too, exactly
once (see above), so running this twice is a no-op except immediately after a second
correction to the same still-id-less entry, which cannot happen once it has an id.

Usage:
    python dev/refresh_artifact_names.py            # report what would change
    python dev/refresh_artifact_names.py --write    # apply
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import _OBSERVANCE_SEP                # noqa: E402
from dev.observance_ids import ids_for_text, text_for_id              # noqa: E402
from dev.source_corrections import (                                  # noqa: E402
    apply_ground_truth, normalize_confusables,
)


def corrected(text):
    """The same text chain ``apply_source_corrections`` runs on a cached feast string,
    minus the date-scoped position-label fix (a schedule label is not date-scoped).

    Text-anchored fallback only -- see the module docstring for why an entry that already
    has an id is resolved through :func:`_label_for_ids` instead."""
    return normalize_confusables(apply_ground_truth(text))


def _label_for_ids(ids):
    """A sequence entry's served label, composed from its own declared ids, in order."""
    return _OBSERVANCE_SEP.join(text_for_id(sid) for sid in ids)

SCHEDULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "armenian_lectionary", "data", "saint_schedule.json")


def refresh(schedule):
    """Rewrite every feast label in ``schedule`` in place. Returns the list of changes."""
    changes = []
    for zone in schedule.values():
        for entry in zone.get("sequence", []):
            old_label = entry.get("label", "")
            old_ids = entry.get("observance_ids") or []
            if old_ids:
                new_label, new_ids = _label_for_ids(old_ids), old_ids
            else:
                new_label = corrected(old_label)
                new_ids = ids_for_text(new_label)
            if new_label != old_label:
                changes.append((old_label, new_label))
                entry["label"] = new_label
            if new_ids != old_ids:
                changes.append((old_ids, new_ids))
                entry["observance_ids"] = new_ids
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
