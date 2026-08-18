# Feast-name corrections: where the engine departs from sacredtradition.am

The engine reproduces sacredtradition.am's feast name on **every one of the 9,496 days it
publishes** for 2001–2026. That is the accuracy contract, and it has a consequence worth
stating plainly:

> Matching the source perfectly means reproducing the source's mistakes perfectly.

This document records every place the engine deliberately does **not** reproduce the
source, and the evidence for each. It is the companion to
[`dev/feast_name_review.tsv`](../dev/feast_name_review.tsv), which lists all 392 distinct
name components with the approved English spelling, the source's own Armenian, and the
questions still open.

## How a correction is justified

Only one kind of evidence counts: **the source contradicting itself.** Never an editorial
preference, never "this reads better."

The strongest form of that evidence is the source's own Armenian. sacredtradition.am
publishes each day in English and in Armenian independently, so the two are separate
witnesses to the same feast — and where they disagree, one of them is wrong on the
publisher's own account. That is an oracle no amount of cross-year comparison provides: a
mistake the source makes in all 26 years is invisible to every consistency check, and
visible immediately in the Armenian.

Where nothing establishes the intended form, the source stands as published and the
question is recorded in the review table instead. Those rows are listed at the bottom.

### The one declared exception: disambiguation

A name can be *wrong* in a way self-contradiction cannot detect: correct as far as it goes,
and still not identifying the observance it names. "Fast day" was the case that forced the
distinction — one string standing for six different observances (§5). There the Armenian
happened to be more specific, so the repair fit the rule above. It does not always.

So there is exactly one other admissible justification, and it is deliberately narrow. A
**disambiguation** may land when all four hold:

1. the served text does not identify the observance a reader is looking at;
2. **both** languages are equally unspecific, so no self-contradiction exists to appeal to
   — if the Armenian *is* more specific, this is an ordinary §1 correction, not this;
3. what the observance actually is can be established from the calendar itself, not from
   preference — its date, its position, and what the surrounding days do;
4. the added words state only that established fact, and contradict nothing the source says.

This is a weaker warrant than the rest of this document and is meant to stay rare: one
correction uses it (§6). "This reads better" still never qualifies, and neither does a name
that is merely terse — §6 changes a name that gives the reader no way to tell *which* fast
begins, on the only day of the year that it does.

Detection: [`dev/audit_source_anomalies.py`](../dev/audit_source_anomalies.py) (nine
detectors) plus a read of all 187 commemoration components by hand — the corpus is small
enough that exhaustive human review is practical, and two of the corrections below came
only from that.
Enforcement: `tests/test_source_text.py` (the detectors stay silent) and
`tests/test_feast_name_review.py` (the engine serves the approved names).
Registry: the `approved_en` / `approved_hy` columns of `dev/feast_name_review.tsv`, and
nothing else. `build_ground_truth.py` freezes the row and `apply_ground_truth` resolves a
component by whole-component lookup — `source_en` and `approved_en` are both keys, and the
answer is always `approved_en` verbatim. There is no substring pass and no word-level fold,
so a correction can only ever land on the component a reviewer actually looked at.

---

## 1. Factual — the English contradicts the Armenian

| Day | Source (English) | Source (Armenian) | Served |
|---|---|---|---|
| Aug 4 (Council of Ephesus) | `… of Ephesus (AD 341)` | `… (431 թ.)` | `… (AD 431)` |
| Pentecost | `PENTECOST (Fifteenth day of Eastertide)` | `ՀՈԳԵԳԱԼՈՒՍՏ (Պենտեկոստէ՝ յիսներորդ օր ի Զատկէն)` | `PENTECOST (Fiftieth day of Eastertide)` |
| Dec 9 (Conception of the Theotokos) | `Feast day` | `Պահք` | `Fast day` |

**Ephesus.** The Third Ecumenical Council met at Ephesus in **431**. `341` is a digit
transposition, and the source's own Armenian gives `431 թ.` on the same day.

