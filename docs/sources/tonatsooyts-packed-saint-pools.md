# Packed saint pools — when one printed line carries several canons, and when it must not

> **Source / provenance:** Տօնացոյց (*Tōnatsʿoyts*), **Second Volume preface, Sixth**
> (p. 556); **First Volume p. 526** (the gap-length rubric, stated of the autumn interval); **Second Volume p. 574**
> (a leap-year unpacking note, printed in the small cursive / նօտր գիր); **First Volume
> pp. 461–462** (the post-Theophany pool itself). Quoted from
> `grabar-ocr/corpus/book.english.md` and `book.grabar.md`, both page-anchored.
>
> **Rule governed:** whether the engine may add a companion canon the Second Volume
> abbreviated away — `engine._PACKED_POOLS`, `engine._drop_owned_companions`,
> `engine._canons_with_own_day`. Companion to
> [tonatsooyts-prelent-cohort.md](tonatsooyts-prelent-cohort.md), which records the same
> rule's first application (the Mark/Pionius canon).

---

## The warrant, and the half that was missing

**Second Volume preface, Sixth** (p. 556, `book.english.md:4175`):

> The feasts of the Saints for the most part are set down **plurally** in our Tonatsuyts
> from its original state, that is, two, three, four, five, and others, many or few,
> **which are always celebrated together indivisibly**, as you see. These we have likewise
> placed in the First Volume as before. But when we mention such in this Second Volume,
> **we have placed only the name of the first saints in many places for the sake of
> brevity**; nevertheless, when you encounter such feasts in this Second Volume, you must
> celebrate, along with the first-named saint, all the other companions following him,
> **and commemorate their names by that canon as they are set down in the First Volume**.

Grabar (`book.grabar.md` ~L7684):

> Վեցերորդ. Տօնք Սրբոցն ըստ մեծի մասին յոգնակի են եդեալք ի Տօնացուցիս մերում ի բնէ անտի…
> **որք միշտ ի միասին տօնին անբաժան**… Բայց զայսպիսիս ի յիշելն մեր յԵրկրորդ հատորոջս,
> **զանուն առաջնոց սրբոցն միայն եդաք ի բազում տեղիս վասն կարճելոյ բանին**. սակայն ի
> հանդիպելն քոյ այսպիսեաց տօնից յԵրկրորդ հատորոջս, **պարտիս ընդ առաջնոյ եդեալ սրբոյն եւ
> զայլ զամենայն հետեւեալ ընկերսն նորին տօնել**, եւ զանուանս նոցին այնու կանոնաւ յիշել՝
> որպէս եդեալք են ի յԱռաջին հատորոջն։

The engine honoured the first clause and stopped there. The sentence has two:

1. a printed line may abbreviate companions away — so the engine may serve them;
2. the companions are commemorated **by that canon** — and the First Volume sets each
   canon down **once**.

Clause 2 is the condition on clause 1. Where the taregir gave a companion a day of its own,
adding it back to the head canon's day commemorates the same canon twice in one year.

## The canons are separate to begin with — First Volume pp. 461–462

The pool is printed as a chain, each entry with its own tone, psalm, Alleluia and four
readings, each appearing exactly once:

| # | Canon (p. 461 unless noted) |
|---|---|
| 1 | Saint Anton the Anchorite |
| 2 | King Theodosius, and the Children of Ephesus |
| 3 | Cyriacus [Kirakos] and his mother Julietta |
| 4 | Vahan of Goghtn |
| 5 | The Holy Anchorites: Tryphon, Parsamas and Onuphrius |
| 6 | The Holy Patriarchs: Athanasius and Cyril |
| 7 | The Holy Martyrs: Gordius, Polyeuctus and Grigoris |
| 8 | Eugenia the virgin, her father Philip, her mother Claudia, her brothers, the two Eunuchs (p. 462) |
| 9 | Gregory the Theologian (p. 462) |
| 10 | Eugenius, Macarius, Valerius, Candidus and Aquila (p. 462) |

The connective is «Ապա» — *"Then [the feast] of…"* — a laydown operator, not a list
separator. Andrew the General is not on these pages; his canon is at p. 527, and he is in
the pool on preface **Seventh**'s warrant instead (the feasts that "frequently shift and
are celebrated in various and different intervals").

## Why they run together — First Volume p. 526

