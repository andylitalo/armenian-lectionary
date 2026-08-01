"""DEV-ONLY: build and refresh ``dev/feast_name_review.tsv`` -- our OWN ground truth
for the English feast names.

Why a second ground truth. ``dev/reference_data/`` is sacredtradition.am's, and the engine
now reproduces it on 9496/9496 days -- which means it reproduces its typos too. That cache
answers "does the engine match the source?"; it cannot answer "is the name right?". This
file answers the second question: one row per distinct feast-name component, with the
approved English spelling a human has signed off on. ``tests/test_feast_name_review.py``
holds the engine to it.

Columns:

  status     ok        served text equals the source's, and has been read and accepted
             fixed     a registered correction changed it (see dev/source_corrections)
             review    an open question -- the ``note`` says what is uncertain
  days       how many days in 2001-2026 carry this component
  first      earliest date carrying it, for looking it up on sacredtradition.am
  source     EXACTLY what the source publishes, before any correction
  approved   the English the engine must serve. THIS COLUMN IS THE GROUND TRUTH.
  armenian   the source's own Armenian for the same component, as an independent witness
  note       why it was changed, or what is being asked

To review: open the file in a spreadsheet (tabs are the separator; GitHub also renders it
as a table), edit ``approved`` where the English should read differently, and say why in
``note``. Nothing else needs touching -- leave ``source`` alone, it is the record of what
was published.

A changed ``approved`` makes ``tests/test_feast_name_review.py`` fail with the row that
disagrees. Registering the corresponding fold in
``dev/source_corrections._FEAST_TEXT_FIXES`` and rebuilding (see CLAUDE.md) makes it pass
again. That failure is deliberate: it is what stops a reviewed decision from being quietly
lost the next time the artifacts are rebuilt.

Refreshing this file NEVER discards human edits: ``approved`` and ``note`` are carried over
by ``source`` key, and a row whose approved text no longer matches what the engine serves
is reported rather than overwritten.

Usage:
    python dev/feast_name_review.py             # refresh (preserving edits)
    python dev/feast_name_review.py --check     # report drift, write nothing
"""

import collections
import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dev.analyze import REF_DIR                                        # noqa: E402
from dev.source_corrections import (                                   # noqa: E402
    normalize_confusables, normalize_feast_spelling, normalize_position_label,
)
from armenian_lectionary.engine import _FEAST_SEP, FEAST_NAMES_HY_PATH  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_PATH = os.path.join(HERE, "feast_name_review.tsv")
FIELDS = ("status", "days", "first", "source", "approved", "armenian", "note")

# Open questions -- keyed by the SOURCE spelling, so they survive a correction landing.
# Each is a name that reads oddly but that nothing available settles: the Armenian is
# itself a transliteration, or the awkwardness is the source's English style rather than
# an error. They are deliberately NOT corrected; this is the list to review.
OPEN_QUESTIONS = {
    "Saints Jacoc and Themistocles":
        "'Jacoc' is not an English name. hy 'Յակովկայ' is the genitive of Յակովիկ "
        "(a diminutive of Jacob/James), so this is plausibly 'Jacob' -- but 'Jacovk' or "
        "'Hakovik' would transliterate the Armenian more closely. Which?",
    "Saint Theodoron the Martyr":
        "hy 'Աստուածատրոյ' is Astvatsatur, 'God-given' -- the Armenian name usually "
        "rendered Theodore. 'Theodoron' looks like a half-declined Greek form. Should "
        "this be 'Theodore the Martyr', or is Theodoron the intended distinct form?",
    "Staint Gregory the Illuminator's coming out of Pit":
        "Missing article, and lowercase 'coming' where the companion feast reads "
        "'Commitment to the Pit'. 'Coming out of the Pit'? Left alone as the source's "
        "own wording rather than silently rewritten.",
    "The Twelve Holy Doctors of Church: Hierotheus of Athens, Dionysius the Areopagite, "
    "Sylvester of Rome, Athanasius of Alexandria, Cyril of Jerusalem, Ephraim the Syrian, "
    "Basil the Great, Gregory of Nyssa, Gregory the Theologian, Epiphanius of Cyprus, "
    "John Chrysostom, and Cyril of Alexandria":
        "'of Church' is missing an article -- 'of the Church'. Also the longest name "
        "served, at 289 characters.",
    "Saints martyrs Antoninus, Theophilus, Anicetus and Potinus":
        "Lowercase 'martyrs' where 'Saints Virgins' and 'Saints Princes' are capitalised. "
        "Capitalise for consistency, or leave as published?",
    "Saints virgins Indes and Domna, and Clericus the Priest along with the 20,000 "
    "Martyrs of Nicomedia":
        "Lowercase 'virgins' -- same question as the row above.",
    "Saint Nicolas Wonderworker the Bishop of Myra":
        "Reads 'Nicholas Wonderworker' after the spelling fold; the other two components "
        "naming him say 'the Wonderworker'. Add the article?",
    "Saints Gregory and Nicholas the Wonderworkers, and other Nicholas the Bishop and "
    "Myron the Bishop":
        "'and other Nicholas' -- hy 'միւս Նիկողայոսի' is 'the other Nicholas'. Add the "
        "article?",
    "Saints Joachim and Anna, parents of the Holy Mother of God, and of Myrophores":
        "'and of Myrophores' is hard to parse; the Myrophores are the myrrh-bearing "
        "women. 'and of the Myrophores'?",
    "Saints Vardan the General and His Companions - the 1036 Martyrs who died in the "
    "Great Battle":
        "Uses a hyphen where the source's own component separator is an em-dash. Left as "
        "published because it sits INSIDE a component, but it may be meant as a break.",
    "Commemoration of 318 Fathers of the Holy Council of Nicea (AD 325)":
        "'Nicea' -- the usual English is Nicaea (or Nicea). Accepted as a variant, not "
        "folded. Confirm the preferred form.",
    "Discovery of Relics of St. Gregoris the Catholicos of Aghvank, and the Holy Fathers "
    "Tatоul, Varus and Thomas, Anton and Cronides, and the Seven Herbivorous Hermits":
        "'Herbivorous Hermits' renders hy 'խոտաճարակացն' literally (grass-eating). The "
        "usual English is 'the Seven Grass-eating Hermits'. Preferred form?",
    "Saints Menas, Hermogenes, Eugraphus and the poor mans John and Alexis":
        "Corrected to 'the poor men'. But hy 'կամաւոր աղքատացն' is the VOLUNTARY poor -- "
        "'the voluntary poor John and Alexis' may be the intended sense. Confirm.",
    "Saints St. Aret and His Companions, the martyrs Artemius and Christopher and the "
    "Women Callinice and Aquilina":
        "The doubled title was dropped. 'Aret' renders hy 'Խարիթեանցն'; the saint is "
        "usually Arethas of Najran in English. 'Saints Arethas and His Companions'?",
}


