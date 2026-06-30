# Second Volume — per-year-type cycles, coverage, and the section-index

> **Source:** Տօնացոյց (*Tōnats'oyts'*) **Second Volume** (Fourth Jerusalem Edition,
> 1915 — therefore **Julian**), pp. ~555–643. Human-corrected OCR + translation in
> `grabar-ocr/runs/human__proj__tess__gemini-min/`. Tooling:
> [`../../dev/second_volume_coverage.py`](../../dev/second_volume_coverage.py),
> [`../../dev/second_volume_index.py`](../../dev/second_volume_index.py).

## What the Second Volume is
One **day-by-day calendar per year-type** (per calendar-letter), giving for each civil
date: weekday, tone, Sunday-number (movable position), **saint/feast identity**, fast
markers, and hymn incipits. Its editorial preface (pp. 555–557) states the operating
rules:

- **It carries no readings** — every entry says "See Volume 1." It supplies the
  *coordinate* (year-type → date → position + saint); readings come from the First
  Volume / the engine's cache.
- **Point Sixth** — saints are "set down plurally … celebrated together indivisibly …
  only the name of the first saint" is printed; celebrate all companions. → defines the
  canonical **saint groups** (the engine's "merge" rule).
- **Point Seventh** — names the *frequently-shifting* feasts: those after the Nativity
  (penitential), after the 2nd week of Vardavar, and the Assumption-week tail (Andrew
  the General & Adrian; Abraham & Khoren; Adeodatus). → exactly the engine's
  floating-saint ceilings.
- **Point Third** — per-letter **leap-year** exceptions (e.g. "when the year is leap and
  the letter is 19, do not celebrate Theodosius here") deterministically resolve the
  saint splits the engine could only guess (e.g. Eugenia-solo vs Eugenios).

## Coverage measurement (`dev/second_volume_coverage.py`)
Over 2014–2026 the engine leaves **50** days non-validated. Of these, **42** have their
feast/saint **named in the Second Volume**; the **floating-saint block is 22/22**:

| Source bucket | days | named in SV |
|---|---:|---|
| `generative-saint` (floating saints) | 22 | **22** |
| `algorithmic-estimate` (Feb 13 Presentation eve, Nov 21, …) | 16 | 16 |
| `generative-composite` (Annunciation Apr 7) | 4 | 4 |
| `generative-continua` (Fast-of-Assumption Wed/Fri) | 8 | 0 — *readings, out of SV scope* |

The only uncovered days are the **lectio-continua fast days**, which need First-Volume
*readings*, not the Second Volume's skeleton — so the Second Volume covers every
non-validated day it is *supposed* to.

> **"Named" ≠ "auto-resolved."** Naming is necessary but not sufficient. Full resolution
> needs (a) the **section→letter index** below, to know which cycle applies to a given
> year, and (b) the **Julian→Gregorian** laydown (saints by civil-date, movable by
> Easter-offset). Those are engineering, not more translation.

## The section-index
`second_volume_index.csv` has **one row per calendar letter Ա..Ք (36)** — the full
year-type space. The calendar letter (`taregir`) is taken as correct; each row records
where that year-type's Second-Volume section is and which "Cycle of the Romans" it is.

| column | meaning |
|---|---|
| `taregir` | the calendar letter (row key), Ա..Ք |
| `easter_md_julian` | the Julian Easter date that letter encodes (Ա=Mar22 … Փ=Apr25) |
| `page` | page where that letter's Second-Volume section begins |
| `cycle` | the **Cycle of the Romans** number (1–7) printed in the section heading |

### The section heading and the cycle number
The heading printed at each section is **ԵՕԹՆԵՐԵԱԿ ՀՌՈՄԱՅԵՑՒՈՑ #** — *"Septenary of the
Romans #"* (the English OCR renders the word inconsistently as "Seven-**year** / Seven-**day**
/ Seven-**week** cycle of the Romans" — they are all the **same Armenian phrase**). The
number `#` runs **1..7 descending** as the letter advances, wrapping 1→7, so it is a closed
form of the letter position:

```
cycle(pos) = ((11 - pos) % 7) + 1          # anchored on Ի (pos 11) = 1
```

Verified against every printed heading Ա..Ի (4, 3, 2, 1, 7, 6, 5, 4, 3, 2, 1) and the later
detected sections (Ծ, Կ, Ճ, Մ, Ս). The `cycle` column is filled by this formula for all 36.

### Verifying / maintaining it
- **Read pages from the scan, not the translation.** The `page` column points to the page
  scan; the grabar `merged.md` `## page_NNNN_human` heading is a secondary check. The
  English translation is regenerable OCR — never the source of truth.
- **Source of truth:** this CSV (repo, version-controlled). Never hand-edit the translation
  files for these labels.
- `python dev/second_volume_index.py scaffold` rebuilds the 36 rows (cycle = closed form;
  existing `page` values preserved, blanks filled from the translation by Easter match) —
  safe to re-run as the translation is corrected/extended.
- `python dev/second_volume_index.py validate` parses the cycle number printed at each
  filled `page` and flags any that disagree with the row's `cycle` — i.e. a **misattached
  page**. (This caught p. 619, whose heading prints cycle 4 = `Ս`, not `Վ`/cycle 3; the
  page was moved to `Ս` accordingly.)

**Open items:**
- 23 letters still have no `page` (their section's Easter line wasn't on the first page, so
  the detector couldn't pin them). They fall in page order between the filled rows.
- Row **`Ք`** (36th letter) has no Easter: the Julian Easter range is only 35 dates
  (Mar 22–Apr 25). Confirm whether `Ք` is a real distinct cycle, a leap-only variant, or
  unused.

## Related
- [`great_paschal_cycle_index.md`](great_paschal_cycle_index.md) — civil year → Taregir
  (the lookup that selects which section above applies to a year).
