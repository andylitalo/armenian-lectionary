# Remaining Unpredictable Days — Armenian Lectionary Engine

**Generated:** 2026-06 · branch `winter-hinge-scheduler` · engine commit after the
post-Nativity saint-identity replay (`PnSaint`).

> **Update (Easter-band `EB` chunk):** the Easter core has since been given a
> `pn_len`-banded sub-key (`EB = "{band}:{offset}"`, precedence just above plain
> `E`; bin width 4 days). This delivered **Priority 1 (Class A / bucket-1 Easter
> core)**: runtime exact-match rose **9 088 → 9 199 (+111 days), 95.7 % → 96.9 %**,
> estimate **407 → 296**, still **0 wrong**. The pre-Lent saint days (`E=−64/−62/
> −61`), Easter Sunday (`E=0`) and the `E=−70…−72` boundary now ship for every
> normal year; only the irreducible **single-sample extreme-Easter outliers**
> (2008 Mar 23, 2011 Apr 24) remain estimate there — they cannot be cross-validated
> with one observation.
>
> **Update (Advent-band `HEB`/`HEpB` chunk):** the Heesnak offset cycles got the same
> treatment — an Advent-length-banded sub-key (`HEB`/`HEpB = "{adv_len}:{offset}"`,
> placed at low precedence just above `HE`/`HEp` so the winter grid still wins).
> `adv_len = Jan 6 − Heesnak` is the clean (no-leap-span) Advent-length scalar. This
> zeroed the Heesnak-Sunday block (`HE=0` and the other Advent Sundays) and trimmed
> the Fast-of-Nativity tail continua (`HEp`): runtime **9 199 → 9 252 (+53 days),
> 96.9 % → 97.4 %**, estimate **296 → 243**, still **0 wrong**.
>
> **Update (post-Nativity Wed/Fri continua `PnFerF` chunk):** the post-Nativity
> Wed/Fri fast (Hebrews/Luke) is a continua that marches per *fast-day*, but was
> keyed by Sunday count (`PnFer`), splitting one continua reading across years. Fix:
> a forward Wed/Fri index `PnFerF = "{count of Wed/Fri since Jan 14}:{weekday}"`
> (the coordinate `AdvFer` already uses). Runtime **9 252 → 9 271 (+19 days),
> 97.4 % → 97.6 %**, estimate **243 → 224**, still **0 wrong**.
>
> **Note (taxonomy correction):** the `AS=−9…−14` block this report called "the
> single largest deep continua" is in fact the **summer saint-weekdays** (Athenogenes,
> Andrew, Triphon, Twelve Prophets…) caught by the higher-precedence `AS` keyspace —
> a *saint* zone, not a continua. It and the autumn `ExSatL` block both suffer a
> one-slot **saint phase-shift / merge** that NO forward/backward/length key resolves
> (verified: forward & backward saint-ordinal and span-classed variants all recover 0);
> they need the deferred **bidirectional saint merge-folding** engine. The clean
> banding/continua fruit (`EB`, `HEB`/`HEpB`, `PnFerF`) is now harvested; the
> remaining ~95 hinge-saint days are the genuine deep tail.
>
> The numbers in the body below describe the *pre-`EB`* state and are retained for
> the taxonomy; the live counts are in these banners.

## Executive summary

Over the full cross-year ground-truth cache (**9 495 days, civil years 2001–2026**),
the engine now exact-matches **9 088 days (95.7 %)** with **0 wrong table hits**.
The remaining **407 days (4.3 %)** are returned as `algorithmic-estimate`: the
engine emits the correct season/feast label but withholds the scripture readings
because no liturgical coordinate for that day is cross-year consistent.

**This is by design (strict shipping).** A reading is shipped only if *every*
supporting year that lands on the same liturgical coordinate agrees on it. A
single disagreeing year therefore drops the whole coordinate to estimate rather
than risk shipping a wrong reading. Consequently most "unpredictable" days are
not modelling failures but **genuine calendar collisions**, and — as shown below
— they **cluster sharply by year type** (date of Easter, leap status).

### The headline finding

The number of estimate days per civil year is **strongly predicted by how
extreme that year's Easter is**:

