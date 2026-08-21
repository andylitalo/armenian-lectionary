"""DEV-ONLY: project dev/feast_name_ground_truth.json into the shipped id -> {en, hy}
observance catalog.

"Observance" (not "feast") because the corpus is not all feasts -- fasts ("First day of
the Fast of the Assumption"), calendar positions ("Fourth Sunday after Nativity") and eve
notes ("Eve of Great Lent") are named components too.

This is a PROJECTION, not a derivation. Every id is STATED, in the ``id`` column of
dev/feast_name_review.tsv, next to the human decision about what the observance should be
called::

    {row.id: {"en": row.approved_en, "hy": row.approved_hy}}

That is the whole build. It matters that ids are stated rather than computed from text:
an id derived from display text moves when the text is corrected, and a consumer keying
stored data on it would be no better off than one keying on names -- only the breakage
would be silent. bahk lost 158 of 429 stored feast names that way when 1.3.0 folded
"Saint(s)" to "St(s)."; an id must not be able to repeat it.

So there is no minting here for text that already has an id, no reuse-by-text lookup, and
no registry of superseded spellings. Correcting a name edits ``approved_en`` and the id stays
put. Only a genuinely new observance needs an id, and ``--mint`` assigns one, writing it
back to the TSV so it is recorded in the same place as every other.

Rows with an empty ``id`` are deliberately not observances:
  * "Fast day - Remembrance of the Ten Virgins" -- a whole DAY. A registered correction
    split the source's comma-joined text into two components; both halves are their own
    rows with their own ids, and the day resolves component-wise to the pair.
  * three minority source spellings the table's unanimity rule overrides, which nothing
    reaches: no date serves them and no table entry stores them. An id nothing can produce
    is one no consumer can ever match. (Text the table stores DOES keep an id even where a
    higher-precedence tier shadows it at runtime -- the artifacts still have to resolve.)

Deliberately excluded: _PLACEHOLDER_LABELS ("(commemoration)", "(movable ordinary-time
reading)") and the "{season} (day not yet in validated table)" fallback -- internal
absence-markers, not observances, with nothing to translate. They never reach the TSV.

Also writes armenian_lectionary/data/observance_readings_index.json, a SEPARATE
readings-hash -> id index (see build_readings_index) covering the subset of position/eve
ids whose readings are the same on every date they are served (a dedicated fast weekday or
an eve, never a day sharing its table key with a rotating saint). It exists so
engine._position_label/_eve_label can find an already-stated id from a date's own
(immutable) readings instead of from its (renameable) display text -- see
engine._resolve_generated_text. Unlike the catalog above, this index is safe to fully
regenerate on every run: readings, unlike text, are never corrected, so recomputing it
always reproduces the same keys.

Usage:
    python dev/build_observance_catalog.py            # project and verify
    python dev/build_observance_catalog.py --mint     # also assign ids to new observances
"""

import csv
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import (                              # noqa: E402
    _FEAST_SEP, _compute_lectionary, _eve_label, _observance_id_from_coordinate,
    _observance_id_from_readings, _position_coordinate, _position_label,
    compute_armenian_lectionary, MAX_YEAR, MIN_YEAR, fixed_date_label,
)

DEV_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DEV_DIR)
GROUND_TRUTH_PATH = os.path.join(DEV_DIR, "feast_name_ground_truth.json")
REVIEW_PATH = os.path.join(DEV_DIR, "feast_name_review.tsv")
CATALOG_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                            "observance_catalog.json")
READINGS_INDEX_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                                   "observance_readings_index.json")

# _FEAST_SEP is the ENGINE's component join, and a catalog entry is ONE component. Any
# entry whose own text contains it is a category error, and it shows: the source's Armenian
# for a few days carries a trailing note its English drops ("- Նաւակատիք", the vigil), and
# the scrape kept that inside the single component it was paired with. The engine then
# joined the day's components with the same separator, so `hy` came out with one component
# more than `en` on 131 days -- a consumer splitting on " - " to render or measure them saw
# a different shape per language.
#
# The content is real and the source publishes it, so it stays; only the delimiter changes.
# ASCII on purpose: source_corrections._is_expected_char allows ASCII, the Armenian block
# and the em-dash, so a semicolon needs no widening of that allow-list.
_INTERNAL_SEP = "; "

