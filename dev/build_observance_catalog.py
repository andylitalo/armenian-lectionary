"""DEV-ONLY: mint a single id -> {en, hy} catalog for every liturgical-observance
display-text component the engine currently serves.

"Observance" (not "feast") because the corpus is not all feasts -- fasts ("First day of
the Fast of the Assumption"), calendar positions ("Fourth Sunday after Nativity"), and eve
notes ("Eve of Great Lent") are named components too, and lumping them under "feast" is
the same mislabeling the existing `feast_names_hy.json`/`feast`-prefixed names already
carry. See the observance-catalog plan in dev/ for the fuller rationale.

Sources merged, each already-approved/served text (not the raw scrape) so no correction
step runs here -- that already happened upstream, in dev/feast_name_ground_truth.json and
by hand in engine.py's literal groups:

  1. dev/feast_name_ground_truth.json -- 392 approved commemoration/eve/position
     components, keyed by the raw source text that was reviewed; this script reads their
     ``approved`` value (deduping raw-typo variants that converge on one correct spelling).
  2. The position/eve labels engine.py generates LIVE (_position_label / _eve_label,
     including _advent_eve_label's two forms) -- enumerated by literally calling those
     functions across the full supported date range (2001-2027) rather than hand-
     transcribing _POSITION_FAMILIES'/_EVE_FAMILIES' template strings, so no ordinal or
     season combination is silently missed. This also naturally picks up
     _FV_SUMMER_CONTINUA's labels, which are the same position-family text on a Sunday the
     strict table happens to leave blank.
  3. _PRELENT_COHORT's 5 already-approved literals (sargis/atom/sukias/voskian/ghevond) --
     their existing ids are stable, single-component identities (unlike saint_schedule.
     json's ids, which key a whole multi-component READING-slot, not one display text) --
     reused verbatim.
  4. _EMBEDDED_FEAST's 3 fixed-date literals.

Every id maps to REQUIRED, non-null en/hy text -- per project direction there is no such
thing as an English-only observance. A handful of components the source never published
in isolation (only ever glued to a neighbor, so feast_names_hy.json has no standalone key)
are backfilled in _MANUAL_HY_OVERRIDES, each justified by decomposing a composite
translation that DOES contain it.

Deliberately excluded: _PLACEHOLDER_LABELS ("(commemoration)", "(movable ordinary-time
reading)") and the "{season} (day not yet in validated table)" fallback. These are
internal absence-markers, not liturgical observances -- there is nothing to translate.

This phase is purely ADDITIVE: engine.py's own resolution logic is untouched here, so
this script has zero effect on what compute_armenian_lectionary() serves. It only proves
a complete, bilingual catalog CAN be built. Verify with dev/verify_observance_catalog.py.

Usage:
    python dev/build_observance_catalog.py
"""

import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from armenian_lectionary.engine import (                              # noqa: E402
    _FEAST_SEP, _PRELENT_COHORT, _eve_label, _position_label,
)

DEV_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(DEV_DIR)
GROUND_TRUTH_PATH = os.path.join(DEV_DIR, "feast_name_ground_truth.json")
HY_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data", "feast_names_hy.json")
CATALOG_PATH = os.path.join(REPO_ROOT, "armenian_lectionary", "data", "observance_catalog.json")

MIN_YEAR, MAX_YEAR = 2001, 2027

# Components the source never published standalone -- only ever glued to a neighbor in a
# composite string -- so no standalone Armenian witness exists to scrape. Each value below
# is cross-checked against 2+ independent composite translations that agree on the same
# sub-translation (see dev/feast_name_review.tsv notes on these two rows).
_MANUAL_HY_OVERRIDES = {
    "Great Saturday": "Աւագ շաբաթ",
    "Eve of the Resurrection of our Lord Jesus Christ": "Ճրագալոյց Զատկի",
}

