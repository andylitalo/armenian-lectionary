# Residual Estimate Tail — Armenian Lectionary Engine

**Generated:** 2026-06 · branch `winter-hinge-scheduler` · engine after Stage C
(`{Zone}SaintMD` saint-identity × civil-date sub-keys, commit `7dd6278`).

**State (at analysis):** 9329 / 9495 exact (98.25%), **0 wrong**, **166 estimate**
over the 2014–2026 eval window. This report enumerates those 166, classifies *why*
each resists the engine, and ranks what (if anything) to do about each block.

> **UPDATE — all four ranked quick wins implemented (see §9, Resolution log).**
> Engine now at **9346 / 9495 exact (98.43%)**, still **0 wrong**, **149 estimate**.
> The remaining 149 are the genuine ceiling enumerated in §§1–3 and §5-merge; they
> need the generative laydown/continua model or are accepted as estimate.

---

## TL;DR — answering the question directly

> *"Are they all same-civil-date same-identity merges in single-sample
> extreme-Easter years?"*

**No.** Only **~3 days** are true same-date / same-identity merges (the Jan-27
`eugenios_makarios_valerian` Eugenia-vs-Eugenios split). The 166 split into
**eight** distinct mechanisms across **three** super-categories:

| super-category | days | nature | actionable? |
|---|---:|---|---|
| **Embedded irregular** (Annunciation + its eve) | 55 | movable Holy-Week reorder of a fixed feast | hard / mostly no |
| **Single-sample extreme-Easter** (all of 2008 & 2011) | 41 | whole-window unique phase, 1 observation each | no (need more data or a generative model) |
| **Ordinary-year tail** | 70 | a grab-bag, partly fixable | **yes — ~17 recoverable** |

The ordinary-year tail (70) decomposes further:

| block | days | why it drops | fix | est. recovery |
|---|---:|---|---|---:|
| Summer mid-week floating saints | 39 | saint genuinely floats off civil date; no identity emitted | none clean | ~0 |
| Post-Exaltation Nov saints | 13 | solar-anchored, but the Tue/Thu slot has no identity + 2004 contaminates the grid | zone+weekday+civil-date saint key | ~8 |
| After-Nativity | 8 | 3 true merge + 5 near-extreme phase | partial | ~0–2 |
| EB pre-Lent boundary | 7 | eve-of-Fast Sunday-number collision (4) + Atom band-offset singletons (3) | Sunday-number sub-key | ~4 |
| HEpB Jan-13 Naming octave | 3 | fixed feast leaking into the continua | claim as fixed/embedded feast | ~3 |

Plus a **data-quality** finding that sits across categories: **2011 Easter Sunday
is the same 14 readings in a different order**, which order-sensitively drops the
global `E=0` bucket (recover **2 days** + robustness by normalising order).

Realistic near-term ceiling from the cheap wins below: **~9346 / 9495 ≈ 98.4%**,
still 0 wrong. The remaining ~150 are genuine: floating saints, single-sample
extremes, and irregular embedded feasts — correctly left as estimate, never wrong.

---

## 1. Embedded irregular — Annunciation + eve (55 days) · *out of scope*

`zone = Embedded feast`, `class = Annunciation/eve (irregular)`. The Annunciation
(Apr 7) and its eve (Apr 6) are fixed-date feasts, but in the Armenian calendar
they are **reordered into Holy Week** whenever they collide with it, and the eve
carries a suffix-form proper. Unlike the other embedded Marian feasts (Sep 8,
Nov 21, Dec 9) — which co-celebrate cleanly and *do* ship via `_embedded_composite`
— Annunciation's readings are reshuffled by the movable cycle, so no single
fixed-date entry is cross-year consistent.

**Recommendation:** leave as estimate. A bespoke Holy-Week-collision resolver for
exactly two civil dates is high-effort, low-yield, and high-risk to the 0-wrong
contract. Document and move on. (These are 55 of the 166 — the single largest
block — but they are *known* and *bounded*.)

---

## 2. Single-sample extreme-Easter — 2008 & 2011 (41 days) · *irreducible*

