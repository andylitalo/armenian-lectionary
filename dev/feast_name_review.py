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
  source_en  EXACTLY what the source publishes in English, before any correction
  approved_en the English the engine must serve. THIS COLUMN IS THE GROUND TRUTH.
  source_hy  the source's own Armenian for the same component, as an independent witness
  approved_hy the Armenian the engine must serve -- the Armenian counterpart of
             ``approved_en``, and stated on every row for the same reason it is: a
             decision, not an override. It equals ``source_hy`` wherever the scrape is
             right, which is 394 rows of 397.
  note       why it was changed, or what is being asked

The two languages are deliberately symmetric: ``source_*`` is what sacredtradition.am
published and is never edited, ``approved_*`` is what we serve. Keeping ``source_hy``
separate is what lets the Armenian stay the independent witness that justifies most of the
English fixes -- an edit to ``approved_hy`` cannot quietly erase the evidence for one.

To review: open the file in a spreadsheet (tabs are the separator; GitHub also renders it
as a table), edit ``approved_en`` (or ``approved_hy``) where the text should read
differently, and say why in ``note``. Nothing else needs touching -- leave the ``source_*``
columns alone, they are the record of what was published.

A changed ``approved_en`` makes ``tests/test_feast_name_review.py`` fail with the row that
disagrees; rebuilding (see CLAUDE.md) makes it pass again. For a whole component the row
IS the registration -- ``dev/build_ground_truth.py`` freezes it and ``apply_ground_truth``
serves it, with no second entry anywhere. That failure is deliberate: it is what stops a
reviewed decision from being quietly lost the next time the artifacts are rebuilt.

``id`` is the observance's frozen catalog id -- the key a consumer stores instead of the
display text, which moves. It is STATED here, never derived from the text, which is what
lets a name be corrected without the identity moving with it. Assign one only for a
component the engine actually serves as a single observance; leave it empty for a row that
is a whole day rather than one component, or whose text the engine never emits. Never
change an id that has shipped.

``source_hy`` is refreshed from the scrape every run. ``approved_hy`` is not: like
``approved_en`` it is carried over, and defaults to ``source_hy`` only on a row that has
never had one.

Refreshing this file NEVER discards human edits: ``id``, ``approved_en``, ``approved_hy``
and ``note`` are carried over by ``source_en`` key, and a row whose approved text no longer
matches what the engine serves is reported rather than overwritten.

Usage:
    python dev/feast_name_review.py             # refresh (preserving edits)
    python dev/feast_name_review.py --check     # report drift, write nothing
