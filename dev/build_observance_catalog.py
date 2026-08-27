"""DEV-ONLY: project dev/observance_name_ground_truth.json into the shipped id -> {en, hy}
observance catalog.

"Observance" (not "feast") because the corpus is not all feasts -- fasts ("First day of
the Fast of the Assumption"), calendar positions ("Fourth Sunday after Nativity") and eve
notes ("Eve of Great Lent") are named components too.

This is a PROJECTION, not a derivation. Every id is STATED, in the ``id`` column of
dev/observance_name_review.tsv, next to the human decision about what the observance should be
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
readings-hash -> id index (see build_readings_index) letting engine._resolve_generated_text
find an already-stated id from a date's own (immutable) readings instead of from its
(renameable) display text. Unlike the catalog above, this index is safe to fully
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
    _OBSERVANCE_SEP, _ORDINAL_WORDS, _compute_lectionary, _eve_label,
    _eve_coordinate, _observance_id_from_coordinate, _observance_id_from_readings,
    _position_coordinate, _resolve_generated_id, _eve_observance_id,
    _position_label, compute_armenian_lectionary, MAX_YEAR, MIN_YEAR, fixed_date_label,
)

DEV_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DEV_DIR)
GROUND_TRUTH_PATH = os.path.join(DEV_DIR, "observance_name_ground_truth.json")
REVIEW_PATH = os.path.join(DEV_DIR, "observance_name_review.tsv")
CATALOG_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                            "observance_catalog.json")
READINGS_INDEX_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                                   "observance_readings_index.json")

# _OBSERVANCE_SEP is the ENGINE's component join, and a catalog entry is ONE component. Any
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


# A "{ord} day of ..." label's first 4 words are almost always the same four filler
# words ("first/second/... day of") shared by a dozen unrelated fasts -- _STRIP_PREFIX
# does nothing for them since they don't start with an article/honorific. Slugging THAT
# span produced ids like "first_day_of_the_7", where the "_7" is only load-bearing
# because six other, unrelated fasts got there first; nothing in the id names which fast
# it actually is. Detected and handled specially: slug the FAST'S OWN name instead (a
# stopword filter, not a fixed word count, since "the bishop of" is exactly as
# uninformative here as "day of the" is above) and encode the ordinal as a number, the
# same shape "illuminator_fast_day_1" already uses by hand.
_ORD_DAY_OF_RE = re.compile(
    r"^(?P<ord>[A-Za-z]+) day of (?:the )?(?:Fast of )?(?P<rest>.+)$")
_ORDINAL_TO_N = {word: i + 1 for i, word in enumerate(_ORDINAL_WORDS)}
_SLUG_STOPWORDS = frozenset(
    "of the a an fast day bishop saint st sts holy".split())


def _slug(text, used):
    """A short id for an observance that has none yet. Only reached under ``--mint``.

    Collisions are resolved with a numeric suffix, which is exactly why this must never run
    for text that already has an id: the suffix depends on iteration order, so re-deriving
    the whole catalog would renumber every colliding entry the moment a new one sorted
    ahead of it. Stated ids are what make that impossible.
    """
    m = _ORD_DAY_OF_RE.match(text)
    n = _ORDINAL_TO_N.get(m.group("ord")) if m else None
    if m and n:
        rest = _NON_WORD.sub(" ", m.group("rest").lower()).split()
        words = [w for w in rest if w not in _SLUG_STOPWORDS]
        base = "_".join(words[:2] or ["observance"]) + f"_day_{n}"
    else:
        s = _STRIP_PREFIX.sub("", text.replace(_OBSERVANCE_SEP, " ").lower())
        base = "_".join(_NON_WORD.sub("_", s).strip("_").split("_")[:4]) or "observance"
    sid, k = base, 2
    while sid in used:
        sid, k = f"{base}_{k}", k + 1
    used.add(sid)
    return sid


def load_ground_truth():
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def served_components(ground_truth):
    """Every distinct component the engine can emit as a single observance.

    Two origins, both enumerated rather than transcribed: the position/eve labels the
    engine composes per date (which the source may print less specifically -- see
    source_corrections.named_fast_label), and the COMPONENTS of every approved name.

    Components, not whole approved names: a correction may resolve one source string into
    several observances joined on _OBSERVANCE_SEP, because the Tonats'oyts packs several First
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
        parts = [p.strip() for p in approved.split(_OBSERVANCE_SEP) if p.strip()]
        if len(parts) > 1:
            # Only the halves a split PRODUCED. A whole approved name is already a row, and
            # that row states its id or states why it has none -- sweeping those back in
            # would remint ids for text that reaches nothing, which is what _RETIRED_IDS
            # exists to keep out.
            texts.update(part for part in parts if part not in whole)
    return texts


