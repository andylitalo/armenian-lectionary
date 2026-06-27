# Prediction Certainty for Future, Unseen Year-Types

**Generated:** 2026-06 · branch `winter-hinge-scheduler`. Produced by
`dev/certainty_audit.py` over the full ground-truth cache (9 495 days, civil years
2001–2026). Read-only dev tooling; the shipped engine is unchanged.

## The question

The engine is empirically **0-wrong over 2001–2026**: it ships a reading only when
*every* cached year that landed on the same liturgical coordinate agreed (strict
cross-year validation). But that guarantee is measured *inside* the observed data.
For a **future year whose Easter date was never observed** — 2027 has Easter on
**March 28**, a date no cached year hits — can we say, per day, which predictions are
**provably correct** and which **may be wrong or simply unavailable**?

**Yes.** The deciding idea is **interpolation vs. extrapolation** of the target
year's Easter (and its leap-corrected `pn_len`) against the observed cache.

- Observed Easter range, 2001–2026: **Mar 23 (2008, earliest)** → **Apr 24 (2011,
  latest)**.
- 2027: Easter **Mar 28** → `pn_len = 3`, `_easter_band = 0`. **Band 0** is already
  populated by **2005 (Mar 27, pn_len 2)** and **2016 (Mar 27, pn_len 3)**, which
  agreed. 2027 sits *strictly inside* the observed range — it **interpolates**,
  never extrapolates a brand-new year-type.

That is what lets us grade certainty. A reading whose coordinate **does not depend on
Easter** (civil/solar feasts), or a plain Easter-offset reading that is **invariant
across the entire observed Easter span bracketing 2027**, transfers with certainty.
A reading carried by a **band/grid coordinate** that 2027 merely *shares* with
observed years is high-confidence-by-interpolation but not proven. Everything else
(single-sample bands, generative best-guess, withheld estimate) is uncertain.

This **refines** the engine's own `Source` tag rather than replacing it. `Source`
says a coordinate was validated *in the cache*; this analysis says whether that
validation **transfers** to the unseen target year — which depends on *which*
coordinate matched, because keyspaces differ in year-type sensitivity
(`lectionary.py:746 coords_for`, `:913 PRECEDENCE`).

## Certainty tiers

