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
  last       latest date carrying it, for looking it up on sacredtradition.am
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
    apply_ground_truth, normalize_confusables, normalize_feast_spelling,
    normalize_position_label,
)
from armenian_lectionary.engine import _FEAST_SEP, FEAST_NAMES_HY_PATH  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_PATH = os.path.join(HERE, "feast_name_review.tsv")
FIELDS = ("status", "days", "last", "source", "approved", "armenian", "note")

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

    # Found during the atomic-unit / Wikipedia-verification review pass.
    "Saint Virgins Juliana and Basilla":
        "possible duplicate: the same two saints are also named 'The Holy Virgins Juliana "
        "and Basilla' elsewhere in the corpus (a different phrasing, never published "
        "alone). Same commemoration worded inconsistently across years, or two different "
        "occasions?",
    "Saints Cornelius the Centurion, Simeon the Relative of Christ, martyred in "
    "Jerusalem, Polycarp the Bishop of Smyrna, and the Martyrs that perished in the East":
        "possible duplicate: the companion row drops 'the Relative of Christ' from "
        "Simeon's name. Same group worded inconsistently across years, or intentional?",
    "Saints Cornelius the Centurion, Simeon, martyred in Jerusalem, Polycarp the Bishop "
    "of Smyrna, and the Martyrs that perished in the East":
        "possible duplicate: the companion row includes 'the Relative of Christ' after "
        "Simeon's name. Same group worded inconsistently across years, or intentional?",
    "Saints Gregory the Wonderworker, Nicholas the Bishop and Myron the Bishop":
        "possible duplicate: the companion row names a second, 'other' Nicholas "
        "('Saints Gregory and Nicholas the Wonderworkers, and other Nicholas the Bishop "
        "and Myron the Bishop'). Same group worded inconsistently across years, or a "
        "genuinely different day?",
    "Saint Gregory the Illuminator's Sons and Grandsons: Saints Aristakes, Vrtanes, "
    "Housik, Grogoris and Daniel":
        "Wikipedia's own article (St. Vrtanes I) spells these 'Aristaces' and 'Husik', "
        "not 'Aristakes'/'Housik' -- but Armenian Church diocese sites are inconsistent "
        "on this convention generally (cf. Ghevond vs Ghevont). Wikipedia form or "
        "church-website form?",
    "Saints Eustachius, his wife Theopista and their two sons, and the Holy Virgins "
    "Hermione and Catherine":
        "'Catherine' is suspect: the Armenian is 'Նեքտարինեայ', which starts with Ն "
        "(N), not Կ (K) as 'Catherine' would. Eustace's own known family are his sons "
        "Agapius and Theopistus, not daughters -- this may be an unrelated commemoration "
        "glued onto his day. Could not identify the intended English name.",
    "Saints Eugenios, Makarios, Valerian, Candidus and Aquila":
        "folded to match the registered spelling of the same group elsewhere (Eugenius, "
        "Macarius, Valerius, Candidus, Aquila) for consistency, but the standard Orthodox "
        "'Eugene/Candidus/Valerian/Aquila of Trebizond' is a group of FOUR -- no Macarius "
        "at all. Armenian tradition may add a fifth companion, or this may be an "
        "inherited error further upstream. Worth a closer look.",
    "Eve of Fast of Advent":
        "do not fold to 'Eve of the Fast of Advent' -- this is the engine's deliberate "
        "dual-form reproduction (engine._advent_eve_label): the source writes it two ways "
        "depending on whether Heesnak falls 9 or 10 weeks after Exaltation, and both are "
        "correct as published.",
    "Second Sunday of Great Lent, Sunday of the Expulsion":
        "the served form (period, not comma) is a hardcoded template in "
        "engine._POSITION_FAMILIES, already a deliberate fix. A different 'approved' here "
        "has no effect on what is served.",
    "Sixth Sunday of Great Lent, Sunday of the Advent":
        "the served form (period, 'the Advent') is a hardcoded template in "
        "engine._POSITION_FAMILIES, already reviewed. 'Sunday of the Second Coming' would "
        "be a real theological content change, not a mechanical fix -- needs explicit "
        "sign-off before it could go anywhere, and even then requires an engine.py edit "
        "since a text correction here has no effect on what is served.",
}


def corrected(text):
    """The served English for a raw source component.

    The full ``apply_source_corrections`` chain minus its date-scoped part: one entry in
    ``POSITION_LABEL_FIXES_BY_DATE`` fixes a wrong ordinal on a single date, which is a
    property of that day rather than of the component.
    """
    return normalize_position_label(
        normalize_feast_spelling(normalize_confusables(apply_ground_truth(text))))


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
    """{raw component -> (days, last date)} straight from the cache, uncorrected."""
    days = collections.Counter()
    last = {}
    for path in sorted(glob.glob(os.path.join(REF_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        iso = rec["date"]
        for comp in [c.strip() for c in (rec.get("feast") or "").split(_FEAST_SEP)
                     if c.strip()]:
            days[comp] += 1
            if comp not in last or iso > last[comp]:
                last[comp] = iso
    return days, last


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
    days, last = source_components()
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
            "last": last[src],
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
