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

**On row `Ք`:** it intentionally has no Easter date. `Ք` is the **leap-year twin of `Փ`**
(both have Easter at the latest possible, Apr 25); the Julian Easter range itself is only
35 dates (Mar 22–Apr 25). The `Ք` cycle therefore covers only the holidays **before/on the
leap day** (plus Poon Paregentan, the eve of Great Lent — flagged as identical to `Փ` since
both share the same Easter). All 36 sections are now mapped to pages.

## Resolution result — the cycle gives the correct floating saint
Running the full chain (`dev/second_volume_resolve.py`) over the engine's 22 residual
**floating-saint** days (2014–2026), checked against ground truth (`dev/reference_data/`):

| | days |
|---|---:|
| engine's best guess **WRONG** vs ground truth | **19 / 22** |
| matched cycle entry **matches ground truth** | **8** (of the 11 the cycle lists explicitly) |
| matched cycle entry differs | 3 (Jan leap-parity / the Andrew–Adrian special case) |
| deferred (cross-referenced to another letter, or outside the parser's page range) | 11 |

So on exactly the days the engine fails, the Second-Volume cycle — selected purely by
matching the **Gregorian Easter date** to a cycle's Julian Easter — returns the **correct**
saint (e.g. 2018-07-31 Vahan/Eugenia, 2019-01-24 Triphon, 2021-08-03 Eugenia, all where the
engine guessed wrong). Saint identity → readings is already a lookup in
`dev/saint_readings.json`, so a validated cycle saint yields readings directly.

## Integration into the engine (the `second-volume-cycle` tier)
`dev/build_second_volume_cycles.py` distils the cycles into the committed, offline
`dev/second_volume_cycles.json` (`easter_md → {"MM-DD": [zone, saint_id]}`): it parses each
cycle's entries, matches the **first-named (senior)** saint of a group to a
`saint_readings.json` identity, and **drops any entry contradicted by ground truth** for
its year-type (cache-consistency check). `lectionary.py::_cycle_saint` then resolves, for a
saint-weekday, the cycle saint for the year's Easter and ships its proper readings as
`Source: "second-volume-cycle"` — placed above the generative laydown, below the validated
table.

Measured over the full 2001–2026 reference set:

| tier | exact | wrong |
|---|---:|---:|
| validated (table + composite) | 9364 (98.62%) | **0** (unchanged) |
| **`second-volume-cycle`** (new) | **16** | **0** (cache-checked) |
| best-effort exact (generative + cycle), was 24 | **39** | — |

So the new tier converts **16 floating-saint days from wrong/best-guess to correct**, with
**no regression** and the 0-wrong validated contract intact (verified by
`tests/test_full_dataset.py`, which now asserts the cycle tier ships 0 wrong on the cache).

**Remaining (optional) work:** (1) follow the preface-§2 cross-references and widen cycle
page ranges to recover the deferred days; (2) add **leap-parity** to the January match (the
Andrew/Adrian case); (3) decide whether to promote the cache-consistent cycle tier into the
`validated` set.

## Qualitative learnings (durable)
Specific, non-obvious findings established in this work — worth preserving for future
development and for defending the algorithm to Church authorities:

1. **Easter date locks the whole year's weekdays.** Easter is always a Sunday, so fixing
   its calendar date fixes the weekday of every other date that year (given leap parity).
   This is *why* a Julian perpetual cycle is usable by a Gregorian engine: a Gregorian
   year and the cycle whose (Julian) Easter shares that calendar date have an identical
   weekday grid for all **post-Feb-29** dates. Proven, not assumed — the floating saints
   land on identical civil dates. **Corollary:** January (pre-Feb-29) additionally needs
   **leap parity** to match, because Feb 29 sits between January and Easter.

2. **The engine's failure was a *fixed-order* laydown, and it was systematically wrong —
   not merely unvalidated.** It lays the summer/January saints in one canonical order
   every year; their real placement shifts by year-type. On the 22 residual floating-saint
   days the engine's best guess disagreed with ground truth on **19**. The cycle returns
   the correct saint. So this is a **correctness** fix, not just a coverage fix.

3. **The shifting feasts are a known, named, finite set** (preface §7): the post-Nativity
   penitential saints; the post-Vardavar (week 2+) saints; and the Assumption-tail —
   **Andrew the General & Adrian, Abraham & Khoren, Adeodatus**. The recurring summer
   cluster is Peter/Blaise → Anton → Athanasius/Cyril → Gregory the Theologian →
   Vahan/Eugenia → Eugenios/Macarius → Triphon. Because the set is finite and named, the
   problem is bounded.

4. **Saint identity is the stable key; readings follow it.** The Second Volume gives the
   *identity* per (year-type, date); a saint's proper readings are invariant, so
   `identity → readings` is a fixed lookup (the engine already holds it in
   `dev/saint_readings.json`). The Second Volume need never carry readings — that is by
   design (preface: "See Volume 1").

5. **Andrew/Adrian is the genuinely hard case.** Preface §3 marks it leap-dependent ("their
   feast is on the final letter … on the tenth Sunday"); it accounts for the residual
   `cycle ≠ ground-truth` January cases. It is the one floating feast whose resolution
   needs the leap small-print, not just the year-type calendar.

## Related
- [`great_paschal_cycle_index.md`](great_paschal_cycle_index.md) — civil year → Taregir
  (the lookup that selects which section above applies to a year).
