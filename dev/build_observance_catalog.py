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
    _FEAST_SEP, _eve_label, _position_label, MAX_YEAR, MIN_YEAR,
)

DEV_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DEV_DIR)
GROUND_TRUTH_PATH = os.path.join(DEV_DIR, "feast_name_ground_truth.json")
REVIEW_PATH = os.path.join(DEV_DIR, "feast_name_review.tsv")
CATALOG_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data",
                            "observance_catalog.json")

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
    # MERGED: an alternate name, not a second observance. The source spells these
    # commemorations with a longer or shorter companion list and prints both across years
    # for the same liturgical day; the propers settle it, being byte-identical within each
    # group (docs/feast-name-corrections.md section 7). They now ship as ``variants`` of the
    # id named here, so the display text is unchanged and only the identity is single.
    "cyricus_and_his_mother_2": "merged into cyricus_and_his_mother (identical propers)",
    "cyricus_and_his_mother_3": "merged into cyricus_and_his_mother (identical propers)",
    "vahan_of_goghtn_eugenia": "merged into vahan_of_goghtn (identical propers)",
    "vahan_of_goghtn_gordius": "merged into vahan_of_goghtn (identical propers)",
    "fathers_sts_athanasius_and_2":
        "merged into fathers_sts_athanasius_and (identical propers)",
    "hermits_sts_anton_tryphon": "merged into hermit_st_anton (identical propers)",
    "atom_and_his_soldiers": "merged into atom (identical propers)",
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


def served_components():
    """Every distinct component the engine can emit as a single observance.

    Two origins, both enumerated rather than transcribed: the reviewed text of everything
    the source published, and the position/eve labels the engine composes per date (which
    the source may print less specifically -- see source_corrections.illuminator_fast_label).
    """
    texts = set()
    d, end = datetime.date(MIN_YEAR, 1, 1), datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        texts.update(label for label in (_position_label(d), _eve_label(d)) if label)
        d += datetime.timedelta(days=1)
    return texts


def build_catalog(ground_truth):
    """``(catalog, problems)`` -- the projection, and every invariant it violates.

    One entry per OBSERVANCE, not per display string. A commemoration the source spells
    several ways (a longer or shorter companion list for the same liturgical day) is one
    entry, and its short forms are ABBREVIATIONS: the row approves the full list, so the
    short text is a key into the catalog and never a value in it.

    ``variants`` survives for the one case that is not an abbreviation -- two companion
    sets the source prints for one id that are not nested in each other, where naming the
    union would assert saints the source never puts on that day. Those keep their own
    ``en``/``hy``, so display text stays exact while identity stays single.
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

    for source, row in sorted(ground_truth.items()):
        primary = row.get("variant_of")
        if not primary:
            continue
        if row.get("id"):
            problems.append(f"{primary}: a row has BOTH an id and a variant_of; it is "
                            "either its own observance or an alternate name for one")
            continue
        en, hy = names_of(row)
        if not en or not hy:
            problems.append(f"variant of {primary}: missing approved text for {source!r}")
            continue
        if primary not in catalog:
            problems.append(f"{en!r} is a variant of {primary!r}, which is not an "
                            "observance -- variant_of must name a row that has an id")
            continue
        if en == catalog[primary]["en"]:
            # The ordinary case, and what the Second Volume's own preface describes: the
            # source printed an ABBREVIATION of this observance on some days, and the row
            # approves the full name. The short form is a key into the catalog, never a
            # value in it -- apply_ground_truth has already resolved it by the time the
            # engine looks anything up, so there is nothing to add here.
            continue
        if en in by_en:
            problems.append(
                f"variant {en!r} of {primary} is already the English of {by_en[en]}")
            continue
        by_en[en] = primary
        catalog[primary].setdefault("variants", []).append(
            {"en": en, "hy": hy.replace(_FEAST_SEP, _INTERNAL_SEP)})

    for entry in catalog.values():
        if "variants" in entry:
            entry["variants"].sort(key=lambda v: v["en"])

    return catalog, problems


def audit(catalog, ground_truth):
    """Coverage against what the engine actually serves, and against what has shipped."""
    findings = []
    # A variant is covered by the observance it names, so it counts as resolvable text.
    approved_ids = {row["approved_en"]: (row.get("id") or row.get("variant_of"))
                    for row in ground_truth.values() if row.get("approved_en")}
    served = served_components()

    unregistered = sorted(t for t in served if not approved_ids.get(t))
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
    # A variant is covered by the observance it names, so it counts as resolvable text.
    approved_ids = {row["approved_en"]: (row.get("id") or row.get("variant_of"))
                    for row in ground_truth.values() if row.get("approved_en")}
    used = {sid for sid in approved_ids.values() if sid}
    new = {text: _slug(text, used)
           for text in sorted(served_components()) if not approved_ids.get(text)}
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