_STRIP_PREFIX = re.compile(r"^(the\s+|sts?\.?\s+|saints?\s+|holy\s+)+", re.IGNORECASE)
_NON_WORD = re.compile(r"[^a-z0-9]+")

# Ids that were in the catalog file but are deliberately gone, each with the reason. An id
# may only be retired by being named here; otherwise its disappearance is a build failure.
#
# These three were minted for approved source text that reaches NOTHING -- not a served
# name, and not a stored one either. The catalog was built by sweeping every reviewed
# source string, which includes the minority spellings the table's unanimity rule overrides
# in favour of the form the other years agree on, so an id could be minted for a variant
# with no consumer at all.
#
# Note the line: text the table STORES keeps its id even where no date serves it, because a
# higher-precedence tier shadows the entry at runtime (the pre-Lent cohort does exactly this
# to two Atom/Cyricus variants). The artifacts have to resolve, so the id has to exist.
#
# Retiring was only available because the catalog's keys had never been served as ids at
# this point -- ObservanceIds did not exist yet. After that, an id here keeps meaning the
# same observance forever, and this table stops being a place to add to.
_RETIRED_IDS = {
    "eugenius_macarius_valerius_candidus_2":
        "a glued variant no date emits and the table does not store",
    "sargis_the_warrior_and":
        "a glued variant no date emits and the table does not store",
    "theodore_the_general":
        "published once, on 2016-02-13; every other year at that coordinate says Theodore "
        "the TYRON, which is what the table serves -- a source one-off, not an observance",
    # Ids minted for a PACKED DAY, not an observance. The Tonats'oyts squeezes the
    # post-Theophany saint pool into a gap whose length varies with the taregir, so one
    # line can carry several First Volume canons; the old build minted an id per distinct
    # line. Each canon keeps its own id and the join gets none, exactly as with the
    # comma-joined "Fast day, Remembrance of the Ten Virgins".
    "cyricus_and_his_mother_2": "a packed day; Cyricus and the Gordius canon each keep an id",
    "cyricus_and_his_mother_3": "a packed day; Cyricus, Vahan and Gordius each keep an id",
    "vahan_of_goghtn_eugenia": "a packed day; Vahan and the Eugenia canon each keep an id",
    "vahan_of_goghtn_gordius": "a packed day; Vahan and the Gordius canon each keep an id",
    "fathers_sts_athanasius_and_2":
        "a packed day; Athanasius/Cyril and Gregory the Theologian each keep an id",
    "hermits_sts_anton_tryphon":
        "a packed day; Anton and the Tryphon canon each keep an id",
    "atom_and_his_soldiers": "a packed day; Atom and the Mark canon each keep an id",
    "eugenia_the_virgin_her_2":
        "a packed day; the Eugenia and Eugenius canons each keep an id",
    "atom_and_his_soldiers_2": "a packed day; Atom and the Sukiasians each keep an id",
}


def _slug(text, used):
    """A short id for an observance that has none yet. Only reached under ``--mint``.

    Collisions are resolved with a numeric suffix, which is exactly why this must never run
    for text that already has an id: the suffix depends on iteration order, so re-deriving
    the whole catalog would renumber every colliding entry the moment a new one sorted
    ahead of it. Stated ids are what make that impossible.
    """
    s = _STRIP_PREFIX.sub("", text.replace(_FEAST_SEP, " ").lower())
    base = "_".join(_NON_WORD.sub("_", s).strip("_").split("_")[:4]) or "observance"
    sid, n = base, 2
    while sid in used:
        sid, n = f"{base}_{n}", n + 1
    used.add(sid)
    return sid