def generated_label_ids():
    """``{literal label text -> the observance id it resolves to}``, for every position and
    eve label the engine composes in range.

    The third route by which a served component is registered, and the only one that
    survives a rename of a label whose engine literal has drifted from its ``source_en``.
    The first two match TEXT -- ``approved_en``, then the immutable ``source_en`` -- and a
    label composed in ``engine.py`` matches whichever of those its literal happens to
    equal. That is fine until a correction moves the literal (the Nativity fast's eve is
    ``"Eve of the Fast of Nativity"`` in ``_EVE_CIVIL`` and ``"Eve of Fast of Nativity"``
    in the source), because the row is then pinned: renaming ``approved_en`` leaves the
    literal matching neither, and the build reports a served, catalogued observance as
    unregistered.

    Resolving by id instead asks the question the runtime asks -- readings first, then the
    calendar coordinate -- and gets an answer that does not move when the text does.

    One ``_compute_lectionary`` per day, not one per label: it is the expensive half, and
    both kinds need the same day's readings.
    """
    out = {}
    d, end = datetime.date(MIN_YEAR, 1, 1), datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        labels = (("position", _position_label(d), _position_coordinate(d)),
                  ("eve", _eve_label(d), _eve_coordinate(d)))
        if any(label and label not in out for _, label, _ in labels):
            readings = _compute_lectionary(d).get("ReadingsList", [])
            for kind, label, coordinate in labels:
                if label and label not in out:
                    sid = _resolve_generated_id(readings, kind, coordinate)
                    if sid:
                        out[label] = sid
        d += datetime.timedelta(days=1)
    return out


def registration(ground_truth):
    """``text -> the id registering it``, or ``None`` -- the one place that question is asked.

    Both callers below (the coverage audit, which refuses to write, and ``--mint``, which
    hands out new ids) must agree exactly: a text the audit thinks is unregistered and mint
    thinks is registered blocks the build forever, and the reverse mints a duplicate id for
    an observance that already has one. They used to spell the predicate out separately.
    """
    approved_ids = {row["approved_en"]: row.get("id")
                    for row in ground_truth.values() if row.get("approved_en")}
    ids_by_source = {source: row.get("id")
                     for source, row in ground_truth.items() if row.get("id")}
    generated_ids = generated_label_ids()
    known = ({sid for sid in approved_ids.values() if sid}
             | {sid for sid in ids_by_source.values() if sid})

    def registered(text):
        # approved_en, then the immutable source_en, then the id the engine's own
        # resolution route gives this literal -- accepted only if some row states it, so a
        # stale shipped index cannot register an observance the TSV has dropped.
        sid = approved_ids.get(text) or ids_by_source.get(text)
        if sid:
            return sid
        sid = generated_ids.get(text)
        return sid if sid in known else None

    return registered


