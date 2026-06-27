# The Great Paschal Cycle Index (Տօնացոյց year-letter table)

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*), appendix, **p. 637** (the
> 532-year perpetual cycle table). Transcribed to
> [`great_paschal_cycle_index.csv`](great_paschal_cycle_index.csv) by the project
> owner. Decoder / validator: [`../../dev/paschal_index.py`](../../dev/paschal_index.py).

This note records **what the table is, what its two codes mean, the closed-form that
reproduces it, and — crucially — that it is a *Julian* artifact and what that implies
for the Gregorian lectionary the engine computes.**

---

## What the table gives

For every civil year, two Armenian-letter codes:

- **Veradir** (Վերադիր, the *epact*) — the lunar position in the **19-year Metonic
  cycle**. Purely periodic: it depends only on `(year − 1909) mod 19`. (Verified: the
  19 column-values repeat exactly down the whole table.)
- **Taregir** (Տարեգիր, the *year-letter* / Dominical letter) — see below. Leap years
  carry **two** Taregir letters.

The page header states the layout explicitly: «ՅԱՌԱՋՆՈՒՄ ՏՈՂԻ … ԵՆ **ՎԵՐԱԴԻՐՔ**, ԻՍԿ
Ի ՏՈՒՓՍ ԵՆ **ՏԱՐԵԳԻՐՔ**» — *"in the topmost line are the Epacts; in the boxes are the
Year-letters."* Rows step by 19 years; each row holds 19 consecutive years.

---

## Decoding the Taregir: it is a code for the **Julian Easter date**

The Taregir letter, taken in Armenian-alphabet order, is exactly the **Julian-calendar
Easter date**, one letter per possible date across the 35-day Paschal range:

| Ա | Բ | Գ | … | Ժ | Ի | … | Փ |
|---|---|---|---|---|---|---|---|
| Mar 22 | Mar 23 | Mar 24 | … | Mar 31 | Apr 1 | … | Apr 25 |

Position *k* (Ա = 1 … Փ = 35) ⇒ Julian Easter on **March 21 + k**. In a leap year the
**second** letter is this Easter-date code; the first is the bissextile (solar /
weekday) adjustment.

This is a **closed form** — `dev/paschal_index.py::taregir_for(year)` computes it from
the Julian Easter algorithm with no table at all.

### Validation (and one OCR correction)

`taregir_for` reproduces **all 171 transcribed years** (1909–2079). It originally
disagreed on exactly one: **2034**, where the OCR read **Ջ** but the Julian Easter
(Mar 27 Julian = Apr 9 Gregorian) is **Զ**. Independently confirmed — 2062, also a
genuine **Ջ** year, has Julian Easter Apr 17 — so 2034 was a transcription error and
has been **corrected to Զ** in the CSV. The table now validates 171/171.

> Practical upshot: because the Taregir is a closed form, the table can be regenerated
> or extended to any year, and any future OCR can be checked against it automatically
> (`python dev/paschal_index.py`).

---

## Why it is **Julian**, and what that means for the engine

The Taregir tracks **Orthodox / Julian** Easter, not Gregorian. Grouping the cached
years (2001–2026) by Taregir and checking both Easters:

| Taregir | Years | Gregorian Easter | Orthodox (Julian) Easter |
|---|---|---|---|
| Ե | 2007, 2018 | Apr 8, **Apr 1** ✗ | Apr 8, Apr 8 ✓ |
| Յ | 2011, 2022 | Apr 24, **Apr 17** ✗ | Apr 24, Apr 24 ✓ |
| Խ | 2017, 2023 | Apr 16, **Apr 9** ✗ | Apr 16, Apr 16 ✓ |

Same-Taregir years agree on Orthodox Easter **6/6** but on Gregorian Easter only
**3/6**. The engine (and sacredtradition.am) target **Gregorian** Easter — which is
why `calculate_gregorian_easter` validates at ~98% and the extreme years are the
*Gregorian* extremes (2008 Mar 23, 2011 Apr 24).

**Therefore the Taregir is not a usable Gregorian year-key**: two years with the same
letter can have different Gregorian movable arrangements. This table is the master key
for the **classical / Julian** calendar (and for Julian-reckoning bodies such as the
Armenian Patriarchate of Jerusalem), not for the modern Gregorian engine directly.

---

## Can we "adjust to Gregorian"? — yes, by splitting the calendar out

You do **not** convert the Julian letters into Gregorian ones (the Gregorian Easter is
just computed directly from the year). The useful move is to recognise that the
lectionary separates into a calendar-independent part and a calendar-specific part:

- **Movable propers** are indexed by **Easter-offset** (days from Easter). This is
  **calendar-independent**: "Easter − 40" is the same liturgical day, with the same
  readings, whether Easter is reckoned Julian or Gregorian. The engine already keys
  these (`E` / `EB`).
- **Fixed feasts** (civil dates) and their **collisions** with movable days are
  calendar-specific — these are the canon rules in this directory (Annunciation,
  fast-suppression, octave, …).

So a **Julian** source of movable propers — the Տօնացոյց's per-letter arrangement (the
"Second Volume", one *Khoran* per Taregir) — re-indexed by Easter-offset **transfers
to the Gregorian engine for free**, because the offset is the same in both calendars.
This decoder (Taregir → Julian Easter date → offset frame) is exactly what makes that
re-indexing mechanical.

### Why this matters for the accuracy ceiling

The engine's irreducible block is the **single-sample extreme-Easter years** (2008,
2011) — offsets the 26-year Gregorian cache saw only once. More Gregorian ground truth
is the obvious fix but is unavailable. The Julian route is the alternative: those same
Easter-offsets recur in **non-extreme** Julian years, so a Julian per-letter source
would supply their **movable** propers without any new Gregorian data. Only the
**fixed-feast collisions** landing on those offsets would still need the Gregorian
canons. That makes the Տօնացոյց's per-letter Second Volume the highest-value artifact
to obtain next — and this index is the key that unlocks it.

---

## Files

- [`great_paschal_cycle_index.csv`](great_paschal_cycle_index.csv) — `year, taregir, veradir` (1909–2079), validated, 2034 corrected.
- [`../../dev/paschal_index.py`](../../dev/paschal_index.py) — `taregir_for`, `julian_easter[_gregorian]`, `validate_csv`; run directly to re-validate.