def load_ground_truth():
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def served_components(ground_truth):
    """Every distinct component the engine can emit as a single observance.

    Two origins, both enumerated rather than transcribed: the position/eve labels the
    engine composes per date (which the source may print less specifically -- see
    source_corrections.illuminator_fast_label), and the COMPONENTS of every approved name.

    Components, not whole approved names: a correction may resolve one source string into
    several observances joined on _FEAST_SEP, because the Tonats'oyts packs several First
    Volume canons onto one line when the taregir leaves few days for them. Each half is a
    served observance and needs an id, including the halves the source never publishes
    alone -- which is precisely the case that reading only whole approved names misses.
    """
    texts = set()
    d, end = datetime.date(MIN_YEAR, 1, 1), datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        texts.update(label for label in (_position_label(d), _eve_label(d),
                                         fixed_date_label(d)) if label)
        d += datetime.timedelta(days=1)
    whole = {row["approved_en"] for row in ground_truth.values() if row.get("approved_en")}
    for approved in whole:
        parts = [p.strip() for p in approved.split(_FEAST_SEP) if p.strip()]
        if len(parts) > 1:
            # Only the halves a split PRODUCED. A whole approved name is already a row, and
            # that row states its id or states why it has none -- sweeping those back in
            # would remint ids for text that reaches nothing, which is what _RETIRED_IDS
            # exists to keep out.
            texts.update(part for part in parts if part not in whole)
    return texts