**Pentecost.** `յիսներորդ` is *fiftieth*. Three independent confirmations: the Armenian;
the arithmetic (the day is Easter + 49, and the source's own Eastertide count reaches
`Forty Ninth day of Eastertide` the day before); and the word *Pentecost* itself, from
Greek for "fiftieth". `Fifteenth` is wrong on all three.

**Dec 9.** `Fast`, mistyped `Feast` — one letter, on the same row where the source also
writes `Fiest of the Conception`. Three independent confirmations:

- `Feast day` appears on **no other date** in the 9,861-day English corpus. A genuine
  marker meaning "this is a feast" would not be unique to one December day in a calendar
  this dense with feasts.
- It appears only on **Mon, Tue, Wed and Fri**, and is absent on Thu and Sat (16 of 16
  either way; Sunday is claimed by the Advent Sunday count). That is the Advent-fast
  weekday set. It cannot be describing the feast: Dec 9 is the same feast every year, so a
  feast marker would appear on Thursdays too. It tracks the **fast**.
- The source's own Armenian for the component reads `Պահք` — *fast*.

The third witness is the one the catalog surfaced. Consolidating display text onto one
id-keyed entry put `Feast day → Պահք` and `Fast day → Պահք` side by side, which is how a
seven-year-old typo became visible.

None of these three errors varies by year, so none could have been found by comparing
years — only by reading the source against itself.

## 2. Grammatical — the Armenian settles the sense

| Source | Served | Armenian, and what it shows |
|---|---|---|
| `… and the poor mans John and Alexis` | `… the poor men …` | `կամաւոր աղքատացն` — plural. (See the open question below: it is also *voluntary* poor.) |
| `… deacons and many faithfuls` | `… many faithful` | `ժողովրդոցն` — the people; `faithfuls` is not an English plural. |
| `Gregory of Theologian` | `Gregory the Theologian` | `Գրիգորի Աստուածաբանին` — Gregory **the** Theologian. |
| `Saint Patriarchs Barlaam, …` | `Saints Patriarchs …` | `Սրբոց հայրապետացն` — plural. |
| `Saint Virgins Juliana and Basilla` | `Saints Virgins …` | `Սրբոց կուսանացն` — plural; and the source itself writes `Saints Virgins Nune and Mane` on other days. |
| `Clement the Bishop Rome` | `Clement the Bishop of Rome` | A dropped preposition. |

## 3. Mechanical slips

| Source | Served | Why |
|---|---|---|
| `… and Saints Saints Jacoc and Themistocles` | `… and Saints Jacoc …` | The word typed twice. |
| `Saints St. Aret and His Companions …` | `Saints Aret …` | Two titles stacked on one name. |
| `Discovery of the Holy Cross.` | `Discovery of the Holy Cross` | A trailing period no other component carries; the Armenian `Գիւտ խաչի` has none. |
| `Begining of the Fast` | `Beginning of the Weekly Fasts` | Plain misspelling; the rest of the change is the §6 disambiguation. |
| `… Ignatius the Bishop of Antiosh …` | `… of Antioch …` | Ignatius of **Antioch**. |
| `Fast day, Remembrance of the Ten Virgins` | `Fast day — Remembrance of the Ten Virgins` | The day's fast marker comma-joined into the commemoration. The source's own Armenian for that day separates the two with the component separator, as does its English on all 2,139 other fast days. |
| `Fiest of the Conception …` | `Feast of the Conception …` | Long-standing scrape typo, now folded in the same place as the rest. |

## 4. One saint, two spellings

The source refers to the same person two ways. Each is folded to the form the source uses
more often, which is also the standard English one.

