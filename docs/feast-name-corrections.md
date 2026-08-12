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

Detection: [`dev/audit_source_anomalies.py`](../dev/audit_source_anomalies.py) (nine
detectors) plus a read of all 187 commemoration components by hand — the corpus is small
enough that exhaustive human review is practical, and two of the corrections below came
only from that.
Enforcement: `tests/test_source_text.py` (the detectors stay silent) and
`tests/test_feast_name_review.py` (the engine serves the approved names).
Registry: `dev/source_corrections._FEAST_TEXT_FIXES` and `_FEAST_SPELLING_FIXES`.

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
πεντηκոստή, fiftieth. `Fifteenth` is wrong on all three.

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
| `Begining of the Fast` | `Beginning of the Fast` | Plain misspelling; `Սկիզբն պահոց`. |
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

---

## Open questions — NOT corrected

These are recorded in `dev/feast_name_review.tsv` with `status = review`. The source stands
as published until someone who reads Armenian decides. Enter the preferred English in the
`approved` column of that file.

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

## Reviewing

```bash
python dev/feast_name_review.py          # refresh the table (never discards edits)
python dev/feast_name_review.py --check  # report rows the engine does not yet serve
python dev/audit_source_anomalies.py     # hunt for NEW errors in the source
```

Edit `approved` in `dev/feast_name_review.tsv`, say why in `note`, and
`tests/test_feast_name_review.py` will fail until the fold is registered in
`dev/source_corrections._FEAST_TEXT_FIXES` and the artifacts are rebuilt (CLAUDE.md gives
the order). That failure is deliberate — it is what stops a reviewed decision from being
lost the next time the artifacts are rebuilt.