def corrected(text):
    """The served English for a raw source component.

    The full ``apply_source_corrections`` chain minus its date-scoped part: one entry in
    ``POSITION_LABEL_FIXES_BY_DATE`` fixes a wrong ordinal on a single date, which is a
    property of that day rather than of the component.
    """
    return normalize_position_label(
        normalize_feast_spelling(normalize_confusables(text)))


def armenian_for(approved, hy):
    """The source's Armenian for ``approved``, per component.

    A whole-string lookup first; failing that, join the per-component forms -- one
    correction splits a component in two ("Fast day, Remembrance of the Ten Virgins"), so
    the joined form was never scraped as a single string even though both halves were.
    """
    if approved in hy:
        return hy[approved]
    parts = [p.strip() for p in approved.split(_FEAST_SEP) if p.strip()]
    if len(parts) > 1 and all(p in hy for p in parts):
        return _FEAST_SEP.join(hy[p] for p in parts)
    return ""


def source_components():
    """{raw component -> (days, first date)} straight from the cache, uncorrected."""
    days = collections.Counter()
    first = {}
    for path in sorted(glob.glob(os.path.join(REF_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        iso = rec["date"]
        for comp in [c.strip() for c in (rec.get("feast") or "").split(_FEAST_SEP)
                     if c.strip()]:
            days[comp] += 1
            if comp not in first or iso < first[comp]:
                first[comp] = iso
    return days, first


def armenian_map():
    if not os.path.exists(FEAST_NAMES_HY_PATH):
        return {}
    with open(FEAST_NAMES_HY_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("feasts", data) if isinstance(data, dict) else {}


def read_existing():
    """{source -> row} of what a human has already entered."""
    if not os.path.exists(REVIEW_PATH):
        return {}
    with open(REVIEW_PATH, encoding="utf-8", newline="") as fh:
        return {r["source"]: r for r in csv.DictReader(fh, delimiter="\t")}


def build_rows():
    days, first = source_components()
    hy = armenian_map()
    existing = read_existing()
    rows, drift = [], []

    for src in sorted(days):
        served = corrected(src)
        prior = existing.get(src)
        approved = (prior or {}).get("approved") or served
        note = (prior or {}).get("note") or ""

        if approved != served:
            # A human asked for a different name and the engine does not serve it yet.
            drift.append((src, served, approved))

        if src in OPEN_QUESTIONS and not note:
            note = OPEN_QUESTIONS[src]
        status = "review" if src in OPEN_QUESTIONS else (
            "fixed" if served != src else "ok")
        if not note and status == "fixed":
            note = "registered correction; see dev/source_corrections._FEAST_TEXT_FIXES"

        rows.append({
            "status": status,
            "days": days[src],
            "first": first[src],
            "source": src,
            "approved": approved,
            "armenian": armenian_for(approved, hy),
            "note": note,
        })
    return rows, drift


def write(rows):
    with open(REVIEW_PATH, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t",
                           lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)


def main():
    rows, drift = build_rows()
    by_status = collections.Counter(r["status"] for r in rows)
    no_hy = [r for r in rows if not r["armenian"]]

    if "--check" not in sys.argv:
        write(rows)
        print(f"wrote {REVIEW_PATH}")
    print(f"{len(rows)} components: " +
          ", ".join(f"{n} {s}" for s, n in sorted(by_status.items())))
    if no_hy:
        print(f"{len(no_hy)} with no Armenian witness (the source publishes none for "
              "these): " + ", ".join(r["source"][:40] for r in no_hy[:6]))
    if drift:
        print(f"\n{len(drift)} row(s) where the approved name is NOT what the engine "
              "serves -- register each in dev/source_corrections._FEAST_TEXT_FIXES and "
              "rebuild:")
        for src, served, approved in drift:
            print(f"  source   {src}")
            print(f"  served   {served}")
            print(f"  approved {approved}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