| Minority form | Majority form | Same person? |
|---|---|---|
| `Phillip` (the Apostle, and Eugenia's father) | `Philip` | Yes — `Փիլիպպոսի` in both Armenian renderings. |
| `Nicolas` (of Myra) | `Nicholas` | Yes — `Նիկողայոս` throughout. |
| `Gregoris` (Catholicos of Aghvank) | `Grigoris` | Yes — `Գրիգորիսի`. The repo already folded a third spelling, `Grogoris`. |

These three are the most debatable corrections here: `Phillip` and `Nicolas` are both
legitimate English spellings, and only the source's inconsistency argues against them.
Each is a one-line revert if the preferred form is the other one.

## 4b. One name, two spellings — in Armenian

The same policy as above, applied to `language="hy"`. The source's Armenian varies its own
spelling across years, and `dev/fetch_translations.py` pairs each English name with the
Armenian of **one** representative day — so whichever day it sampled decides what ships,
for every occurrence of that name. That is a coin flip, not a decision.

The engine serves the form the source uses **most often**, and `dev/audit_hy_variants.py`
is what makes that checkable: it counts every witness in `dev/reference_data_hy/` and
reports any catalog entry serving a minority spelling.

| Name | Source publishes | Served |
|---|---|---|
| Presentation of the Theotokos | `Ս. Աստուածածնի` ×4, `ս. Աստուածածնի` ×2, `ս.Աստուածածնի` ×1 | `Ս. Աստուածածնի` |
| Fast of the Catechumens | `Առաջաւորաց` ×8, `Առաջաւորի` ×2 | `Առաջաւորաց` |
| Sundays after Nativity | `զկնի Ս. Ծննդեան` ×9, `զկնի Ծննդեան` ×1 | `զկնի Ս. Ծննդեան` |
| Days of Great Lent | `Մեծի պահոց` ×40, `Մեծի Պահոց` ×1 | `Մեծի պահոց` |

Only the first was wrong: the catalog was serving `ս.Աստուածածնի` — lowercase, and missing
the space after the abbreviation dot — on **every Nov 21**, because that 1-of-7 day is the
one the pairing sampled. Fixed by folding the two Presentation ground-truth rows into one,
after which the pairing's own vote picks the majority. The other three were already
correct, and are listed here so they are not "fixed" into the minority form later;
`dev/hy_discrepancy.py` classifies them `DOMINANT_FORM` rather than counting them against
the accuracy ratchet.

`Ը օր Զատկի. Կրկնազատիկ` belongs to the same family and is worth naming, because it looks
backwards: the source writes the Octave of Easter as one component with a period twice, and
splits it into two with an em-dash once. The period is the dominant form, so that is what
ships — reproducing the single em-dash day would be serving the minority.

### Known gap: `Նաւակատիք` on Holy Saturday

The source's Armenian ends Holy Saturday with a trailing `— Նաւակատիք` (the vigil) that its
English does not have. Resolution is driven by the English components a day has, so the
note has nothing to attach to and is dropped — every Holy Saturday.

Gluing it onto the eve's name does not work, and the source says why: when Holy Saturday
coincides with the Annunciation (2007-04-07) it prints `Նաւակատիք` **last**, after the
Annunciation, not beside the eve. It is a day-level component in its own right.

Expressing that needs an observance that exists in only one language — a design change, and
properly part of Phase 3, where ids come from storage rather than from reverse text lookup.
Until then it is counted as an `OMISSION` by `dev/hy_discrepancy.py` rather than hidden.

## 5. Position labels

Registered separately, in `POSITION_LABEL_FIXES`, because they are calendar labels rather
than commemorations: a stray trailing period on `the Fast of Nativity.` (4 occurrences, on
Jan 1, against 25 clean ones), two comma-for-period variants of `Great Lent. Sunday of …`
(1 occurrence each against 25), and one wrong ordinal word — 2008-04-07 reads `Thirteenth
day of Eastertide` where the count is 16, pinned by its own neighbours (Apr 5 is
`Fourteenth`, Apr 8 `Seventeenth`). That last is scoped to its single date, since
`Thirteenth day of Eastertide` is correct on every other year's Easter+12.

Also folded, for casing: `PRESENTATION of the Holy Mother of God to the Temple`, which the
source shouts in 19 of 26 years and title-cases in the other 7.

### The Fast of St. Gregory the Illuminator counts its days only in Armenian

The source heads the fast's five weekdays (Pentecost+22…+26) `Ա/Բ/Գ/Դ/Ե օր Լուսաւորչի
պահոց` — *First … Fifth day of the Fast of the Illuminator* — while its English prints a
bare `Fast day`, the same two words it uses on 2,139 ordinary Wed/Fri fast days. This is
the section-1 pattern applied to a position label: the source states the same fact twice
and disagrees with itself, so the more specific statement stands.

Registered as `source_corrections.illuminator_fast_label` and regenerated by a matching
`_POSITION_FAMILIES` entry, so the stored and overlaid labels agree. 130 days across
2001–2026, 135 including 2027.

The consequence reaches past the name. One English string standing for six observances
meant no consumer could tell them apart by text, and the engine carried a date-scoped side
channel purely to recover the distinction for its own Armenian resolution — the only
exception to "an observance is identified by its display text". Saying in English what the
source already says in Armenian retired that channel, and the catalog's English became a
key rather than a hint.

The Armenian confirms the repair rather than merely permitting it. The old hand-declared
block could attest days 1, 2 and 4 directly and constructed 3 and 5 by analogy; once the
English was specific enough to pair against, the scrape yielded all five, and days 3 and 5
matched the constructed forms exactly.

---

## 6. Disambiguation — `Beginning of the Fast` names no fast

| | published | served |
|---|---|---|
| en | `Begining of the Fast` | **`Beginning of the Weekly Fasts`** |
| hy | `Սկիզբն պահոց` | **`Սկիզբն շաբաթական պահոց`** |

(The `Begining` → `Beginning` misspelling is a separate §3 fold and was already registered.)

The only correction in this document justified by [disambiguation](#the-one-declared-exception-disambiguation)
rather than by the source contradicting itself. Both languages are equally unspecific —
`Սկիզբն պահոց` is "beginning of the fasts" and names no more of a fast than the English
does — so there is no second witness to appeal to. The four conditions:

**1. The text does not identify the observance.** The Armenian Church keeps ten week-long
fasts, Great Lent, the Fast of Advent and a weekly Wed/Fri fast. On a day headed only
"Beginning of the Fast", a reader has no way to tell which one begins.

**2. Neither language is more specific.** Unlike §5, where the Armenian counted the days
the English left bare.

**3. The calendar establishes what it is.** It falls on the **41st day of Eastertide,
always the Friday immediately after Ascension** — one day a year, in all 27 years
2001–2027. What the surrounding days do settles the rest: no day in Eastertide 1–40 carries
a fast marker at all, and days 46 (Wed) and 48 (Fri) do. So this is the end of the
Eastertide dispensation from the weekly Wed/Fri fast, and the day is itself the first
resumed fast rather than an announcement of one. The rule is published doctrine, not
inference — the Prelacy states the Wed/Fri fast is waived "during the forty days after
Easter (until Ascension)".

**4. The added words state only that.** `Weekly` / `շաբաթական` is the whole change.

Not **"after Eastertide"**, which would be false and would contradict the name it composes
with: the day is *in* Eastertide (41 of 50), and the dispensation ends at Ascension, not at
Pentecost. The served day already reads `Forty First day of Eastertide — Beginning of the
Weekly Fasts`, so the position label supplies the coordinate and the commemoration supplies
the fact.

27 days, one per year. The catalog id **`beginning_of_the_fast` does not move** — the name
changed in both languages and the identity did not, which is the property the stated-id
design exists to provide.

`lectionary_data.json` stores this component on 8 entries (`E:40` and `EB:0–6:40`), and
`feast_names_hy.json` re-keys its two entries onto the corrected English. The documented
rebuild order was run end to end from the cache and reproduces every artifact byte for
byte, with `build_table.py` self-validating at 0 wrong over 9,496 days.

This name is provisional in one direction only: it anticipates the [`Fast day`
question](#fast-day--a-name-or-an-attribute) below. If the weekly Wed/Fri fasts get their
own labels, the day reads `… — Friday Fast — Beginning of the Weekly Fasts` and this
component needs no further change.

---

---

## 7. Packed days — one line, several canons

Ids were minted per distinct display string, so a commemoration the source spells several
ways became several observances. The source prints "Sts. Cyricus and His Mother Julitta" on
one year's Jan 21 and the same plus "and Sts. Gordius, Polyeuctus and Grigoris" on
another's. `cyricus_and_his_mother`, `_2` and `_3` were one feast, and a consumer
persisting `_2` had no way to learn it.

**The Tōnats'oyts explains the varying strings itself**, in the Second Volume's preface,
**Sixth** (p.556, `grabar-ocr/corpus/book.english.md`):

> The feasts of the Saints for the most part are set down **plurally** in our Tonatsuyts
> from its original state… **which are always celebrated together indivisibly**… But when
> we mention such in this Second Volume, **we have placed only the name of the first saints
> in many places for the sake of brevity**; nevertheless… you must celebrate, along with
> the first-named saint, all the other companions following him, **and commemorate their
> names by that canon as they are set down in the First Volume**.

— `զանուն առաջնոց սրբոցն միայն եդաք ի բազում տեղիս վասն կարճելոյ բանին`
(`book.grabar.md:7683`).

That last clause is the operative one. **Each saint is its own canon**, and the First
Volume proves it: pp.460–462 sets out Anton · Theodosius and the Children of Ephesus ·
Cyriacus and Julietta · Vahan of Goghtn · Tryphon, Parsamas and Onuphrius · Athanasius and
Cyril · Gordius, Polyeuctus and Grigoris · Eugenia's household · Gregory the Theologian ·
Eugenius and companions — ten consecutive canons, each with its own propers. pp.464–465
does the same for the pre-Lent cohort, including the Atomian Generals and the Mark/Pionius
group separately.

**Why they run together.** That pool has to fit between the fixed Theophany and the movable
Fast of the Catechumens, and the gap changes length with the taregir. So each Second Volume
year-type *packs* the canons onto however many days it has, and abbreviates the resulting
line. A line like `Sts. Vahan of Goghtn, Gordius, Polyeuctus and Grigoris` is therefore a
**day**, not an observance.

So the observance is the canon and the id follows the canon:

```
approved_en:  Sts. Cyricus and His Mother Julitta — St. Vahan of Goghtn — Sts. Gordius, Polyeuctus and Grigoris
              ← "Saints Cyricus and His Mother Julitta, and Saints Vahan of Goghtn, Gordius, Polyeuctus and Grigoris"
```

Eleven rows split this way; each keeps `id` empty and says why, exactly as the comma-joined
`Fast day, Remembrance of the Ten Virgins` already did. Twelve ids retired into
`_RETIRED_IDS`, all of them minted for a packed line rather than an observance, and one id
minted for the canon the source never prints alone (`gordius_polyeuctus_and_grigoris` —
always behind Cyricus or Vahan, so `source_hy` is empty and its Armenian is stated from the
run it appears in).

### What the readings evidence settled

The propers within each former group are byte-identical, which is what made the merge look
right in the first place — and it stays informative: it says the day's readings are the
**head canon's**, which is how the packing works. It also kept two look-alikes apart.
`atom_and_his_soldiers_2` ("…and Sts. Sukiasians the Martyrs") carries those four readings
**plus six more** — Leviticus 12.6-8, Proverbs 8.22-34, Ezekiel 44.1-2, Malachi 3.1-4,
Galatians 3.24-29, Luke 2.22-40 — which are the Presentation of the Lord, on Feb 13, the
eve of Տեառնընդառաջ. And `discovery_of_relics_of` was swept in only by `_FEAST_CANON_RULES`'
crude Anton predicate (`"Anton" in c and "Hermit" in c`); disjoint readings, different feast.

### The declared pools, and what they let the reports see

`dev/observance_ids._PACKED_POOLS` enumerates the two pools by **id**, from the First Volume
pages above. A day where the source prints one head canon and the engine serves that canon
plus the others packed with it is then reported as an **EXPANSION** — the book's own
instruction, visible and ratcheted, not folded into silence. Andrew the General is in the
first pool on a different warrant: his canon is at p.527, in the Assumption cycle, but the
preface (**Seventh**) names him among the feasts that "frequently shift and are celebrated
in various and different intervals", and the source does pack him into the January run.

This is also what makes the remaining gap measurable. **The engine serves one packing per
liturgical coordinate**, and which canons the source names varies by year-type. Five English
days (and four Armenian) now report as OMISSION for that reason. They were already wrong on
`origin/main` — 2008-07-28 serves Vahan with Eugenia's household where the source prints
Vahan with Gordius — but `canonical_commem`'s deliberately crude predicates folded any two
companion sets to equality, so nothing could see it. Closing them needs per-year packing
data, which moves readings provenance and belongs in its own commit.

### Two packings the engine now gets right

- **2008-01-21**, Sargis + Atom. Both are pre-Lent cohort canons at fixed Easter offsets;
  when the Presentation blocks Atom's slot he shifts onto Sargis's, and
  `_prelent_cohort_layout` used to let the senior win and drop the junior. It now joins the
  two labels on `_FEAST_SEP`. The senior keeps the day's id and its readings, so a merge
  cannot move a reading.
- **2009-01-27**, Eugenius + Andrew the General — the floating feast of preface Seventh,
  added to the `PN`-zone schedule label so the second-volume-cycle tier serves both.

### The Armenian witness column, three times over

`dev/feast_name_review.armenian_for` looks `source_hy` up in a map keyed on the **corrected**
English, and that has now failed in three distinct ways, each erasing the column that is
supposed to be the independent witness justifying a correction:

1. correcting a name **emptied** it (the map is re-keyed by `dev/fetch_translations.py`,
   which is why it is step 1 of the rebuild order);
2. approving one name for several source strings **duplicated** it across them;
3. splitting a line into canons **synthesised** it by joining the halves' Armenian, which
   makes `source_hy` equal `approved_hy` and so registers no fold at all — leaving the
   source's glued spelling reading as a contradiction on every packed day.

Rows whose approved name contains `_FEAST_SEP` now take `source_hy` from a raw-keyed pairing
(`source_armenian_map`) instead. Scoped there on purpose: the Presentation's casing-typo
pair also shares an approved name, but for that one the approved-keyed map is better,
because it votes across every year rather than the single day the Armenian cache sampled.

## 8. Accepted differences from the source

Not everything that differs is a defect, and three of these are the source disagreeing with
itself. They are listed here so that "we looked and decided" is on the record.

| Day(s) | Difference | Decision |
|---|---|---|
| 2003-02-13 | `Դ օր Առաջաւորի պահոց` vs `Առաջաւորաց` — genitive singular against genitive plural of the Fast of the Catechumens (1 witness against 2) | serve the majority |
| 2011-02-13 | `Ե կիւրակէ զկնի Ծննդեան` missing the `Ս.`, and `Բարեկենդան Առաջաւորի պահոցն` against 5 witnesses for `Առաջաւորաց պահոց` | serve the majority |
| Nov 21 | `ս.Աստուածածնի` / `ս. Աստուածածնի` / `Ս. Աստուածածնի` | serve the majority (§4b) |

Neither of the first two is correctable in `feast_name_review.tsv` as it stands: a row holds
**one** `source_hy`, sampled from one day, and these are what the source printed on another.
`DOMINANT_FORM` cannot group them either — it compares spacing and case, not declension or a
dropped word, on purpose. `dev/audit_hy_variants.py` is the standing check that we are
serving the majority form everywhere.

## 9. Additions — a day the English source names on no day at all

Every other correction in this document rewrites text the source printed. This one supplies
text it never printed in English, and that is a different kind of act, so it gets its own
category, its own registry and its own ratchet.

**Jan 1.** The source's Armenian prints `Կաղանդ. տարեմուտ` — *Kaghand, the turn of the
year* — and its English prints nothing. Three cached Armenian days attest it (2001, 2002,
2005) and on two of them it stands as its own component with no saint attached:

```
2001-01-01 hy:  Գ օր Ս. Ծննդեան պահոց — Կաղանդ. տարեմուտ
2001-01-01 en:  Third day of the Fast of Nativity
```

So the day reached English callers as a bare position label, and the pairing in
`dev/fetch_translations.py` — which matches whole strings when the component counts differ —
folded the Armenian into the position label's own entry: `third_day_of_the_4` shipped
`Գ օր Ս. Ծննդեան պահոց; Կաղանդ. տարեմուտ`. A civil-date observance hidden inside a
calendar-position label, in one language only.

### What it is called, and what that asserts

It ships as **`Blessing of the Pomegranates`** / **`Նռնօրհնէք`**, id
`blessing_of_the_pomegranates` — the *Prayer of Thanks and Pomegranate Blessing*
(`Գոհաբանական մաղթանք եւ նռնօրհնէք`), instituted by Karekin II and served at midnight at the
turn of the year in every Armenian church since about 2015.

**Be clear about what that does and does not follow from the source.** The Tōnats'oyts names
the civil day (`Կաղանդ. տարեմուտ`); it does not name the rite, which postdates the 1915
edition by a century. Naming the observance for the rite is an editorial decision about what
the day *is*, of the same kind as §6's `Beginning of the Weekly Fasts`, and it carries one
known cost: the engine serves it on Jan 1 of every year in range, including the fourteen
that precede the rite's institution. The alternative — serving `New Year's Day` before 2015
and the rite's name after — would put two ids on one day and make a consumer's stored id
depend on which year it first saw. A single stable id was judged worth the anachronism. One
line in `engine._FIXED_DATE_OBSERVANCES` reverses that if the judgement changes.

### How it is registered

There is no printed English to correct, so `apply_ground_truth` has no hook: the component
would read as a contradiction on every Jan 1, against a contract that requires zero. It is
therefore declared in two places and counted in a third:

| | |
|---|---|
| `engine._FIXED_DATE_OBSERVANCES` | `{(1, 1): "Blessing of the Pomegranates"}` — the only source of the mapping; `fixed_date_label()` is public so the review file, the catalog build and the verifiers enumerate it rather than keeping copies |
| `dev/observance_ids._ADDED_OBSERVANCES` | the ids the discrepancy reports may see without the source's English backing them |
| `FEAST_ADDITION_DAYS` | **an equality, not a ceiling** — exactly 26 days (Jan 1, 2001–2026; 2027 has no oracle) |

The equality is the point. An addition is excluded from the contradiction count by
construction, so nothing else in the suite would notice the overlay firing on the wrong
days. A count that drifts *either way* fails.

`engine._apply_fixed_date_label` inserts it after the position label and before the
commemoration — the order the source's own Armenian uses on Jan 1.

The bar for a future entry: the source must state the day in its **other** language, so the
addition closes a translation gap rather than expressing an opinion; and this section must
say what the served name asserts beyond what the source's text does.

### What it fixed on the Armenian side

`third_day_of_the_4` gives up the glued note and is just `Գ օր Ս. Ծննդեան պահոց`. Because
the new row carries `source_hy = Կաղանդ. տարեմուտ` and `approved_hy = Նռնօրհնէք`,
`ground_truth_hy_fixes` folds the source spelling and both bare Jan 1 days score exact:
`INTERNAL_DELIMITER` 7 → 5, exact 411 → 413.

2005-01-01 is the one Jan 1 that stays a contradiction, and for a reason no row can express:
there the source glues the New Year onto the **saints** (`Կաղանդ. տարեմուտ Սրբոցն Բարսղի …`)
rather than printing it as its own component, and a review row holds one `source_hy`, not
one per year.

## Open questions — NOT corrected

These are recorded in `dev/feast_name_review.tsv` with `status = review`. The source stands
as published until someone who reads Armenian decides. Enter the preferred English in the
`approved_en` column of that file.

| Component | Question |
|---|---|
| `Saints Jacoc and Themistocles` | `Jacoc` is not an English name. `Յակովկայ` is the genitive of `Յակովիկ`, a diminutive of Jacob/James — so `Jacob`? Or a closer transliteration, `Jacovk` / `Hakovik`? |
| `Saint Theodoron the Martyr` | `Աստուածատրոյ` is *Astvatsatur*, "God-given", usually rendered **Theodore**. Is `Theodoron` intended, or a half-declined Greek form? |
| `Saint Gregory the Illuminator's coming out of Pit` | Missing article, and lowercase `coming` where the companion feast reads `Commitment to the Pit`. `Coming out of the Pit`? |
| `Saints Aret and His Companions …` | `Aret` renders `Խարիթեանցն`; the saint is usually **Arethas** of Najran in English. |
| `… and the poor men John and Alexis` | `կամաւոր աղքատացն` is the **voluntary** poor — perhaps `the voluntary poor John and Alexis`. |
| `The Twelve Holy Doctors of Church: …` | `of Church` wants an article — `of the Church`. Also the longest name served, 289 characters. |
| `Saints Gregory and Nicholas the Wonderworkers, and other Nicholas …` | `միւս Նիկողայոսի` is "**the** other Nicholas". |
| `Saint Nicholas Wonderworker the Bishop of Myra` | The other two components naming him say `the Wonderworker`. |
| `Saints Joachim and Anna, … and of Myrophores` | The Myrophores are the myrrh-bearing women (`կանանցն իւղաբերից`) — `and of the Myrophores`? |
| `… the Seven Herbivorous Hermits` | Renders `խոտաճարակացն` literally (grass-eating). Usual English: `the Seven Grass-eating Hermits`. |
| `Saints martyrs Antoninus, …` / `Saints virgins Indes and Domna, …` | Lowercase where `Saints Virgins` and `Saints Princes` are capitalised elsewhere. |
| `Saints Vardan the General and His Companions - the 1036 Martyrs …` | A hyphen where the source's component separator is an em-dash; possibly meant as a break. |
| `Commemoration of 318 Fathers of the Holy Council of Nicea (AD 325)` | `Nicea` vs `Nicaea` — confirm the preferred form. |

Two of these are larger than a spelling, and blocked on each other.

### `Fast day` — a name, or an attribute?

Served on **2,108 days**, and the two halves of that number want different answers:

| Origin | Days | What it means there |
|---|---|---|
| generated position label (`engine._POSITION_FAMILIES` terminal fallthrough) | 1,575 | the **weekly** fast — 784 Wed, 783 Fri, plus 8 Advent-fast weekdays around Dec 9 |
| stored table text | 533 | Holy Week and the week-long fasts (Elijah, Assumption, post-Ascension Eastertide), where the weekday is not the reason |

So there are really two questions. **(a)** Is a fast marker part of what an observance is
*called*, or an attribute of the day that belongs in its own field? **(b)** If it stays a
name, the 1,575 ordinary-time instances should say which fast they are, rather than sharing
one string with the 533 that are a different thing — the same argument that unblocked the
Illuminator fast in §5, one level up.

Not corrected here. Either answer rewrites `Liturgical Day` on more than 2,000 days, needs
an `engine._POSITION_FAMILIES` change plus a table rebuild for the stored half, and moves
`test_feast_name_raw`'s omission ratchet off 0. It needs its own reviewed change.

§6 is already named on the assumption that it lands: `Beginning of the Weekly Fasts`, the
Friday after Ascension, reads `… — Friday Fast — Beginning of the Weekly Fasts` once
Wed/Fri carry their own labels, and needs no further change then.

## Reviewing

```bash
python dev/feast_name_review.py          # refresh the table (never discards edits)
python dev/feast_name_review.py --check  # report rows the engine does not yet serve
python dev/feast_name_review_atomic.py   # one saint per row, for reviewing them singly
python dev/audit_source_anomalies.py     # hunt for NEW errors in the source
python dev/audit_hy_variants.py          # catalog entries serving a minority Armenian form
```

`feast_name_review_atomic.py` splits the rows where the SOURCE glued two independent
commemorations onto one day, so a reviewer sees each saint once instead of once per
combination. Its output is derived and therefore not committed — run it when you want it.

Edit `approved_en` in `dev/feast_name_review.tsv`, say why in `note`, and
`tests/test_feast_name_review.py` will fail until the artifacts are rebuilt (CLAUDE.md
gives the order); the row itself is the registration. That failure is deliberate — it is what stops a reviewed decision from being
lost the next time the artifacts are rebuilt.