Every non-embedded estimate day in **2008** (Easter **Mar 23**, the earliest in
the cache) and **2011** (Easter **Apr 24**, the latest) is here. With Easter that
extreme, the *entire* post-Nativity and summer window is uniquely phased: every
coordinate that day produces has **exactly one supporting year**, so the strict
≥2-year filter cannot validate it. This is not a keying weakness — it is a
**sample-size** limit. Examples: the whole 2008 summer saint march
(`TrSaint=cyricus_and_his`, `…=andrew_the_general`, …, plus `TrSun/TrFer/TrSat`),
the 2011 long post-Nativity tail (`PnSat=3:*`, `PnFerB`, `PnSunB`), and the
pre-Lent saints (`E=-64` Sargis, `E=-62` Atom, `E=-61` Sukiasians).

**Options:**
- **(a) More data.** The cache already spans 2001–2026; the source has nothing
  pre-2001. The *next* Mar-23 Easter is 2160; the next Apr-24 is 2011→2095. So
  more history will not arrive. **Dead end.**
- **(b) A generative laydown/continua model** that emits readings from an ordered
  data list *without* cross-year support (the saint sequence and the
  Hebrews/Luke continua are deterministic given the window). This is the only
  path that could ship extreme years — but it trades the airtight "strict-shipping
  ⇒ 0-wrong" guarantee for a model we'd have to trust. **High effort, real risk.**
- **(c) Accept.** These are 2 of 26 years; estimate is the correct, safe answer.

**Recommendation:** accept as estimate. Note that one of these (2011 Easter
Sunday) is *also* recoverable via the data-normalisation fix in §6 — see there.

---

## 3. Summer mid-week floating saints (39 days) · *the real ceiling*

`zone = Summer (Transfiguration→Assumption)`, ordinary years
(2002/2005/2010/2013/2015/2016/2018/2021/2024/2026). These are the Tue/Thu/Mon
minor saints between Transfiguration and the Fast of the Assumption —
`TrSatL=35:3:Tue`, `TrSatL=28:3:Tue`, `TrFerL=28:7`, etc.

**Why they resist everything tried so far.** Transfiguration is **Easter-anchored**
(Easter + 98) while the Assumption is **solar** (Sunday nearest Aug 15), so the
gap's *content* slides relative to the civil calendar by Easter date. Two years
with the *same* length class (e.g. span 35) but Easter Mar-27 vs Mar-31 carry
**different** saints in the same grid slot:

```
TrSatL=35:3:Tue   2002 Vahan      2005 Theodosius   2013 Vahan
                  2016 Theodosius 2024 Vahan          → 3 vs 2 split
```

Probes (this session) confirm **none** of these recover the block:
- **civil-date key** (`m-d`, the Stage C trick): recovers **0** here — the saint
  *floats off* the civil date (Jul-30 Vahan in 2002 vs Jul-26 Theodosius in 2005);
  same date ≠ same saint across years.
- **length-band + civil-date**: *fragments* support below 2 (TrSatL 256→248).
- **extending saint-identity to every weekday + SaintMD**: the senior-anchor
  identity is only well-defined for the pinned/head/tail saints; the mid-week
  minors are exactly the ones the laydown can't place deterministically (that is
  *why* they were left to the grid), so an emitted id would itself be unstable.

This block is the genuine **phase-float core** the winter-mechanism memo has flagged
since the hinge work began. The only mechanism that could crack it is the same
**generative bidirectional laydown** as §2(b) — model the canonical summer saint
sequence and lay it onto each year's free weekdays, emitting readings from data
rather than cross-year voting. Same effort/risk tradeoff.

**Recommendation:** do **not** add more keys here — every additive key tested
either recovers 0 or fragments existing wins. Treat this 39-day block as the
documented accuracy ceiling pending a decision on the generative model.

---

## 4. Post-Exaltation November saints (13 days) · *partially fixable, ~8*

`zone = Post-Exaltation→Advent`, all `ExSatL=69:9:Tue` / `=69:9:Thu` on Nov 15–18.
Unlike summer, this zone is **doubly solar-anchored** (Exaltation = Sunday nearest
Sep 14 → the saints sit on **near-fixed civil dates**). The Tue slot is Adrian in
six years (2005/2010/2011/2016/2021/2022) and the Thu slot is Abraham-&-Khoren —
but **2004 alone** displaces the sequence by one (`ExSaintMD=andrew_the_general:11-15`
on the Monday), so 2004 reads Andrew on the Tuesday. That single disagreeing year
drops the otherwise-unanimous `69:9:Tue`/`Thu` buckets for **all** years.