def build_readings_index(ground_truth):
    """readings-hash -> catalog id, for every position/eve label whose OWN readings (within
    its dominant source tier -- see below) are in a ONE-TO-ONE correspondence with it across
    every date served in MIN_YEAR..MAX_YEAR: the same text always carries the same readings
    there, AND those readings never recur under a DIFFERENT text.

    Restricting to each label's dominant tier first is what makes that correspondence
    possible to state at all. A day inside the Fast of St. James the bishop of Nisibis can
    coincide with the fixed civil date of the Conception of the Holy Virgin (12 of 27
    supported years), which OUTRANKS the fast day and replaces its readings wholesale with
    its own ("Source" flips from "validated-table" to "validated-composite") -- the fast
    day's position label is still served as text that year, but that year's readings belong
    to the Conception, not to the fast day, and indexing them under the fast day's id would
    be wrong regardless of whether they happen to collide with anything else. Filtering each
    label to only the tier it is served under on most of its occurrences drops exactly those
    displaced years from consideration; the label is still fully indexed from its other,
    undisplaced occurrences. (Elijah and Illuminator have no such displacement -- every
    occurrence is "validated-table" -- so this filter is a no-op for them.)

    That is a different problem from the Sunday-after-Nativity/Transfiguration/Assumption
    families, whose own ``_position_label`` docstring admits their counting rule is "not
    exact on every occurrence": there the instability is WITHIN one tier (validated-table
    every time -- the reading a lectio-continua slot carries stays put, but the Sunday-count
    the source prints for it can drift across years of different length), so tier-filtering
    does not and should not rescue them. Requiring an exact one-to-one correspondence within
    the dominant tier is what correctly leaves those excluded -- they fall back to their
    literal template text via engine._resolve_generated_text, exactly as an uncatalogued
    label already does, so this is safe to run unattended as new families are added.

    Loads _position_label/_eve_label with NO readings argument (the literal calendar-rule
    text, matching how the catalog's ids were originally minted from that same text), then
    separately fetches each date's ReadingsList and Source via compute_armenian_lectionary.
    That second call is the (currently) only way to get a date's readings independent of its
    position/eve label text, since readings are resolved by _compute_lectionary before any
    label is applied.

    A position label whose dominant-tier readings come up EMPTY (some days in the ferial
    track of the Fast of the Catechumens carry no scripture at all -- an aliturgical day,
    validated as intentional, not missing data) has no reading content to hash in the first
    place. Those are indexed instead by their calendar COORDINATE
    (engine._position_coordinate: the position family's own anchor key and day-offset),
    checked for the same one-to-one correspondence readings get -- trivially satisfied here,
    since a family's coordinate is a pure function of the calendar, never of which saint or
    reading happens to land on it. engine._observance_id_from_coordinate hashes it in a
    namespace that cannot collide with a readings-based hash by construction.

    A dominant tier is not always enough on its own. "Eve of Great Lent" disagrees on 2 of
    27 years (2010, 2021) -- Feb 14, when the FIXED civil date of the Presentation of the
    Lord happens to land on Great Lent's own eve and outranks it -- but "Source" stays
    "validated-table" both ways, so tier-filtering cannot see this one (unlike Nisibis /
    Dec 9, where "Source" itself flips). Rather than lower the bar to "close enough," a
    disagreeing occurrence is EXPLAINED, and excluded from the count rather than counted
    against it, only when that date's own pre-overlay commemoration
    (_compute_lectionary(d)["Liturgical Day"], BEFORE the eve/position text is added) is
    independently, globally stable in its OWN readings across every one of ITS OWN
    occurrences (checked over the whole date range, not just the ones that also happen to
    carry this label) -- i.e. the Presentation of the Lord always reads the same four
    verses on Feb 14 whether or not that date happens to also be an eve. That is a
    verified fact about a SEPARATE observance, not a loosened threshold on this one: the
    label's own remaining, unexplained occurrences must still agree EXACTLY, or it stays
    excluded. This does not rescue the Sunday-after-X families either -- their disagreeing
    years share no such independently stable competing commemoration; they are simply
    the label's own genuine variance.
    """
    approved_ids = {row["approved_en"]: row.get("id")
                    for row in ground_truth.values() if row.get("approved_en")}
    # Fall back to the row's own (immutable) source_en key -- see audit()'s matching
    # comment -- so a row already renamed (approved_en no longer equal to the literal text
    # engine.py still composes) still gets its id indexed here, keeping it resolvable
    # through a SECOND rebuild after the first rename rather than dropping out of the index.
    ids_by_source = {source: row.get("id")
                     for source, row in ground_truth.items() if row.get("id")}

    def id_for_literal_text(text):
        return approved_ids.get(text) or ids_by_source.get(text)

    # (kind, text) -> {Source tier: [(readings, pre-overlay commemoration), ...]}, so the
    # dominant tier can be picked per label before the stability checks run. ``kind``
    # ("position"/"eve") keeps the two collision checks below from colliding a position
    # label with an eve note that shares its day's readings by CONSTRUCTION rather than
    # coincidence -- Pentecost+21 is a Sunday every year (21 is a multiple of 7), so "Third
    # Sunday after Pentecost" and "Eve of Fast of St. Gregory the Illuminator" always carry
    # the identical readings. Without the namespace both would permanently collide and
    # neither could ever be indexed; with it, each resolves independently within its own
    # kind, matching engine._observance_id_from_readings's own kind parameter.
    #
    # commemoration_readings is built from EVERY date, not just labeled ones: it is what
    # lets a disagreeing occurrence be checked against an independently, globally stable
    # competing commemoration (see the docstring above).
    occurrences_by_key = {}
    coordinates_by_text = {}                          # position-only; see the docstring
    commemoration_readings = {}
    commemoration_dates = {}
    d, end = datetime.date(MIN_YEAR, 1, 1), datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        base = _compute_lectionary(d)
        readings = tuple(base["ReadingsList"])         # unaffected by any overlay
        commem = base["Liturgical Day"]
        commemoration_readings.setdefault(commem, set()).add(readings)
        commemoration_dates.setdefault(commem, set()).add(d)
        for kind, label in (("position", _position_label(d)), ("eve", _eve_label(d))):
            if label and id_for_literal_text(label):
                by_tier = occurrences_by_key.setdefault((kind, label), {})
                by_tier.setdefault(base["Source"], []).append((readings, commem, d))
                if kind == "position":
                    coordinates_by_text.setdefault(label, set()).add(_position_coordinate(d))
        d += datetime.timedelta(days=1)

    # Collision registration must see every tier a label was EVER served under, not just
    # its dominant one: a minority tier (a best-guess continuum falling back for a date the
    # validated table doesn't cover, say) can still reuse the same reading pool as some
    # other, fully-resolved label. Dropping those occurrences before the collision check --
    # rather than merely before the stability check -- would let that other label's id
    # claim a reading that is not actually unique to it, silently.
    keys_by_readings = {}
    for key, by_tier in occurrences_by_key.items():
        kind, _text = key
        for occurrences in by_tier.values():
            for r, _commem, _d in occurrences:
                keys_by_readings.setdefault((kind, r), set()).add(key)

    readings_by_key = {}
    for key, by_tier in occurrences_by_key.items():
        dominant_tier = max(by_tier, key=lambda tier: len(by_tier[tier]))
        occurrences = by_tier[dominant_tier]
        readings_set = {r for r, _commem, _d in occurrences}
        if len(readings_set) != 1:
            # Explain away a disagreeing occurrence only if its OWN reading equals what
            # its pre-overlay commemoration reads on EVERY ONE of that commemoration's own
            # occurrences globally, AND that commemoration is independently attested on a
            # date that does NOT also carry this label -- otherwise a one-off coincidence
            # (a rare commemoration that happens to appear only alongside this label, with
            # nothing to compare it to) could pass the singleton check trivially and wrongly
            # explain away what is actually this label's own genuine variance. This also
            # correctly refuses to explain away a SELF-referential "commemoration" -- a
            # civil-year-unanimous table entry that already bakes this very label's own text
            # into its stored "feast" field, which would otherwise look tautologically
            # "stable" and explain the label away using nothing but itself.
            these_dates = {d for _r, _commem, d in occurrences}
            unexplained = {
                r for r, commem, _d in occurrences
                if commemoration_readings.get(commem) != {r}
                or not (commemoration_dates.get(commem, set()) - these_dates)
            }
            if unexplained:
                readings_set = unexplained
        readings_by_key[key] = readings_set

    index = {}
    for (kind, text), readings_set in readings_by_key.items():
        if len(readings_set) != 1:
            continue                              # not offset-determined; leave unresolvable
        (readings,) = readings_set
        if readings:
            if len(keys_by_readings[(kind, readings)]) != 1:
                continue                          # those readings also carry another text
            index[_observance_id_from_readings(list(readings), kind)] = (
                id_for_literal_text(text))
        elif kind == "position":
            coords = coordinates_by_text[text]
            if len(coords) != 1 or None in coords:
                continue                          # not a single stable calendar coordinate
            (akey, offset), = coords
            index[_observance_id_from_coordinate(akey, offset)] = id_for_literal_text(text)
    return index


