# Winter-hinge progress & next steps (handoff)

Status as of branch `winter-hinge-scheduler` (commit "Crack winter hinge…").
Audience: the next agent continuing the Armenian lectionary engine.

## TL;DR

The winter ferial zone (Advent → Theophany → pre-Lent) was the project's
documented "hard zone": ~24% of all days were flagged `algorithmic-estimate`
(no readings), two-thirds of them in Nov–Feb. This pass gave winter days a
**stable grid coordinate** and let the existing strict cross-year filter learn
them. Result:

| Metric | Before | After |
|---|---|---|
| Exact match (all 4747 days) | 3607 (76.0%) | **3798 (80.0%)** |
| Wrong (table hit) | 0 | **0** |
| Accuracy where covered | 100.00% | **100.00%** |
| Winter estimate days (Nov/Dec/Jan/Feb) | 148 / 263 / 203 / 143 = **757** | 92 / 194 / 161 / 119 = **566** |

191 winter days recovered, every one cross-year-validated, **0 shipped wrong**.
The coordinate is computable for any future year (anchored to computable
feasts): `2026-12-08` — a future date with no source data — returns
validated-table readings that match the (later-scraped) ground truth.

## How to reproduce / inspect

```bash
python dev/build_table.py            # learn + strict-filter + export; prints kept/dropped per keyspace and self-validation
python dev/compare_app.py            # runtime engine vs ground truth, by source + month
python dev/slot_model.py             # winter coordinate diagnostic: kept/dropped buckets per winter keyspace
python dev/slot_model.py AdvSat      # detail one keyspace's DROPPED buckets (shows the disagreeing occupants)
python dev/slot_model.py all         # detail every dropped bucket
python lectionary.py 2026-12-08      # spot-check a single date through the real app path
```

## Architecture (what changed and why)

The engine keys a date's *liturgical coordinate* and looks it up, by precedence,
in `lectionary_data.json` (built by `dev/build_table.py`, which keeps a
coordinate ONLY if every supporting year agrees — "strict shipping"). The old
winter failure: the offset-to-anchor coordinate is unstable because saints are
laid onto free Mon/Tue/Thu/Sat weekdays in a fixed *order*, so one merge/drop
shifts every downstream day. The old `dev/slot_model.py` positional cursor hit
only 66% for exactly this reason.

**Fix:** `lectionary.py` now has a per-year scheduler (`winter_window`,
`winter_coords`, `_advent_slot`, `_postnat_slot`) that emits a stable **string**
grid coordinate per winter day, registered as new keyspaces in `WINTER_KS`,
`WINDOWS`, `PRECEDENCE`, `_KS_SEASON`. `build_table.py` picks them up with no
structural change. Lookup/load handle string keys (`INT_KEYSPACES` distinguishes
the old integer-offset keyspaces) and absent winter keys.

Two windows (see `winter_window(year)`):
- **Advent** = day after Heesnak Sunday … Jan 5 (eve of Theophany).
- **Post-Nativity** = Jan 14 (day after the octave) … eve of the Fast of
  Catechumens = `Easter − 70` (always a Sunday).
- The Theophany octave Jan 6–13 is already fully covered by the civil `C`
  keyspace (`01-05`…`01-13`), so the scheduler emits nothing there.

### Winter keyspaces and what KEEPS (kept / dropped buckets, days_kept)

```
PnJohn   1/0  (13)  John the Forerunner: Jan 14, transferred to the next
                    Mon/Tue/Thu/Sat when Jan 14 is Wed/Fri/Sun. Clean.
AoF      5/0  (56)  Opening Fast of Advent (Colossians), key = day-from-Heesnak.
AdvSun   5/2  (55)  Numbered Sundays of Advent, forward ordinal.
PnSun    3/0  (24)  Numbered Sundays after Nativity, forward ordinal.
AdvFer   9/3 (107)  Wed/Fri ferial continua, ordinal AFTER the 1st Advent
                    Sunday (NOT from Heesnak — the opening-fast week shifts
                    phase and pollutes the count).
AdvSat  13/13(147)  Advent saints, forward (week-from-Heesnak, weekday) grid.
AdvSatB  6/21 (60)  Advent saints, BACKWARD (weeks-to-Nativity, weekday) grid —
                    adds net coverage because Advent is only 6–7 wks.
PnSat    5/10 (27)  Post-Nat saints, forward (week-from-Nativity, weekday) grid.
PnFer    2/6  (15)  Post-Nat Wed/Fri ferial.
PnEve    0/1   (0)  Eve-of-Fast Sunday backward override (see "known misses").
```

### Key empirical findings (the "grammar" the data revealed)

