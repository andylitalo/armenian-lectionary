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

## The section-index — how to verify and label
`second_volume_index.csv` has **one row per calendar letter Ա..Ք (36)** — the full
year-type space. Each row's identity is its letter and the Julian Easter date that letter
encodes; the Second-Volume section that teaches that year-type is attached **by matching
Easter date**. Columns:

| column | filled by | meaning |
|---|---|---|
| `taregir` | tool | the calendar letter (row key), Ա..Ք |
| `easter_md_julian` | tool | the Julian Easter date that letter encodes (Ա=Mar22 … Փ=Apr25) |
| `page`, `header` | tool | the detected Second-Volume section whose Easter matches (12 of 36 so far) |
| **`letter_printed`** | **human** | the Armenian letter **printed at that section's head** |
| **`verified`** | **human** | `y` once checked |
| **`notes`** | **human** | leap-variant, "see letter X" cross-refs, OCR issues |

**Sections are attached by Easter date, not by the printed header letter — deliberately.**
The printed labels may be **offset** from the paschal-table convention: p. 557's section
puts Easter on **March 22** (= `Ա` here) yet is **headed `Գ`**. Whether the Second Volume's
lettering is shifted from the paschal table is the key thing to settle; until then,
Easter-date attachment is convention-independent and correct.

**Where to verify the printed letter:** read it from the **page scan** named in the `page`
column (authoritative), or the human-corrected grabar `merged.md` `## page_NNNN_human`
header as a secondary check. **Do not** read it from the English translation — regenerable
OCR.

**Source of truth to edit:** this CSV (repo, version-controlled). **Never** hand-edit the
translation files for labels — the OCR pipeline can regenerate and clobber them. Humans
touch only `letter_printed` / `verified` / `notes`.

**Keeping it from getting lost:**
1. `python dev/second_volume_index.py scaffold` rebuilds the 36 rows and re-attaches
   sections **without** touching your human columns (merge-safe, keyed by `taregir`) —
   safe to re-run after the translation is corrected/extended.
2. `python dev/second_volume_index.py validate` reports every row where `letter_printed`
   differs from `taregir`, **with the offset**. A *constant* offset across rows is the
   smoking gun for the labeling convention (then we shift once and reconcile); a *one-off*
   offset means that row's page or Easter is misread.
3. The `verified` column is the progress tracker; this note + `docs/README.md` are the
   durable pointers so the scheme survives context loss.

**Open items to resolve while verifying:**
- The `Գ`-vs-`Ա` offset at p. 557 (above) — fill a few `letter_printed` and run `validate`
  to see whether the shift is constant.
- Row **`Ք`** (36th letter) has no Easter: the Julian Easter range is only 35 dates
  (Mar 22–Apr 25). Confirm whether `Ք` is a real distinct cycle, a leap-only variant, or
  unused.
- 24 letters still have no `page`: their sections were among the ones the detector
  couldn't pin (Easter line not on the section's first page). The detected-but-unattached
  section pages are 566, 568, 573, 575, 590, 592, 601, 605, 607, 624, 627, 630, 632, 635
  — candidates to slot into the empty letters (they fall in page order between the
  attached ones).

## Related
- [`great_paschal_cycle_index.md`](great_paschal_cycle_index.md) — civil year → Taregir
  (the lookup that selects which section above applies to a year).