def build_catalog(ground_truth):
    """``(catalog, problems)`` -- the projection, and every invariant it violates.

    One entry per OBSERVANCE, not per display string. A commemoration the source spells
    several ways is one entry per CANON: the Tonats'oyts packs several First Volume canons
    onto one line when the taregir leaves few days for them, and the row approves the
    _FEAST_SEP-joined split, so each canon resolves to its own id and the join gets none.
    """
    catalog, problems = {}, []
    by_id, by_en = {}, {}

    def names_of(row):
        en, hy = row.get("approved_en"), row.get("approved_hy")
        return en, hy

    # Primaries first: a variant cannot be attached before its observance exists.
    for source, row in sorted(ground_truth.items()):
        sid = row.get("id")
        if not sid:
            continue
        en, hy = names_of(row)
        if not en:
            problems.append(f"{sid}: has an id but no approved English")
            continue
        if not hy:
            problems.append(f"{sid}: no Armenian for {en!r} -- fill approved_hy "
                            f"in {os.path.basename(REVIEW_PATH)}, with a note")
            continue
        if sid in by_id:
            # Several raw source spellings can correct to one approved name ("Hermogenes"
            # / "Hermongenes"), and they are the same observance, so they share its id.
            # Sharing an id under DIFFERENT names is the real error: it means the id no
            # longer picks out one observance.
            if catalog[sid]["en"] != en:
                problems.append(
                    f"{sid}: assigned to two different observances "
                    f"({catalog[sid]['en']!r} and {en!r})")
            continue
        if en in by_en:
            problems.append(
                f"{sid} and {by_en[en]} share the English {en!r}; one display string "
                "cannot identify two observances")
            continue
        if _FEAST_SEP in en:
            problems.append(f"{sid}: {en!r} is a whole day, not one component -- an id "
                            "belongs on each half, not on the join")
            continue
        by_id[sid], by_en[en] = source, sid
        catalog[sid] = {"en": en, "hy": hy.replace(_FEAST_SEP, _INTERNAL_SEP)}

    return catalog, problems