A standalone **zone + weekday + civil-date** saint-grid key
(`Ex:Tue:11-15` → Adrian, etc.) was probed to ship the six consistent years while
2004 (Andrew) falls into its own bucket — **recovering ~8 of these 13** at 0-wrong
(verified: the probe recovered 8 November days).

**Recommendation — quick win.** Add an `ExSatMD = "{wd}:{m-d}"` key just above the
`ExSatL` grid (mirrors `ExSaintMD`, but for the non-anchor weekday slots). It is
purely additive and self-guarded. Expect ~8 days. *Caveat from §3:* this works for
**Ex** (solar) and likely **As**, but **not Tr** (Easter-anchored, saints float) —
scope it to the autumn/post-Exaltation zones only.

---

## 5. After-Nativity (8 days) · *mostly irreducible, 3 true merges*

The genuine "same civil date, same identity, different readings" case the original
hypothesis described — and it is **small**:

- `PnSaintMD=eugenios_makarios_valerian:01-27` — **2004** reads *Eugenia* (solo),
  **2009/2011** read *Eugenios*. All Jan-27, all band-4-ish, same identity token.
  Neither civil-date nor band nor a composite `a+b` id separates them, because the
  difference is which saint is *actually celebrated* that year (a solo vs a group
  commemoration), which is not a function of any calendar coordinate we can
  compute. **3 days, irreducible.**
- The remaining 5 are 2011/2019 (the two latest Easters) long-window grid
  singletons — same family as §2.

**Recommendation:** accept. The 3-day merge is the textbook case where the readings
are genuinely not date-derivable; composite-id folding would not help (both
variants share every computable coordinate).

---

## 6. Data-quality: 2011 Easter reading **order** (recovers 2 + robustness)

Easter Sunday's 14 readings are **byte-identical across 25 of 26 years**. In
**2011 only**, the *same* readings appear in a **different sequence** (`John
20.1-18` is 1st in every other year but 11th in 2011). Because the engine compares
`ReadingsList` order-sensitively, this one reordered year makes the global `E=0`
bucket inconsistent → it is dropped → and the two extreme years (2008, 2011),
which rely on `E=0`/`EB` for Easter, fall to estimate.

This is almost certainly a **source-page ordering artifact**, not a liturgical
difference. Two clean options:

- **(a) Normalise the cache:** reorder 2011-04-24's `readings` to the 25-year
  canonical sequence in `dev/reference_data/`. Restores a unanimous `E=0`,
  recovers **2008 + 2011 Easter** (2 days), and makes the plain `E=0` bucket
  shippable for every year (robustness).
- **(b) Order-insensitive Easter compare:** riskier (could mask real differences
  elsewhere); not recommended as a blanket change.

**Recommendation — do first, cheapest win.** Option (a). Verify the two readings
multisets are equal before reordering (they are), then rebuild. Document the edit
in the cache provenance so it is not "corrected" back by a future re-fetch.

---

## 7. EB pre-Lent boundary (7 days) · *4 fixable, 3 marginal*

- **Eve-of-Fast-of-Catechumens Sunday (4):** `EB=1:-70` on 2002/2013 carries the
  **First** Sunday-after-Nativity readings; on 2018/2024 the **Second** Sunday's.
  The day is simultaneously a numbered Sunday *and* the eve, and the readings
  follow the **Sunday number**, which `EB`'s band+offset doesn't encode. A
  sub-key adding the Sunday number (`PnSun`/`PnSunB` is already computed) splits
  2002/2013 (N=1) from 2018/2024 (N=2) → both ship. **Recover ~4.**
- **Atom / Sukiasians (3):** `EB=5:-62` (2001) and `EB=5:-61` (2022) have identical
  readings but **different offsets**, so each is a singleton in its own band-offset
  key. Recovering them needs a cross-offset merge of these specific pre-Lent
  national saints — marginal, **leave as estimate** (the audit already flags
  2001-02-12 and 2022-02-04 as the only two truly date-bespoke "editorial variant"
  days; bucket 4).