| Easter window | Example years | Estimate days |
|---|---|---|
| **Earliest** (Mar 23, leap) | 2008 | **31** (worst) |
| **Latest** (Apr 24 = Genocide-day collision) | 2011 | **25** |
| Very early (Mar 27) | 2005, 2016 | 19–20 |
| Late (Apr 21) | 2019 | 21 |
| Early-mid (Mar 31 – Apr 12) | 2002, 2007, 2010, 2018, 2020–21 | 16–18 |
| **Mid-late, "central"** (Apr 15–20) | 2003, 2006, 2014, 2017, 2025 | **8–9** (best) |

Mean = 15.7 estimate days/year. The five "central-Easter" years (Apr 15–20) have
roughly **one-third** the estimate count of the two extreme years. The mechanism:
the lectionary is woven between a *solar* frame (fixed civil feasts, Theophany,
the Assumption/Exaltation/Heesnak "closest-Sunday" anchors) and a *paschal* frame
(everything Easter-anchored). When Easter is extreme, the movable frame stretches
or compresses against the solar frame, and the saints / fasts laid in the gap
land on coordinates that occur in *no other year* — so they cannot be
cross-validated.

---

## Method

For every cached day the runtime flags `algorithmic-estimate`, this report
records its dominant liturgical coordinate (the highest-precedence in-window
keyspace key), then re-derives that coordinate's build bucket across all years to
measure **how near-unanimous it was** and **which years disagreed**. Year type =
(date of Gregorian Easter for that civil year, leap status). Reproduce with:

```bash
python dev/estimate_report.py            # per-day JSON: zone / class / coord / year-type
python dev/slot_model.py PnSaint         # the post-Nativity saint buckets specifically
python dev/compare_app.py                # the 407 total, by month
```

Month distribution of the 407 estimate days:

```
Jan 108   Feb 100   Mar  6   Apr 46   Jul 39   Aug 54   Sep 7   Nov 47
```

---

## Failure taxonomy (4 classes)

Every estimate day falls into one of four mechanisms. The first two account for
**61 %** and are *near-recoverable*; the last two are deep.

| Class | Days | Recoverability | Mechanism |
|---|---:|---|---|
| **A — Single-outlier poison** | **152** | High (needs outlier-aware / composite keying) | A coordinate is unanimous in all-but-1–2 years; one anomaly year drops it for *all* years. |
| **C — Year-type-banded split** | **102** | Medium (needs finer length/Easter-band classing) | The reading genuinely differs, but each variant correlates with a year-type band; more sub-keys would separate them. |
| **B — Lectio-continua / deep drift** | **98** | Low (needs a continua position model) | A continuous daily Epistle/Gospel march whose index depends on how many fast-days preceded it; no offset key is stable. |
| **D — Embedded irregular feast** | **55** | Out of scope under exact-match | Floating fixed-date feasts whose proper readings entangle with the movable slot they land on. |

### Class A — Single-outlier poison (152 days) — *the biggest and most fixable block*

A liturgical coordinate that is **byte-identical in 24–25 of 26 years** is dropped
to estimate because one or two outlier years carry different readings. The outlier
is almost always an extreme-Easter year. Concentrated in: Easter core (76), Summer
(35), Post-Exaltation→Advent (21), After Nativity (20).

**Worst offenders (the years that poison the most near-unanimous coordinates):**

| Outlier year | Year type | Near-unanimous coords it drops |
|---|---|---:|
| **2008** | Mar 23, **leap** (earliest possible Easter) | 7 |
| **2011** | Apr 24 (latest; collides with Apr 24 Genocide Remembrance) | 6 |
| 2004 | Apr 11, leap | 5 |
| 2005 | Mar 27 | 5 |
| 2016 | Mar 27, leap | 3 |

Canonical examples (modal = how many years agree):

- **`E=0` — Easter Sunday itself**: 25/26 agree on
  `[John 20.1-18, Acts 1.1-8, Mark 16.2-8, John 19.38-42]`; **2011** alone
  substitutes `Luke 23.50-56` for `John 20.1-18`. The single Apr-24-2011 collision
  (Easter falling on Genocide Remembrance Day) drops Easter for all 26 years.
- **`E=-64` — Saint Sargis the Warrior** (the pre-Lenten Saturday): 25/26 agree;
  only **2008** (Mar 23 leap) differs, because the earliest-possible Easter shoves
  Sargis into a different pre-Lent configuration.