"""

import collections
import csv
import datetime
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
from armenian_lectionary.engine import (                                # noqa: E402
    _FEAST_SEP, FEAST_NAMES_HY_PATH, MAX_YEAR, MIN_YEAR, _eve_label, _position_label,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_PATH = os.path.join(HERE, "feast_name_review.tsv")
FIELDS = ("status", "days", "last", "source_en", "id", "approved_en", "source_hy",
          "approved_hy", "note")

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
        "engine._POSITION_FAMILIES, already a deliberate fix. A different 'approved_en' here "
        "has no effect on what is served.",
    "Sixth Sunday of Great Lent, Sunday of the Advent":
        "the served form (period, 'the Advent') is a hardcoded template in "
        "engine._POSITION_FAMILIES, already reviewed. 'Sunday of the Second Coming' would "
        "be a real theological content change, not a mechanical fix -- needs explicit "
        "sign-off before it could go anywhere, and even then requires an engine.py edit "
        "since a text correction here has no effect on what is served.",
    "Fast day":
        "TWO open questions, both deferred as their own change. (a) Is a fast marker a "
        "NAME at all? It is arguably an attribute of the day -- served in its own field, "
        "the way is-a-fast already is -- rather than a component of what the observance "
        "is called. (b) If it stays a name, the ordinary-time instances should say which "
        "fast: 1,575 of the 2,108 served days are the generated Wed/Fri position label "
        "(784 Wed, 783 Fri, plus 8 Advent-fast weekdays on Dec 9), and those are the "
        "weekly fast, not a generic one. The remaining 533 are stored table text inside "
        "Holy Week and the week-long fasts, where Wed/Fri is not the reason -- so the two "
        "groups need different answers and cannot be folded together. Not corrected here "
        "because either answer rewrites Liturgical Day on >2,000 days, needs an "
        "engine._POSITION_FAMILIES change plus a table rebuild, and would move the "
        "omission ratchet in test_feast_name_raw off 0. 'Beginning of the Weekly Fasts' "
        "(the Friday after Ascension) is already named on the assumption this lands: once "
        "Wed/Fri carry their own labels that day reads '... -- Friday Fast -- Beginning "
        "of the Weekly Fasts' and needs no further change.",
}

# Why a row has no ``id`` -- keyed by the SOURCE spelling, like OPEN_QUESTIONS, so the
# explanation survives a rebuild. An empty id is a deliberate statement ("this row is not
# one served observance"), and without a reason beside it the only way to tell that from an
# oversight is to re-derive the whole argument. Two shapes, both the source's doing:
#
#   * a WHOLE DAY the source published as one string, whose halves are separately served
#     and separately identified;
#   * a GLUED or ONE-OFF variant the table's unanimity rule overrides -- no date emits it
#     and no table entry stores it, so an id here could never be matched by a consumer.
#
# Three of these carried an id in 1.3.0 and are retired by name in
# build_observance_catalog._RETIRED_IDS. The reason is stated in both places on purpose: a
# reviewer reading the TSV never opens that file.
NO_ID_REASONS = {
    "Fast day, Remembrance of the Ten Virgins":
        "no id: a whole DAY, not one observance -- the source comma-joined the day's fast "
        "marker to its commemoration, and a registered correction splits them. Both halves "
        "are their own rows with their own ids (fast_day, remembrance_of_the_ten), so the "
        "day resolves component-wise to the pair.",
    "Saint Sargis the Warrior and his son Martiros and his Fourteen Soldiers, and Saints "
    "Atom and his soldiers":
        "no id (retired sargis_the_warrior_and): the source glued two commemorations into "
        "one string on 2008-01-21 alone. The engine serves only the first half there, and "
        "both halves already have ids of their own (sargis, atom), so nothing emits or "
        "stores this text -- an id on it could never be matched.",
    "Saint Theodore the General":
        "no id (retired theodore_the_general): published on exactly one day out of 9,861 "
        "(2016-02-13), where every other year at that coordinate says Theodore the TYRON "
        "-- which is what the table serves (id theodore_the_tyron). A source one-off, not "
        "a second observance.",
    "Saints Eugenius, Marcarius, Alerius, Canditus and Aquila, and Saints Andrew the "
    "General and his army, and Callinicus and Diomedes the Martyrs":
        "no id (retired eugenius_macarius_valerius_candidus_2): the source glued two "
        "commemorations into one string on 2009-01-27 alone. The engine serves only the "
        "first half there, and both halves already have ids of their own "
        "(eugenius_macarius_valerius_candidus, andrew_the_general_and).",
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


def generated_components():
    """{component -> (days, last date)} for labels the ENGINE composes, over the full range.

    The cache cannot enumerate these. A position label the source prints less specifically
    than its own Armenian is corrected on read (source_corrections.illuminator_fast_label),
    so the served component exists on no cached day under that spelling -- yet it is a
    component the engine serves and therefore needs a reviewed name and an id like any
    other. Enumerated by calling the generators, so no ordinal or season combination is
    missed.
    """
    days = collections.Counter()
    last = {}
    d = datetime.date(MIN_YEAR, 1, 1)
    end = datetime.date(MAX_YEAR, 12, 31)
    while d <= end:
        iso = d.isoformat()
        for label in (_position_label(d), _eve_label(d)):
            if label:
                days[label] += 1
                if label not in last or iso > last[label]:
                    last[label] = iso
        d += datetime.timedelta(days=1)
    return days, last


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
    """{source_en -> row} of what a human has already entered."""
    if not os.path.exists(REVIEW_PATH):
        return {}
    with open(REVIEW_PATH, encoding="utf-8", newline="") as fh:
        return {r["source_en"]: r for r in csv.DictReader(fh, delimiter="\t")}


def build_rows():
    days, last = source_components()
    gen_days, gen_last = generated_components()
    hy = armenian_map()
    existing = read_existing()
    rows, drift = [], []

    # A generated label the source also publishes is already a cache row; only the ones it
    # does not get added, keyed by their own text (there is no rawer form of them to key on).
    # Compared against the CORRECTED cache text: the raw spelling of a row whose name was
    # folded ("Saint" -> "St.") never equals the generated label, and treating those as new
    # would duplicate rows that already exist under their raw key.
    already = {corrected(src) for src in days}
    generated_only = set(gen_days) - already
    for label in generated_only:
        days[label] = gen_days[label]
        last[label] = gen_last[label]

    for src in sorted(days):
        served = src if src in generated_only else corrected(src)
        prior = existing.get(src)
        approved = (prior or {}).get("approved_en") or served
        note = (prior or {}).get("note") or ""

        if approved != served:
            # A human asked for a different name and the engine does not serve it yet.
            drift.append((src, served, approved))

        if src in OPEN_QUESTIONS and not note:
            note = OPEN_QUESTIONS[src]
        # Stated ahead of the generic "registered correction" note below: these rows ARE
        # registered corrections, but that is not the interesting fact about them.
        if src in NO_ID_REASONS and not note:
            note = NO_ID_REASONS[src]
        status = "review" if src in OPEN_QUESTIONS else (
            "generated" if src in generated_only else
            "fixed" if served != src else "ok")
        if not note and status == "fixed":
            note = ("reviewed correction: this row IS the registration -- "
                    "build_ground_truth.py freezes approved_en and apply_ground_truth serves it")
        if not note and status == "generated":
            note = ("engine-composed label; the source prints a less specific English "
                    "text here -- see dev/source_corrections")

        source_hy = armenian_for(approved, hy)
        rows.append({
            "status": status,
            "days": days[src],
            "last": last[src],
            "source_en": src,
            "id": (prior or {}).get("id") or "",
            "approved_en": approved,
            "source_hy": source_hy,
            # Defaults to the scrape only on a row that has never carried a decision;
            # once stated it is preserved, exactly as approved_en is.
            "approved_hy": (prior or {}).get("approved_hy") or source_hy,
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
    no_hy = [r for r in rows if not r["approved_hy"]]
    hy_fixed = [r for r in rows if r["approved_hy"] != r["source_hy"]]

    if "--check" not in sys.argv:
        write(rows)
        print(f"wrote {REVIEW_PATH}")
    print(f"{len(rows)} components: " +
          ", ".join(f"{n} {s}" for s, n in sorted(by_status.items())))
    print(f"{len(hy_fixed)} row(s) where approved_hy differs from the scraped source_hy")
    if no_hy:
        print(f"{len(no_hy)} with no approved Armenian (the source publishes none for "
              "these -- fill approved_hy, with a note): "
              + ", ".join(r["source_en"][:40] for r in no_hy[:6]))
    if drift:
        print(f"\n{len(drift)} row(s) where the approved name is NOT what the engine "
              "serves -- rebuild so the row takes effect (CLAUDE.md gives the order), and "
              "rebuild:")
        for src, served, approved in drift:
            print(f"  source   {src}")
            print(f"  served   {served}")
            print(f"  approved {approved}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