# A known-WRONG scraped value to override even though feast_names_hy.json does have an
# entry: "Second Sunday after Pentecost" ITSELF disagrees with two of its own composite
# occurrences (2-of-3 scraped as "Ա" = First, 1-of-3 as "Բ" = Second) -- a scrape-pairing
# defect, not a real ambiguity. _POSITION_FAMILIES' own comment is explicit that English
# has no "First Sunday after Pentecost" (the count floors at 2), so "Բ" is correct on
# every occurrence; verified against the one composite entry that has it right.
_HY_CORRECTIONS = {
    "Second Sunday after Pentecost": "Բ կիւրակէ զկնի Հոգեգալստեան",
    # The source spells this three ways across the cached years and feast_names_hy.json
    # paired it with the rarest: 'Ս. Աստուածածնի' x4, 'ս. Աստուածածնի' x2,
    # 'ս.Աստուածածնի' x1 -- and the 1-of-7 form, lowercase with no space after the
    # abbreviation dot, is what shipped on every Nov 21. Reported by
    # dev/audit_hy_variants.py; the majority form is also what this component's own
    # ground-truth row carries.
    "Presentation of the Holy Mother of God to the Temple":
        "Ընծայումն Ս. Աստուածածնի երից ամաց ի Տաճարն",
}

# Observances the source names more specifically in Armenian than in English, so one
# English text covers several distinct observances and the id cannot be recovered from it.
# The engine resolves these from the DATE instead (engine._date_scoped_observance_id), so
# they are minted here directly rather than discovered by enumerating served text -- an
# enumeration keyed on English would only ever see the one ambiguous string.
#
# The Fast of St. Gregory the Illuminator is the only family so far: the source heads its
# five weekdays (Pentecost+22..+26) with the ordinal in Armenian and a bare "Fast day" in
# English. The Armenian for days 1, 2 and 4 is attested directly in dev/reference_data_hy/
# (2001-06-25/26/28); days 3 and 5 are the same construction with the next letter numeral,
# the form the source uses for every other counted fast ("Ա օր Յիսնակի պահոց",
# "ԼԴ օր Մեծի պահոց"). Marked so verify_observance_catalog.py does not report them unused.
_ILLUMINATOR_FAST_HY = ("Ա", "Բ", "Գ", "Դ", "Ե")
_DATE_SCOPED = {
    f"illuminator_fast_day_{n}": {
        "en": "Fast day",
        "hy": f"{letter} օր Լուսաւորչի պահոց",
    }
    for n, letter in enumerate(_ILLUMINATOR_FAST_HY, start=1)
}

# _FEAST_SEP is the ENGINE's component join, and a catalog entry is ONE component. Any
# entry whose own text contains it is a category error, and it shows: the source's Armenian
# for a few days carries a trailing note its English drops ("— Նաւակատիք", the vigil;
# "— Կաղանդ. տարեմուտ", the New Year), and feast_names_hy.json kept that inside the single
# component it was paired with. The engine then joined the day's components with the same
# separator, so `hy` came out with one component more than `en` on 131 days -- a consumer
# splitting on " — " to render or measure them saw a different shape per language.
#
# The content is real and the source publishes it, so it stays; only the delimiter changes.
# ASCII on purpose: source_corrections._is_expected_char allows ASCII, the Armenian block
# and the em-dash, so a semicolon needs no widening of that allow-list.
_INTERNAL_SEP = "; "

_STRIP_PREFIX = re.compile(
    r"^(the\s+|sts?\.?\s+|saints?\s+|holy\s+)+", re.IGNORECASE)
_NON_WORD = re.compile(r"[^a-z0-9]+")


def _slug(text, used):
    """A short, stable, globally-unique id derived from display text.

    Same shape as dev/saint_schedule.py's ``_slug`` (strip generic honorifics, collapse to
    underscores, take the first few content words) but operating over the full,
    heterogeneous observance corpus (commemorations AND positions AND eve notes), so
    collisions are expected and resolved with a numeric suffix rather than assumed away.
    """
    s = text.replace(_FEAST_SEP, " ").lower()
    s = _STRIP_PREFIX.sub("", s)
    s = _NON_WORD.sub("_", s).strip("_")
    base = "_".join(s.split("_")[:4]) or "observance"
    sid = base
    n = 2
    while sid in used:
        sid = f"{base}_{n}"
        n += 1
    used.add(sid)
    return sid