- **`PnSaint=fathers_saints_athanasius`** (Athanasius & Cyril, the pinned
  Saturday): 17/19 agree; **2015 & 2026** instead commemorate the *150 Fathers of
  the Council* on the same Saturday — not separable by calendar, so the whole id
  drops. Likewise `PnSaint=gregory_of_theologian` (11/13; **2004 & 2009** carry
  *Sahak the Parthian* on that Saturday) and `PnSaint=eugenios_makarios` (13/15;
  **2004** splits off *Eugenia* and **2019** inserts *Triphon*).
- **`ExSatL=69:9:{Mon,Tue,Thu}`** (post-Exaltation saint grid, November): 6/7
  agree; the lone outlier is **2004** (Apr 11 leap) — 21 November days lost to one
  year.

> **Interpretation:** these are *not* one-off random misses. Each is a coordinate
> that is **consistently correct on every normal year and wrong only in a specific
> extreme-Easter (or specific-collision) year**. The year type is the culprit, not
> the rule. They become recoverable with **composite/outlier-aware keys** (ship the
> 24–25-year consensus, give the 1–2 anomaly years their own coordinate).

### Class C — Year-type-banded / length-class split (102 days)

Here the reading **genuinely differs across years**, but the variants line up with
a year-type *band* — usually a window-length class or an Easter-date band — so the
disagreement is structured, not random. Concentrated in: Easter core (49), Advent
(26), After Nativity (15), Assumption (7), Summer (5).

- **`E=-72`, `E=-71`** (the pre-Lent / eve-of-Catechumens-Fast boundary):
  5–10 distinct reading-sets, each tied to where Easter falls. The boundary
  between the post-Nativity count and the Lenten count moves with Easter, so the
  same offset spans different liturgical roles in different Easter bands.
- **`E=-70` — Eve of the Fast of the Catechumens**: 20/25; the 5 outliers are
  *all* **early Easters** (Mar 23 – Mar 31). In a short paschal run-up the eve
  coincides with a numbered Sunday and steals its readings.
- **`TrSatL=35:*` and `TrSatL=28:*`** (summer saint grid, length-classed): the
  Transfiguration→Assumption gap length is itself an Easter-band proxy; the
  remaining splits are sub-bands not yet separated (e.g. the length-35 class still
  mixes the Mar-27 years).
- **`HE=0` — Heesnak (1st Advent Sunday)**: 19/23; outliers at both early and late
  Easters — the Advent tail's overlap with the *next* spring's paschal cycle.

> **Interpretation:** mixed. Some are recoverable by **adding a finer length/Easter
> sub-class** (as length-classed keys already did for December → 0); others are the
> genuine boundary cells where two counting systems meet and only 2–3 years share
> any given configuration (low support, never cross-validatable with only 26 years
> of data).

### Class B — Lectio-continua / deep drift (98 days)

The hardest block. These days sit on a **continuous daily reading march**
(Hebrews→Luke in the Fast of Nativity; a sequential Epistle/Gospel in the Fast of
the Assumption and the post-Nativity Wed/Fri ferial) whose position depends on
*how many fast-days have elapsed*, which shifts with window length. No
day-offset key is stable. Concentrated in: Assumption (46), Advent (19), After
Nativity (19), Easter/Summer (14).

- **`AS=-9` … `AS=-14` — the Fast of the Assumption run-up** (early–mid August):
  the single largest deep block, 46 days. Modal support is only ~8/26 with 5–7
  distinct reading-sets per offset — the fast's daily continua marches at a
  position set by the Assumption "closest Sunday" vs the solar date, so each
  offset carries a different reading almost every year.
- **`HEp=54` … `HEp=59` — the Fast of Nativity tail** (late Dec → Jan 5): pure
  Hebrews/Luke continua; modal 4–10/26, 6–7 distinct sets. Documented in
  `dev/WINTER_HINGE_PROGRESS.md` idea #1.
- **`PnFerB=0:Wed`, `1:Fri`, …** (post-Nativity Wed/Fri ferial, backward index):
  the same continua viewed from the Lenten end; still drifts.

> **Interpretation:** requires the un-built **continua-position engine** — compute
> the running fast-day index from the window length and key on *that* rather than a
> raw offset. Until then these stay estimate (correctly: shipping any offset
> consensus here would be wrong in most years).

### Class D — Embedded irregular feasts (55 days)

Floating fixed-date feasts whose proper readings **co-celebrate with** (concatenate
onto) whatever movable ferial/Sunday slot they land on, producing a different
reading-set every year.