def audit(catalog, ground_truth):
    """Coverage against what the engine actually serves, and against what has shipped."""
    findings = []
    approved_ids = {row["approved_en"]: row.get("id")
                    for row in ground_truth.values() if row.get("approved_en")}
    # A renamed engine-composed row (its approved_en no longer equal to the LITERAL text
    # engine.py still composes -- see build_readings_index) is still registered: source_en
    # is its immutable identity key, left untouched by a rename per the review workflow, so
    # falling back to it here is what keeps a rename from reading as "unregistered" the
    # moment it lands, before the readings index has had a chance to pick it up.
    ids_by_source = {source: row.get("id")
                     for source, row in ground_truth.items() if row.get("id")}
    served = served_components(ground_truth)

    unregistered = sorted(
        t for t in served if not (approved_ids.get(t) or ids_by_source.get(t)))
    if unregistered:
        findings.append(
            f"{len(unregistered)} component(s) the engine serves have no id: "
            + ", ".join(repr(t) for t in unregistered[:5])
            + "\n  Add the row to feast_name_review.tsv (dev/feast_name_review.py) and "
              "rerun with --mint.")

    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, encoding="utf-8") as fh:
            dropped = sorted(set(json.load(fh)) - set(catalog) - set(_RETIRED_IDS))
        if dropped:
            findings.append(
                f"{len(dropped)} published id(s) would be dropped: "
                + ", ".join(dropped[:5])
                + "\n  A shipped id must keep meaning the same observance forever; a "
                  "consumer keying stored data on it cannot notice it vanished. Restore "
                  "the row's id, or retire it explicitly in _RETIRED_IDS with the reason.")
        revived = sorted(set(catalog) & set(_RETIRED_IDS))
        if revived:
            findings.append(
                f"{len(revived)} retired id(s) are in use again: " + ", ".join(revived)
                + "\n  Reusing a retired id points a consumer's stored key at whatever "
                  "took its place. Drop it from _RETIRED_IDS only if it is the SAME "
                  "observance coming back.")
    return findings


def mint(ground_truth):
    """Assign ids to served components that have none, writing them back to the TSV."""
    approved_ids = {row["approved_en"]: row.get("id")
                    for row in ground_truth.values() if row.get("approved_en")}
    # See audit()'s matching comment: a renamed engine-composed row is found by its
    # immutable source_en, not by approved_en, so a rename is never mistaken for a new,
    # unminted observance.
    ids_by_source = {source: row.get("id")
                     for source, row in ground_truth.items() if row.get("id")}
    used = {sid for sid in approved_ids.values() if sid}
    new = {text: _slug(text, used)
           for text in sorted(served_components(ground_truth))
           if not (approved_ids.get(text) or ids_by_source.get(text))}
    if not new:
        return {}

    with open(REVIEW_PATH, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        if not row["id"] and row["approved_en"] in new:
            row["id"] = new[row["approved_en"]]
    with open(REVIEW_PATH, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t",
                           lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    return new


def main():
    ground_truth = load_ground_truth()

    if "--mint" in sys.argv:
        minted = mint(ground_truth)
        for text, sid in sorted(minted.items()):
            print(f"minted {sid} for {text!r}")
        if minted:
            print(f"{len(minted)} id(s) written to {REVIEW_PATH}; "
                  "rerun dev/build_ground_truth.py to carry them through.")
            return 1

    catalog, problems = build_catalog(ground_truth)
    findings = problems + audit(catalog, ground_truth)
    if findings:
        print("catalog NOT written:")
        for f in findings:
            print(f"  - {f}")
        return 1

    with open(CATALOG_PATH, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {len(catalog)} observances to {CATALOG_PATH}")

    readings_index = build_readings_index(ground_truth)
    with open(READINGS_INDEX_PATH, "w", encoding="utf-8") as fh:
        json.dump(readings_index, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {len(readings_index)} readings-keyed id(s) to {READINGS_INDEX_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