Packing is a property of the **year**, never of the saints: a pool has to fit into however
many saint weekdays a movable fast leaves in front of it, and that count changes with the
taregir. The book states the mechanism outright — for a **different** interval, the autumn
one, which is why the quote names the Fast of the Holy Cross and not the Fast of the
Catechumens (`book.english.md:2885`, immediately before "Fourth Sunday after the Holy
Mother of God"):

> Understand, O **lover of feasts**, **if the interval of eating meat is three weeks**,
> these are the feasts that are set down up to this point. And the fourth Sunday becomes
> the Eve of the Fast of the Holy Cross; at that time, the feasts set down below are
> celebrated in another place. But if the meat-eating period is four weeks, **add one week
> here**, in which the feasts set down below are celebrated, and the fifth Sunday becomes
> the Eve of the Fast. And in such years, sometimes **the Apostles James and Simon, being
> separated from Thomas, are celebrated on the Saturday of this week.** The Directory
> [Tarekirk] shows you all this.

The last clause is the rule read backwards, and it is the decisive one: given an extra week,
a normally-glued triad **splits**. Gluing is what the book does when it runs out of days —
stated here of the Assumption-to-Holy-Cross interval, and the same arithmetic governs the
Theophany-to-Catechumens run this pool sits in and the post-Vardavar run it overflows into.
For the pool itself the book does not argue the point; it performs it, on p. 574.

## The book performing the repair — Second Volume p. 574

This taregir's default line is `Anton, and Tryphon, Barsamas and Onuphrius the hermits` —
the exact string the engine served on all six `hermit_sts_tryphon_barsauma` duplicate days.
The leap-year note beside it (`book.english.md:5201`, grabar `book.grabar.md:9184`):

(Letters normalized: the English corpus prints the year-letter as `8 [Te / Թ]` and `9 [To /
Թ]`, OCR of the Armenian — see the caveat below.)

> 25. Saturday. Tone 4 Plagal. Anton, and Tryphon, Barsamas and Onuphrius the hermits.
> **If the year-letter is [ԹԸ] in a leap year, on this Saturday do not celebrate Anton,
> because it was celebrated under the first letter Թ after the Theophany**; but on Saturday
> celebrate Theodosius; on Monday, Kyriakos; on Tuesday, Vahan; and **on Thursday, Tryphon
> with their companions.** But in ordinary years, as it is set, celebrate in this manner.

> **25. Շբ. ԴՉ.** Անտոնի, — և Տրիփոնի, Պարսամայ եւ Ոնոփրիոսի ճգնաւորացն։ **Եթէ նահանջ
> ամի [ԹԸ] իցէն տարեգիրն, դու յայս շաբաթի օրս զԱնտոնն մի՛
> տօնիցէս, զի տօնեցաւ յառաջին գիրն Թ յետ ծննդեանն**. այլ ի շաբաթի օրն զԹէոդոսն.
> յերկուշաբաթին՝ զԿիրակոսն. յերեքշաբաթին՝ զՎահանն, և ի հինգշաբաթին՝ **զՏրիփոնն տօնեսցէս
> իւրեանց ընկերօքն**։

Given room, Tryphon takes its own Thursday — *with its own companions*, the same rule one
level down. The book never prints a canon twice.

Note also the shape of the suppression: *"do not celebrate Anton **here**, because it was
celebrated under the first letter Թ"*. Five more of these exist (pp. 584, 593, 610, 619,
627), and they are what makes a canon legitimately reachable from two different seasonal
pools — the January and post-Vardavar runs draw on each other's overflow. So "this canon
already has a day" is a question about the **liturgical year**, not about a season.

---

## How the engine uses this (`engine._drop_owned_companions`)

- `_PACKED_POOLS` holds the two pools **by id**, enumerated from pp. 461–462 and 464–465 —
  never inferred from how similar two strings look.
- `_canons_with_own_day(ly)` walks the liturgical year (Heesnak to Heesnak) and collects the
  canons that **head** a day: the first pool component the day carries. That is the year's
  actual laydown, read off the engine's own pre-overlay output rather than re-derived.
- `_drop_owned_companions` drops a later pool component when it shares the head's pool and
  that year gave it a day. The head is never dropped — it owns the day, its id, and its
  readings — so the operation only ever removes a name.

It is a **per-date overlay**, in the `_apply_position_label` family, because the packing is
stored against a liturgical *coordinate* that civil years disagree about: an artifact edit
would be wrong in the years where the packing is right.

Results and the residual are in
[`observance-name-corrections.md` §7b](../observance-name-corrections.md); the invariant is
enforced by `dev/audit_duplicate_commemorations.py` and
`tests/test_duplicate_commemorations.py`.

## Caveats on these pages

- p. 574 has **column bleed** (`corpus/STRUCTURE.md` gotcha #5, `docs/andys_notes.md`);
  stray index numerals there are digitization defects, not text.
- Every Second Volume leap-rule note is set in **small cursive (նօտր գիր)**, which
  `corpus/ERRATA.md` identifies as the corpus's worst OCR failure mode. Verify a specific
  taregir letter against the line images before treating it as authoritative — the rule
  quoted above is load-bearing for its *shape*, not for the letters `ԹԸ`.
- p. 593's `ՂՁՉ` is an OCR hallucination (a taregir is one letter or a reverse-consecutive
  pair); it is not quoted here for that reason.
