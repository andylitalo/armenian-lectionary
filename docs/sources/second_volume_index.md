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
`second_volume_index.csv` maps each printed Second-Volume section ("Roman cycle …") to
its calendar-letter. Columns:

| column | filled by | meaning |
|---|---|---|
| `page`, `header` | tool | where the section starts |
| `easter_md_inferred` | tool | the Julian Easter date stated inside the section |
| `taregir_inferred` | tool | the Taregir that Julian Easter implies (Ա=Mar22 … Փ=Apr25) |
| **`letter_printed`** | **human** | the Armenian letter **printed at the section head** |
| **`verified`** | **human** | `y` once checked |
| **`notes`** | **human** | leap-variant, "see letter X" cross-refs, OCR issues |

**Where to verify:** read the Armenian letter from the **page scan** named in the `page`
column (the authoritative source), or the human-corrected grabar `merged.md`
`## page_NNNN_human` header as a secondary check. **Do not** read it from the English
translation — that is regenerable OCR.

**Source of truth to edit:** this CSV (in the repo, version-controlled). **Never** hand-
edit the translation files for labels — the OCR pipeline can regenerate them and clobber
your work. Humans touch only `letter_printed` / `verified` / `notes`.

**Keeping it from getting lost:**
1. `python dev/second_volume_index.py scaffold` refreshes the tool columns **without**
   touching your verified columns (merge-safe, keyed by page+header) — safe to re-run.
2. `python dev/second_volume_index.py validate` cross-checks every `letter_printed`
   against `taregir_inferred` and flags disagreements — the same closed-form check that
   caught the 2034 error in `great_paschal_cycle_index.csv`. A mismatch means either the
   printed letter or the Easter OCR is wrong; resolve before trusting that row.
3. The `verified` column is the progress tracker; this note + `docs/README.md` are the
   durable pointers so the scheme survives context loss.

> First discrepancy to resolve: p. 557's header reads **Գ**, but its first Easter line
> infers **Ա** — verify which is correct against the scan.

## Related
- [`great_paschal_cycle_index.md`](great_paschal_cycle_index.md) — civil year → Taregir
  (the lookup that selects which section above applies to a year).