def build_readings_index(ground_truth):
    """readings-hash -> catalog id, for every position/eve label whose readings uniquely
    identify it -- plus coordinate-hash -> catalog id for every label a stable calendar
    coordinate uniquely identifies (see the coordinate pass below).

    The readings half: the same text always carries the same readings, and those readings
    never recur under a different text. Checked within each label's DOMINANT ``Source`` tier,
    with two further refinements needed to make the correspondence hold in practice:

    - **Displacement by a fixed civil date.** A day inside the Fast of St. James the
      bishop of Nisibis can coincide with the Conception of the Holy Virgin (12 of 27
      years), which outranks it and replaces its readings wholesale (``Source`` flips
      ``validated-table`` -> ``validated-composite``); those years are excluded from the
      label's signature. This alone doesn't cover a coincidence that does NOT change
      ``Source`` -- e.g. "Eve of Great Lent" disagrees on 2 of 27 years because the
      Presentation of the Lord (a fixed civil date) happens to fall on it, but both stay
      ``validated-table``. A disagreeing occurrence is excluded there only when it is
      independently provable to belong elsewhere: its pre-overlay commemoration
      (``_compute_lectionary(d)["Liturgical Day"]``) must have exactly one reading set
      across ALL its own occurrences globally, on at least one date that does not also
      carry this label -- the second condition rules out a SELF-referential
      "commemoration" (a civil-year-unanimous table entry that already bakes this
      label's own text into its stored ``"feast"`` field, which would otherwise look
      tautologically stable). Neither mechanism lowers the bar: a label's remaining,
      unexplained occurrences must still agree exactly, which is why the
      Sunday-after-Nativity/Transfiguration/Assumption families stay excluded -- their
      own ``_position_label`` docstring admits their count is "not exact on every
      occurrence," and their disagreement has no competing observance to attribute it to.
    - **Cross-tier collisions.** Detected across every tier a label was ever served
      under, not just its dominant one -- a minority tier (a best-guess continuum filling
      in for an unvalidated date) can still reuse another label's reading pool.

    A second pass then indexes by calendar COORDINATE (``engine._position_coordinate`` /
    ``engine._eve_coordinate``: the family's own anchor key and day-offset, hashed by
    ``engine._observance_id_from_coordinate`` in a namespace that cannot collide with a
    readings-based hash). Every label with one stable coordinate that no other label
    shares gets an entry, whether or not the readings pass already covered it.

    That pass used to be reserved for labels with no readings to hash at all (the ferial
    days of the Fast of the Catechumens, a validated aliturgical day). Reserving it left
    93 label-days across 31 labels unresolvable -- days where a fixed civil feast outranks
    the day and takes its readings, so the readings hash misses while the engine goes on
    serving the label. The exclusions above keep those days from corrupting a label's
    readings SIGNATURE, which is right; what they cannot do is give the day an identity,
    and the coordinate can.

    The two routes are not interchangeable and ``engine._resolve_generated_text`` does not
    treat them as such -- readings are evidence, a coordinate is the labelling rule
    restating itself. ``_assert_routes_agree`` is what keeps the weaker one honest: where
    both resolve, they must name the same observance, or the build fails and writes
    nothing.

    ``kind`` ("position"/"eve") is folded into every hash, readings and coordinate alike,
    because the two can share a day by construction: Pentecost+21 is a Sunday every year,
    so "Third Sunday after Pentecost" and "Eve of Fast of St. Gregory the Illuminator"
    always carry identical readings AND sit on the identical coordinate.

    Loads ``_position_label``/``_eve_label`` with no ``readings`` argument (the literal
    calendar-rule text, matching how the catalog's ids were originally minted), then
    separately fetches each date's readings, ``Source``, and pre-overlay commemoration via
    ``_compute_lectionary``/``compute_armenian_lectionary``, since readings are resolved
    before any position/eve label is applied.
    """
    approved_ids = {row["approved_en"]: row.get("id")
                    for row in ground_truth.values() if row.get("approved_en")}
    # See audit()'s matching comment: falls back to the row's immutable source_en so an
    # already-renamed row still gets its id indexed here.
    ids_by_source = {source: row.get("id")
                     for source, row in ground_truth.items() if row.get("id")}

    # (kind, literal text) -> the id the ENGINE declares for it. An eve declares its own
    # (engine._EVE_FAMILIES/_EVE_CIVIL carry it), which is the only route that survives a
    # rename: the two text routes below both compare the literal against a column a rename
    # is free to move, and when they miss, the label loses its index entry -- so the
    # runtime stops resolving it and serves the literal beside the renamed stored
    # component, the same observance twice. Filled in by the per-date sweep, which is
    # where a date is in hand to ask.
    declared_ids = {}

    def id_for_literal_text(text, kind=None):
        return (declared_ids.get((kind, text))
                or approved_ids.get(text) or ids_by_source.get(text))

    # (kind, text) -> {Source tier: [(readings, pre-overlay commemoration), ...]}, so the
    # dominant tier can be picked per label before the stability checks run. See the
    # docstring for why "kind" is part of the key.
    #
    # commemoration_readings is built from EVERY date, not just labeled ones: it is what
    # lets a disagreeing occurrence be checked against an independently, globally stable
    # competing commemoration.
    occurrences_by_key = {}
    coordinates_by_key = {}                  # (kind, text) -> {coordinate, ...}
    keys_by_coordinate = {}                  # (kind, coordinate) -> {(kind, text), ...}
    occurrence_coordinate = {}               # (kind, text, date) -> coordinate
    commemoration_readings = {}
    commemoration_dates = {}
    d, end = datetime.date(MIN_YEAR, 1, 1), datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        base = _compute_lectionary(d)
        readings = tuple(base["ReadingsList"])         # unaffected by any overlay
        commem = base["Liturgical Day"]
        commemoration_readings.setdefault(commem, set()).add(readings)
        commemoration_dates.setdefault(commem, set()).add(d)
        for kind, label, coordinate in (
                ("position", _position_label(d), _position_coordinate(d)),
                ("eve", _eve_label(d), _eve_coordinate(d))):
            if label and kind == "eve":
                declared = _eve_observance_id(d)
                if declared:
                    declared_ids[(kind, label)] = declared
            if label and id_for_literal_text(label, kind):
                by_tier = occurrences_by_key.setdefault((kind, label), {})
                by_tier.setdefault(base["Source"], []).append((readings, commem, d))
                coordinates_by_key.setdefault((kind, label), set()).add(coordinate)
                keys_by_coordinate.setdefault((kind, coordinate), set()).add((kind, label))
                occurrence_coordinate[(kind, label, d)] = coordinate
        d += datetime.timedelta(days=1)

    # Every tier, not just each key's dominant one -- see the docstring's cross-tier note.
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
            # Explain away a disagreeing occurrence only per the docstring's two
            # conditions: independently stable, and attested outside this label's own
            # dates (which also rules out a self-referential "commemoration").
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
        if not readings:
            continue                              # aliturgical: the coordinate pass has it
        if len(keys_by_readings[(kind, readings)]) != 1:
            continue                              # those readings also carry another text
        index[_observance_id_from_readings(list(readings), kind)] = id_for_literal_text(
            text, kind)

    # Coordinate pass. Every label with one stable coordinate that no other label shares
    # gets an entry, not only the aliturgical ones -- see the docstring.
    coordinate_ids = {}
    for key, coords in coordinates_by_key.items():
        kind, text = key
        if len(coords) != 1 or None in coords:
            continue                          # not a single stable calendar coordinate
        (coordinate,) = coords
        if len(keys_by_coordinate[(kind, coordinate)]) != 1:
            continue                          # another label sits on the same coordinate
        akey, offset = coordinate
        coordinate_ids[_observance_id_from_coordinate(akey, offset, kind)] = (
            id_for_literal_text(text, kind))

    _assert_routes_agree(index, coordinate_ids, occurrences_by_key, occurrence_coordinate,
                         id_for_literal_text)
    index.update(coordinate_ids)
    return index