**Recommendation:** add the eve-of-Fast **Sunday-number** sub-key (clean, ~4 days,
0-wrong). Leave the Atom/Sukiasians offset singletons.

---

## 8. HEpB Jan-13 Naming octave (3 days) · *fixable, 3*

`HEpB=49:56` on 2002/2013/2019 = "Eighth day of Nativity / Feast of Naming" — a
**fixed-date** feast (Jan 13, octave of Theophany) whose readings are
**identical across all three years** (`Luke 2.8-14`, `Luke 2.15-20`,
`Luke 3.1-4.13`, …). It currently leaks into the post-Nativity-fast continua
(`HEp`) and bands inconsistently against other years' Jan-13.

**Recommendation — quick win.** Treat Jan 13 like the other fixed feasts: either
add it to the civil-feast table `C` (if its readings are stable in *all* years) or
to `EMBEDDED_FIXED` + `_embedded_composite` (if it co-celebrates with the continua
in some years). First confirm why the civil pass doesn't already claim it (likely a
co-celebration variance in the 2014–2026 years not present in these three).
**Recover ~3.**

---

## Recommended order of work (cheapest, safest first)

1. **§6 — normalise 2011 Easter reading order** in the cache. +2, + `E=0`
   robustness. ~10 min, 0 risk.
2. **§8 — claim Jan 13 Naming** as a fixed/embedded feast. +3. Low risk.
3. **§7 — eve-of-Fast Sunday-number sub-key.** +4. Low risk, additive.
4. **§4 — `ExSatMD` autumn/post-Ex weekday civil-date key.** +~8. Additive,
   scope to solar zones only (not Tr).
5. **Stop.** §3 (39 summer floats), §2 (41 extreme), §1 (55 embedded), §5-merge (3)
   are the genuine ceiling. They need either the **generative laydown/continua
   model** (one decision, covers both §2 and §3) or are accepted as estimate. None
   should be attacked with more cross-year keys — every such key tested recovers 0
   or fragments an existing win.

Cumulative cheap-win projection: **166 → ~149 estimate**, **~98.4%**, still
**0 wrong**. Beyond that the line is the generative-model decision, which trades
the strict 0-wrong guarantee for coverage of the irreducibly under-sampled days.

---

## 9. Resolution log — quick wins implemented

All four ranked wins shipped; the projection held **exactly** (166 → 149,
98.25% → **98.43%**, **0 wrong** preserved throughout). Each is purely additive
and self-guarded, so the strict cross-year shipping contract is untouched.

| # | win | mechanism | recovered |
|---|---|---|---:|
| §6 | 2011 Easter reading order | reordered `dev/reference_data/2011-04-24.json` to canonical 25-year order (same multiset, `John 20.1-18` restored to position 1) so the `E=0` bucket re-agrees | +2 |
| §8 | Jan 13 Naming octave | new `PnOct="01-13"` constant key in `coords_for`, emitted for every year **except** the eve-of-Fast collision (`e_off == -70`, 2008) so the 25 unanimous octave years ship and 2008 stays estimate | +3 |
| §7 | eve-of-Fast Sunday number | new `PnEveN = str(nsun)` in `_postnat_slot`'s eve branch — bands the eve (Easter-70) by Sunday-after-Nativity count; First (`nsun=1`, +Luke 4.14-30) vs Second (`nsun≥2`) separate, extreme singletons `nsun=0`/`5` (2008/2011) stay estimate | +4 |
| §4 | post-Ex / autumn weekday saint grid | new `AsSatMD`/`ExSatMD = "{wd}:{m-d}"` in `_autumn_slot`/`_postex_slot` — keys the bare saint-weekday slot by (weekday, civil-date) in the **solar-anchored** zones only (not Tr), clustering the consistent years and isolating the 2004 phase-shift | +8 |

Build entry counts: `PnOct` 1, `PnEveN` 4, `AsSatMD` 91, `ExSatMD` 257 (3 dropped).
Ratchets bumped: `COVERAGE_RATCHET` 9329 → 9346, `COVERAGE_PCT_FLOOR` 98.2 → 98.4
(chunk-12 note added). All 12 tests pass.

### The final 149 — the genuine ceiling (unfixable without a generative model)