| Date | Feast | Days est. | Why |
|---|---|---:|---|
| **02-13** | Eve of the Presentation of the Lord | 26 (all) | Eve-suffix + variable landing slot; intentionally excluded from the composite engine. |
| **04-07** | Annunciation to the Theotokos | 26 (all) | Falls inside Lent/Holy Week, which reorders its readings irregularly. |
| **11-21** | Presentation of the Theotokos to the Temple | 3 | Usually ships as a validated composite; estimate only when its landing slot is itself unresolved. |

> **Interpretation:** out of scope under the current exact-full-match contract.
> Recoverable only if the project ever ships **feast-proper readings alone**
> (the invariant prefix) for these, accepting a partial match.

---

## Year-type clustering — the cross-cutting conclusion

Re-reading the four classes through the year-type lens gives a single, consistent
story:

1. **Extreme-early Easter (Mar 23–27)** is the most damaging configuration.
   2008 (Mar 23, leap), 2005 (Mar 27) and 2016 (Mar 27, leap) dominate both the
   single-outlier poisons (Class A) and the early-Easter eve/boundary splits
   (`E=-70`, `E=-72`). The compressed paschal run-up forces saint merges/drops and
   collides the eve-of-Fast Sunday with numbered Sundays.

2. **Latest Easter (Apr 24, 2011)** is a *specific* collision, not a band: Easter
   coincides with the Apr 24 Genocide Remembrance commemoration, perturbing
   `E=0`, `E=104`, `E=111` and the late-April ferials.

3. **Leap years are over-represented among the outliers** (2008, 2004, 2016 all
   leap) — but this is a *correlation with extreme Easters*, not an independent
   leap effect. The Feb-29 shift only matters where it co-occurs with an early
   Easter; a leap year with a central Easter (e.g. 2012, Apr 8 — 10 estimate days)
   is unremarkable.

4. **Central Easters (Apr 15–20)** are almost fully predicted. The residual
   estimates in those years are Class D (the embedded feasts, which are
   Easter-independent) and the deep Class B continua — i.e. the year type is *not*
   the problem there.

### Are these one-offs or consistent failures?

A crucial distinction for prioritisation:

- **Class A (152 days) = consistent-rule, year-type-specific failures.** The rule
  is *right* and the coordinate *is* cross-year stable — it is dropped only because
  one extreme-Easter year disagrees. These are "one-off **years** poisoning an
  otherwise-perfect computation," precisely the case the report was asked to flag.
  Fixing the keying to isolate the outlier year would recover essentially all 152
  with zero risk to the 0-wrong guarantee.

- **Class C (102 days) = partially consistent.** Each variant is internally
  consistent within its year-type band; the failure is *insufficient sub-keying*,
  not an anomaly. Recoverable where ≥2 years share a band.

- **Class B (98) and Class D (55) = genuinely not a fixed coordinate.** Not
  one-offs and not year-type artefacts — they need a different *model* (continua
  index; feast-proper partial match), not better keys.

---

## Recoverability ledger & recommended next steps

| Priority | Target | Est. days | Approach |
|---|---|---:|---|
| 1 | **Class A outlier isolation** | ~152 | Composite keys that ship the 24–25-year consensus and route the 1–2 anomaly years (2008, 2011, 2004, 2005, 2016) to their own coordinate. Highest leverage, near-zero risk. |
| 2 | **Post-Nativity merge/split** (`eugenios`, the `andrew`/`adrian` middle, `Sahak`/`150-Fathers` variants) | ~30 | Finish Stage 2/3 of the saint-replay: bidirectional merge-folding so split years (2004, 2019) and variant-Saturday years stop poisoning their ids. |
| 3 | **Class C finer length/Easter sub-classing** | ~60 of 102 | Extend the length-classed-key idea (already zeroed December) to the summer `TrSatL` bands and the `E=-70…-72` boundary. |
| 4 | **Class B continua engine** | ~98 | Model the Fast-of-Assumption and Fast-of-Nativity daily index directly (idea #1 in the progress doc). The single largest deep block (`AS=-9…-14`, 46 days). |
| — | Class D embedded feasts | 55 | Out of scope unless partial (feast-proper) matches are accepted. |

**Guardrail unchanged:** every step must keep `wrong (table hit): 0`. Because the
engine ships only cross-year-validated coordinates, any imperfect new rule can
only lower coverage, never ship a wrong reading.