| Tier | Plain meaning | Assigned when |
|---|---|---|
| **GUARANTEED** | 100% correct for 2027 | civil/solar (Easter-independent) coordinate — `C`, `PnOct`, the `validated-composite` feasts (Sep 8/Dec 9), or a solar season-count — **or** a plain `E=offset` reading **unanimous across every observed year** whose Easter span brackets the target (Easter-independent within the observed range → interpolation). |
| **HIGH** | Almost certainly correct (empirically 0-wrong, unproven for the new sample) | reading carried by a **banded** sub-key (`EB`/`HEB`/`HEpB`/`AnnE`) or a **winter/hinge grid** slot with **≥2 agreeing** observed supporters, with 2027 *in-band* (interpolation at the band's granularity). Also: a plain-`E` reading whose observed support does **not** bracket the target (extrapolation) — likely, but no longer provable. |
| **MODERATE** | Plausible, thin | band/grid coordinate with a **single** observed supporter (not cross-validated). |
| **BEST-GUESS** | Unvalidated by construction | `Source ∈ {generative-saint, generative-continua, generative-composite}` — the labeled best-guess tier (the last is the Annunciation collision composite). |
| **NONE** | No prediction | `Source = algorithmic-estimate`; readings withheld. |

A separate **extrapolation** flag marks any Easter-sensitive day whose matched
coordinate's observed support does not bracket the target year — these are demoted
out of GUARANTEED. It is the early-warning signal for year-types the cache cannot
vouch for.

## 2027 result (Easter Mar 28)

```
GUARANTEED   178      (25 civil/solar/composite + 153 plain-E invariance)
HIGH         177      (31 Easter-band EB core + 145 winter/hinge grid + 1 plain-E extrapolation)
MODERATE       0
BEST-GUESS     8
NONE           2
                      extrapolation-flagged: 1
```

**365 of 365 days classified. 355 (97%) are GUARANTEED or HIGH** — provably or
almost-certainly correct. The mechanism is exactly the interpolation argument: 2027's
Easter and band are bracketed by observed years, so nothing relies on a never-seen
year-type. Only **10 days** are below HIGH, and they are precisely the known residual
blocks (no *new* unpredictability appears for 2027):

| Day | Tier | Source | Why — cross-reference |
|---|---|---|---|
| **Apr 7** (Annunciation) | BEST-GUESS | generative-composite | Embedded feast reordered into the movable cycle. Now **computed** from the Tonatsooyts collision rule (pp. 486–488): the fixed Annunciation proper combined with the movable day it lands on (Easter+10 = 11th day of Eastertide in 2027). Rubric-deterministic in order, but the day-portion may be liturgically reduced, so it ships labeled best-guess, not validated. See `docs/sources/tonatsooyts-annunciation-canon.md`. (Was `algorithmic-estimate`/NONE before this rule; `predictability_classification.md` bucket 5.) |
| **Feb 13** (Eve of the Presentation) | NONE | algorithmic-estimate | Embedded-irregular block (no rubric modeled yet). |
| **Nov 21** (Presentation of the Theotokos) | NONE | algorithmic-estimate | Usually a validated composite; estimate only when its **landing slot is itself unresolved**, as in 2027 (`residual_estimate_tail.md` §1 note). |
| **Jul 24 – Aug 2** (5 days: Athanasius/Cyril, Peter/Blaise, Anton, Gregory the Theologian, Vahan/Eugenia) | BEST-GUESS | generative-saint | Summer mid-week floating saints — Transfiguration-anchored, the saint floats off the civil date, so no cross-year key is stable (`residual_estimate_tail.md` §3). Shipped as labeled best-guess from the canonical laydown. |
| **Nov 16, Nov 18** (Archangels; Adrian & Natalia) | BEST-GUESS | generative-saint | Post-Exaltation autumn saint slots under-sampled for 2027's phase; labeled best-guess. |

The single **extrapolation** day is **Feb 15** (Easter-offset −41): the bare offset
reading is unanimous in the cache, but every observed year carrying it had a *later*
Easter, so 2027's very-early Mar 28 falls just below their span. It is correctly
demoted GUARANTEED→**HIGH** and flagged — a genuine (if minor) "outside observed
support" case even within an interpolating year.

### Why GUARANTEED really is 100% for 2027

- **25 civil/solar/composite days** (Theophany Jan 6, the Presentation, the embedded
  Marian feasts Sep 8/Dec 9, the Naming octave Jan 13, solar season-counts) are
  anchored to civil dates or the "Sunday-closest-to" solar rule. The date of Easter
  cannot perturb them, so an unseen Easter is irrelevant.
- **153 plain-`E` days** carry a reading that is **byte-identical across all 26
  observed years** (Easter spanning Mar 23 → Apr 24). 2027's Mar 28 lies inside that
  span, so the value is an **interpolation of an already-flat function** — there is
  nothing for it to vary into. These are the stable backbone of Lent, Holy Week, and
  Eastertide.

The **177 HIGH** days are honestly *not* guaranteed: 31 are Easter-core days whose
reading genuinely shifts in extreme-Easter years (which is *why* the `EB` band-key
exists), so 2027 rests on the 2 band-0 witnesses (2005, 2016); 145 are winter/hinge
grid slots validated across ≥2 years (some, like the Jan 14 Birth of John Forerunner,
backed by 25 years — near-certain). Empirically 0-wrong, but a single new sample
within a 2-year band is not a proof.

## Horizon 2027–2040 — certainty degrades only on extrapolation

Running the same audit forward shows certainty is stable **as long as a future Easter
stays inside the observed Mar 23 – Apr 24 window**, and collapses the moment one steps
outside it:

| Year | Easter | Band | GUARANTEED | HIGH | MODERATE | BEST-GUESS | NONE | Extrap |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2027 | Mar 28 | 0 | 178 | 177 | 0 | 8 | 2 | 1 |
| 2028 | Apr 16 | 5 | 176 | 187 | 0 | 0 | 3 | 0 |
| 2029 | Apr 01 | 1 | 180 | 179 | 0 | 5 | 1 | 0 |
| 2030 | Apr 21 | 6 | 176 | 183 | 0 | 5 | 1 | 1 |
| 2031 | Apr 13 | 4 | 179 | 184 | 0 | 1 | 1 | 1 |
| 2032 | Mar 28 | 1 | 177 | 180 | 0 | 7 | 2 | 1 |
| 2033 | Apr 17 | 5 | 175 | 186 | 0 | 1 | 3 | 0 |
| 2034 | Apr 09 | 3 | 180 | 183 | 0 | 1 | 1 | 0 |
| 2035 | Mar 25 | 0 | 178 | 178 | 0 | 8 | 1 | 2 |
| 2036 | Apr 13 | 5 | 179 | 180 | 0 | 4 | 3 | 0 |
| 2037 | Apr 05 | 2 | 179 | 181 | 0 | 4 | 1 | 0 |
| **2038** | **Apr 25** | **7** | **25** | **322** | **0** | **9** | **9** | **169** |
| 2039 | Apr 10 | 4 | 178 | 184 | 0 | 2 | 1 | 2 |
| 2040 | Apr 01 | 2 | 179 | 179 | 0 | 7 | 1 | 1 |

The Annunciation composite (below) is why every year's BEST-GUESS now includes Apr 7
and NONE is correspondingly lower than the pre-rubric audit.

**2038 (Easter Apr 25) is the worked extrapolation case.** Apr 25 is one day *later*
than the latest observed Easter (Apr 24, 2011), so almost every Easter-anchored
reading loses its bracketing support: GUARANTEED collapses **178 → 25** (only the
Easter-independent civil/solar days survive), 169 days flip to extrapolation (demoted
to HIGH), and withheld NONE days rise to 9. This is the engine telling the truth — it
has never seen a year that late and cannot *prove* the paschal readings transfer,
even though they very likely do. Every other year through 2040 interpolates and looks
like 2027.

## The determination

For 2027, and for any future year whose Easter falls inside the observed Mar 23 –
Apr 24 window:

- **~178 days are provably correct** (GUARANTEED): civil/solar feasts and the
  Easter-invariant paschal backbone.
- **~177 days are almost certainly correct** (HIGH): in-band/grid interpolations,
  empirically 0-wrong but unproven for the new sample.
- **~10 days are uncertain or unavailable**, and they are *exactly* the residual
  blocks the existing reports already document — the embedded **Annunciation (Apr 7)**,
  now a best-guess composite (see below); the **Presentation eve (Feb 13)** and an
  **unresolved Nov 21**, still withheld; and the generative summer/autumn floating
  saints (`predictability_classification.md` buckets 3 & 5; `residual_estimate_tail.md`
  §§1–3). **Nothing new becomes unpredictable in an unseen interpolating year.**

Certainty drops sharply **only** when a future Easter steps outside the observed
window (next occurrence: 2038, Apr 25), and the `extrapolation` flag catches that
case explicitly.

## The Annunciation composite (Apr 7): from NONE to a rubric-derived best-guess

The Annunciation was the single largest residual estimate block. It is **not**
arbitrary: the **Տօնացոյց (pp. 486–488)** prescribes its readings as a deterministic
*collision rule* — the fixed Annunciation proper combined with the movable Lent /
Holy Week / Eastertide day Apr 7 lands on, ordered by that day's rank. The engine now
implements this (`_annunciation_composite`), so Apr 7 ships **`generative-composite`
(best-guess)** instead of `algorithmic-estimate` whenever the validated `AnnE`
keyspace lacks the year's exact Easter offset (single-sample or unseen offsets like
2027's +10). The rule reproduces **16/26** cached Apr 7 days exactly and is a
controlled superset on most of the rest (Eastertide, where the actual celebration
trims to the Gospel cycle); it never ships as validated, so the **0-wrong contract is
untouched** (still 9 364 validated days, 0 wrong). The source text and clause-by-clause
mapping are in `docs/sources/tonatsooyts-annunciation-canon.md`.

## Reproduce

```bash
python dev/certainty_audit.py 2027            # per-day JSON to stdout, summary to stderr
python dev/certainty_audit.py 2027 2040        # the horizon table above
python dev/certainty_audit.py --summary 2027   # summary only
```

`dev/certainty_audit.py` reuses `dev/predictability_audit._occurrences` (the
per-coordinate `{(year, date, reading-signature)}` support map) and the engine's own
`_lookup` / `coords_for`; it touches no ground truth and changes no shipped data.