1. **Merged days carry the SENIOR saint's readings.** In tight years
   "Anton+Triphon+Barsauma+Onouphrius" share one day and use *Anton's* solo
   readings (Triphon's are dropped). Same for "Gregory+Nicholas".
2. **Saturdays pin high-rank saints** (Athanasius&Cyril, Gregory Theologian);
   minor saints flow around them and merge/drop when weeks are scarce.
3. **Forward + backward duality.** Numbered tracks have a fixed HEAD (forward
   from the window's governing feast) and a fixed TAIL (backward from the next
   feast). E.g. the last post-Nat Sunday is always "Eve of Fast of Catechumens"
   with fixed readings regardless of its ordinal → handled by `PnEve`.
4. **Floating Marian feasts entangle.** Presentation (Nov 21) and Conception
   (Dec 9) are on fixed civil dates but their readings = [feast readings] +
   [whatever ferial/Sunday slot they land on], so they have 4–7 distinct
   reading-sets across years and can't be shipped clean. They're EXCLUDED from
   the grid via `_EMBEDDED_FIXED` so they stop polluting the fast/saint slots
   they overlap — this single change cleaned the whole `AoF` track (0→5 kept).

## What the strict filter correctly WITHHOLDS (the residual ~566 days)

These stay `algorithmic-estimate` (correct season label, no readings) — never
shipped wrong. They are genuine calendar collisions, not modeling laziness:

- **Fast-of-Nativity tail (Dec 30 – Jan 5)** and the backward post-Nat ferial:
  pure **lectio continua** (Hebrews + Luke marching daily). The reading at a
  given day depends on how many fast-days preceded it, which shifts with window
  length → no simple offset key works. See `dev/slot_model.py AdvFer` keys
  10/11 (the "First/Second/… day of the Fast of Nativity" buckets).
- **Saint merges/drops in tight years**: `AdvSat`/`PnSat` slots where a year's
  short window forces a merge (Gregory+Nicholas) or rank-drop. ~half the saint
  grid buckets.
- **Anomaly years where the Fast of Nativity squeezes out a Sunday** (2019,
  2024: the last "Advent Sunday" becomes "Eve of Fast of Nativity" and steals
  the 2nd-to-last readings) → breaks `AdvSun` tail and `PnEve` (2016
  eve-coincides-with-1st-Sunday collision).
- The embedded floating feasts themselves (Presentation, Conception, and the
  late-Dec commemorations Stephen/Peter&Paul/James&John, whose readings also
  merge with their landing slot).

## Ideas for next steps (roughly highest-leverage first)

1. **Model the ferial lectio-continua position directly.** The Wed/Fri Advent
   fast + the Fast of Nativity are ONE continuous Hebrews/Luke reading sequence.
   If you compute the continua *index* (count of fast-reading-days since the
   continua start, accounting for which days are fast days) you can predict the
   whole tail deterministically. This is the single biggest remaining block
   (~Dec 30–Jan 5 across 13 yrs ≈ 78 days, plus drifting ferials). Risk: needs
   an exact model of which days consume a continua slot; verify against
   `dev/slot_model.py` before shipping (strict filter will catch errors, but a
   wrong continua model just produces "no agreement" → still 0 wrong, lower
   coverage). Start by binning every Advent+Fast-of-Nativity day's epistle by a
   candidate continua-index and checking cross-year consistency.

2. **Composite keys for the Sunday/feast collisions.** When a numbered Sunday
   ALSO carries a backward role (eve of a fast) or a fixed feast, it's a genuinely
   different reading-set. Give those a composite coordinate (e.g.
   `PnEve` only when it is NOT also the 1st Sunday; a separate key for the
   "Sunday ∧ eve" collision) so the 12 clean years aren't dropped for 1 outlier.
   Low effort, small but clean gains (`PnEve`, `AdvSun` tail).

3. **Merge-replay scheduler for saints.** The deepest fix the plan envisioned:
   extract the canonical ordered saint list + rank tiers + merge groups (the
   diagnostic already surfaces them — e.g. Anton↔Triphon, Gregory↔Nicholas),
   then have the scheduler lay the list onto each year's actual free weekdays
   with Saturday-pinning and merge-folding, and key each physical day by the
   *senior saint's identity*. This converts the drifting `AdvSat`/`PnSat` buckets
   into stable per-saint keys. Highest effort; do it after (1) and (2). The data
   to mine is all in `dev/reference_data/`; `dev/slot_model.py` is the place to
   prototype the extraction.

4. **Serve the floating feasts' core readings.** Presentation/Conception always
   start with the same OT refs (Song of Solomon …); only the trailing ferial
   refs vary. If the project ever relaxes "exact full match" to "feast-proper
   readings", these become recoverable. Out of scope under strict shipping.

5. **Non-winter ferial gaps (explicitly out of scope this pass).** Scattered
   Mar/Apr/Jul/Aug/Sep estimate days (full Lenten weekdays, post-Transfiguration
   and solar-autumn saint tracks) use the SAME slot mechanism and can be folded
   into this engine with the same approach: define a stable grid coordinate per
   role, register a keyspace, let `build_table.py` strict-filter it. See the
   month breakdown in `compare_app.py` output (Mar 54, Apr 99, Jul 64, Aug 48,
   Sep 99).

## Files

- `lectionary.py` — runtime engine + winter scheduler (calendar math lives here).
- `dev/build_table.py` — learns + strict-filters + exports `lectionary_data.json`.
- `dev/slot_model.py` — winter coordinate extractor + miss-diagnostic.
- `dev/compare_app.py` — runtime-vs-ground-truth, by source and month.
- `dev/analyze.py` — `load_all()` reads `dev/reference_data/*.json` (13 yrs ground truth).
- `lectionary_data.json` — the shipped validated table (regenerated by build_table).
- Memory: `lectionary-winter-mechanism.md`, `lectionary-calendar-structure.md`.

## Guardrails

- **Strict shipping is the contract:** never ship a reading unless every
  supporting year agrees. Coverage rises monotonically as the scheduler
  improves; a wrong scheduler rule just lowers coverage, it does not ship wrong
  readings (the filter drops non-agreeing coordinates). Always confirm
  `compare_app.py` shows `wrong (table hit): 0` after any change.
- Winter keys are **strings**; they must NOT be added to `INT_KEYSPACES`.
- Winter coordinates are self-guarded (emitted only inside their window), so
  their `WINDOWS` entry is `None`.