def _assert_routes_agree(readings_ids, coordinate_ids, occurrences_by_key,
                         occurrence_coordinate, id_for_literal_text):
    """Fail the build if the two routes would ever name different observances.

    The readings route is evidence and the coordinate route is the labelling rule
    restated (see ``engine._resolve_generated_text``), so wherever both resolve, they are
    two independent authorities answering one question and must answer it the same way.
    They do, on every one of the ~4,300 label-days in range. If a table rebuild ever
    parts them, that is the signal that one of the two is wrong -- and it has to stop the
    build, because by the time it reaches a served name there is nothing left to notice
    it: both routes produce a plausible observance name, and neither is marked.

    Bounded by MIN_YEAR/MAX_YEAR, since that is what the sweep above walked.
    """
    conflicts = []
    for (kind, text), by_tier in occurrences_by_key.items():
        expected = id_for_literal_text(text, kind)
        for occurrences in by_tier.values():
            for readings, _commem, d in occurrences:
                coordinate = occurrence_coordinate.get((kind, text, d))
                if coordinate is None:
                    continue
                akey, offset = coordinate
                via_coordinate = coordinate_ids.get(
                    _observance_id_from_coordinate(akey, offset, kind))
                via_readings = readings_ids.get(
                    _observance_id_from_readings(list(readings), kind)) if readings else None
                if via_coordinate and via_readings and via_coordinate != via_readings:
                    conflicts.append(
                        f"{d} {kind} {text!r}: readings -> {via_readings}, "
                        f"coordinate -> {via_coordinate} (expected {expected})")
    if conflicts:
        raise SystemExit(
            "readings and coordinate routes disagree on "
            f"{len(conflicts)} occurrence(s); the index was NOT written:\n  "
            + "\n  ".join(conflicts[:20]))