Estimate-day months after the wins: `{1: 14, 2: 39, 4: 26, 7: 25, 8: 35, 11: 10}`.
These decompose into exactly the blocks §§1–3 + §5-merge flagged as irreducible:

| block (report §) | days | why it cannot be keyed at 0-wrong |
|---|---:|---|
| Embedded irregular — Annunciation (Apr 7) + Presentation eve (Feb 13) (§1) | ~55 | movable Holy-Week reorder of a fixed feast; no deterministic composite rule |
| Single-sample extreme-Easter — all of 2008 & 2011 (§2) | ~41 | whole-window unique phase, **one** observation each; nothing to cross-validate against |
| Summer mid-week floating saints (§3) | ~39 | Transfiguration-anchored zone: the saint genuinely floats off civil date, so no `{wd}:{m-d}` or identity key is cross-year consistent (the As/Ex SatMD trick does **not** transfer to Tr) |
| After-Nativity true merges + Atom/Sukiasians offset singletons (§5, §7) | ~5 | genuine same-date same-identity reading merges + cross-offset national-saint singletons; flagged bucket-4 "editorial variant" by `predictability_audit.py` |

The next move is **not** another cross-year key (every one tested past this point
recovers 0 or fragments an existing win) — it is the **generative laydown/continua
model**, a single design decision that would address §2 and §3 together but trades
the strict 0-wrong guarantee for coverage of the under-sampled days. Out of scope
here; the engine is left at **98.43%, 0 wrong**.

---

## Deferred — pending Տօնացոյց translation (2026 resolution pass)

A separate effort resolved the *low-hanging* ambiguities by reading rules directly
out of the Տօնացոյց (see `docs/sources/`), using only the **partial** `gemini-flash`
translation (pp. ~458–641, with gaps). Four canons were written —
`tonatsooyts-fast-suppression.md`, `tonatsooyts-nativity-octave.md`,
`tonatsooyts-low-sunday-antasdan.md`, `tonatsooyts-eastertide-gospels.md` — three of
which **confirmed** the engine already encodes the rule (no code change) and one
(octave/year-letter) is blocked below.

The ambiguities below were left **out of scope** because the rules needed to resolve
them fall in **untranslated** pages. This list is the standing record so a future
effort (once more of the Տօնացոյց is translated) knows exactly what is unblocked:

| Deferred ambiguity | Maps to block | Blocked on (untranslated) |
|---|---|---|
| **Presentation of the Lord (Feb 14) + eve (Feb 13) collision rules** | §1 (embedded irregular, the Feb-13 half) | The Տօնացոյց names Tearnndaraj as one of only two movable exceptions (p. 467) but its *collision rubric* (the Annunciation-style reorder table) is not in the translated pages — only its date/rank. |
| **Octave→fast encroachment by Dominical letter (Ա→2 days, Ը→1)** | §8 (Jan-13 Naming octave) | Rule is fully stated (p. 464) but applying it needs the **letter of the year**, whose derivation is in the 532-year Paschal tables (pp. ~538–641) — present in OCR, *application* not yet translated. See `tonatsooyts-nativity-octave.md`. |
| **Extreme-Easter phase (2008 Mar 23, 2011 Apr 24)** | §2 (single-sample) | Data-limited, not rule-limited: the Paschal-cycle *tables* are present but their use to phase the whole movable year is untranslated; engine already computes Gregorian Easter, so this stays a data/coverage problem, not a rubric one. |
| **Summer floating-saint identities & ordering (Transfiguration→Assumption)** | §3 (the real ceiling) | The per-saint commemoration order for this zone lives in the untranslated gaps (≈ pp. 489–531). The fast *boundaries* are now justified (`tonatsooyts-fast-suppression.md`), but the saint sequence inside the zone is not. |
| **John the Forerunner (Jan 14) transfer rule** | §5 (after-Nativity) | The transfer-to-next-saint-weekday rule is implemented empirically (`PnJohn`) but no governing rubric was located in the translated pages. |

**Confirmed (no code change, justification added):** the Fast-of-Assumption and
Fast-of-Holy-Cross "no feasts" boundary (the cut at `SUMMER_EVE`/`AUTUMN_EVE`), Low
Sunday's Antasdan reading-block, and the Eastertide four-Gospel continua — all already
shipped validated; the canons supply the primary-source basis (see `docs/README.md`).