def load_hy_map():
    if not os.path.exists(HY_PATH):
        return {}
    with open(HY_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("feasts", data) if isinstance(data, dict) else {}


def hy_for(text, hy_map):
    """Armenian witness for one component: exact key; else, for a component that is
    itself a glued composite (e.g. a correction split "Fast day, Remembrance of the Ten
    Virgins" in two, so the joined form was never scraped as one string even though both
    halves were -- same case dev.feast_name_review.armenian_for handles), the per-piece
    translations rejoined; else a manual backfill."""
    if text in _HY_CORRECTIONS:
        return _HY_CORRECTIONS[text]
    if text in hy_map:
        return hy_map[text]
    parts = [p.strip() for p in text.split(_FEAST_SEP) if p.strip()]
    if len(parts) > 1 and all(p in hy_map for p in parts):
        return _FEAST_SEP.join(hy_map[p] for p in parts)
    if text in _MANUAL_HY_OVERRIDES:
        return _MANUAL_HY_OVERRIDES[text]
    return None


def ground_truth_texts():
    """{approved english text} from every reviewed ground-truth component."""
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as fh:
        gt = json.load(fh)
    return sorted({v["approved"] for v in gt.values() if v.get("approved")})


def live_generated_texts():
    """Every distinct position/eve string engine.py can produce, by actually calling
    _position_label/_eve_label across the full supported range -- exact by construction,
    unlike hand-transcribing the template tuples."""
    positions, eves = set(), set()
    d = datetime.date(MIN_YEAR, 1, 1)
    end = datetime.date(MAX_YEAR, 12, 31)
    one_day = datetime.timedelta(days=1)
    while d <= end:
        p = _position_label(d)
        if p:
            positions.add(p)
        e = _eve_label(d)
        if e:
            eves.add(e)
        d += one_day
    return positions, eves


def prelent_cohort_texts():
    return [(sid, label) for sid, _off, _may_shift, label, _reads in _PRELENT_COHORT]


def build_catalog():
    hy_map = load_hy_map()
    used_ids = set()
    catalog = {}
    missing_hy = []

    # Pre-lent cohort keeps its existing, already-stable single-component ids.
    for sid, label in prelent_cohort_texts():
        used_ids.add(sid)
        hy = hy_for(label, hy_map)
        if hy is None:
            missing_hy.append(label)
            continue
        catalog[sid] = {"en": label, "hy": hy}

    # Date-scoped ids, minted verbatim. Deliberately BEFORE the text sweep so their shared
    # English ("Fast day") is already spoken for; the sweep's own entry for that text is
    # minted below under its general id, which is what the ambiguous text resolves to when
    # no date rule fires.
    for sid, entry in _DATE_SCOPED.items():
        used_ids.add(sid)
        catalog[sid] = dict(entry)

    positions, eves = live_generated_texts()
    all_texts = set(ground_truth_texts()) | positions | eves

    # Date-scoped ids are excluded from the "already minted" check on purpose: they SHARE
    # their English with a general component, which still needs its own general id.
    minted_en = {entry["en"] for sid, entry in catalog.items() if sid not in _DATE_SCOPED}

    for text in sorted(all_texts):
        if text in minted_en:
            continue    # already minted (e.g. a pre-lent cohort literal)
        if _FEAST_SEP in text:
            # Not one component. A registered correction split the source's comma-joined
            # "Fast day, Remembrance of the Ten Virgins" into two components with the
            # engine's separator, so the ground truth carries the JOINED form as one row.
            # Minting an id for it would be minting an id for a whole day; the day already
            # resolves component-wise to its two real ids.
            continue
        hy = hy_for(text, hy_map)
        if hy is None:
            missing_hy.append(text)
            continue
        sid = _slug(text, used_ids)
        catalog[sid] = {"en": text, "hy": hy.replace(_FEAST_SEP, _INTERNAL_SEP)}
        minted_en.add(text)

    return catalog, sorted(set(missing_hy))


def main():
    catalog, missing_hy = build_catalog()

    if missing_hy:
        print(f"{len(missing_hy)} component(s) have no Armenian witness -- "
              f"catalog NOT written:")
        for text in missing_hy:
            print(f"  - {text!r}")
        print("\nBackfill via _MANUAL_HY_OVERRIDES (with justification) or fix the "
              "underlying source, then rerun.")
        return 1

    with open(CATALOG_PATH, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {len(catalog)} observances to {CATALOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