def build_catalog(ground_truth):
    """``(catalog, problems)`` -- the projection, and every invariant it violates.

    One entry per OBSERVANCE, not per display string. A commemoration the source spells
    several ways is one entry per CANON: the Tonats'oyts packs several First Volume canons
    onto one line when the taregir leaves few days for them, and the row approves the
    _OBSERVANCE_SEP-joined split, so each canon resolves to its own id and the join gets none.
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
        if _OBSERVANCE_SEP in en:
            problems.append(f"{sid}: {en!r} is a whole day, not one component -- an id "
                            "belongs on each half, not on the join")
            continue
        by_id[sid], by_en[en] = source, sid
        catalog[sid] = {"en": en, "hy": hy.replace(_OBSERVANCE_SEP, _INTERNAL_SEP)}

    return catalog, problems


def audit(catalog, ground_truth):
    """Coverage against what the engine actually serves, and against what has shipped."""
    findings = []
    registered = registration(ground_truth)
    served = served_components(ground_truth)

    unregistered = sorted(t for t in served if not registered(t))
    if unregistered:
        findings.append(
            f"{len(unregistered)} component(s) the engine serves have no id: "
            + ", ".join(repr(t) for t in unregistered[:5])
            + "\n  Add the row to observance_name_review.tsv (dev/observance_name_review.py) and "
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
    # The SAME predicate audit() refuses on -- see registration(). A renamed
    # engine-composed label must not be minted a second id here: it already has one, and
    # audit() can see that it does.
    registered = registration(ground_truth)
    used = {sid for sid in approved_ids.values() if sid}
    new = {text: _slug(text, used)
           for text in sorted(served_components(ground_truth))
           if not registered(text)}
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
    # "resolvable", not "readings-keyed": the file holds readings hashes and coordinate
    # hashes in one namespace-prefixed keyspace (see build_readings_index).
    print(f"wrote {len(readings_index)} resolvable id(s) to {READINGS_INDEX_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
