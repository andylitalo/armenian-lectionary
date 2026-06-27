# Predictability Classification — Are Any Lectionary Days *Truly* Unpredictable?

**Generated:** 2026-06 · branch `winter-hinge-scheduler` · engine commit after the
post-Nativity saint-identity replay (`PnSaint`). Produced by
`dev/predictability_audit.py` over the full ground-truth cache (9 495 days, civil
years 2001–2026).

This report **refines** `reports/unpredictable_days.md` along a different axis. The
earlier report classified the 407 `algorithmic-estimate` days by *failure
mechanism* (Class A single-outlier / B continua / C year-band / D embedded). The
question here is the one that actually decides whether a day must be hardcoded:

> For each estimate day, is it **truly impossible to predict by any rule** — a
> year-specific editorial judgement call or a source error that could only be
> written as *"the lectionary on mm-dd-yyyy is …"* — or does it just need a **more
> complex, year-type-specific (but not date-specific) rule**?

## Headline answer

**Zero days are truly impossible.** Every one of the 407 estimate days is explained
by a computable mechanism. None is an arbitrary, per-year editorial choice or a
source error that would require a date-keyed override.

| Bucket | Days | Predictable in principle? | What it needs |
|---|---:|---|---|
| **1 — Complex-rule-recoverable** | **183** | **Yes** — a finer/outlier-aware *static* rule | A computable feature separates the variants; this day sits in a ≥2-year variant. |
| **2 — Rule-shaped, single-support** | **22** | **Yes** — but only 1 sample | This day *is* the lone outlier, in an extreme-Easter / collision year; its deviation is a deterministic consequence of a computable condition. |
| **3 — Model-gap** | **147** | **Yes** — a different *model* | Not separable by a static feature; the true coordinate is a running fast-day index (continua) or a saint merge/transfer. |
| **4 — Truly date-bespoke** | **0** | **No** | — (none found) |
| **5 — Embedded irregular feast** | **55** | Partial | Floating fixed-date feasts; out of scope under exact-match. |
| **Total** | **407** | | |

**352 of 407 are predictable in principle** (buckets 1–3); the remaining 55 are the
embedded floating feasts, which are a known, separate out-of-scope category — not
unpredictability. The "must hardcode a specific date" count is **0**.

Reproduce: `python dev/predictability_audit.py` (JSON to stdout, summary to stderr).
Month distribution of the 407 reproduces the engine's exactly:
`Jan 108 · Feb 100 · Mar 6 · Apr 46 · Jul 39 · Aug 54 · Sep 7 · Nov 47`.

---

## Method

The unit of analysis is the **day**, classified by its *dominant in-window
coordinate* (reusing the `estimate_report._classify` precedence walk), so bucket
counts sum to 407 rather than to the count of dropped keyspaces. For each estimate
day the tool:

1. Looks up that coordinate's full `{reading-set → set(years)}` map.
2. If this day's reading-set is shared by **≥2 years** (a consensus variant), it is
   recoverable: either by **outlier-isolation** (one consensus + a stray outlier
   year — ship the consensus, route the outlier) or, where several multi-year
   variants compete, by testing **computable features** for a clean partition.
3. If this day **is** the lone outlier, it attributes the deviation to a mechanism:
   extreme-Easter / civil-collision (→ bucket 2), continua / saint-merge /
   fixed-feast displacement (→ bucket 3), or — only if none apply — flags it as
   truly bespoke (→ bucket 4) and runs a source-error heuristic.

**Zone-gating (the Assumption confound).** In continua/merge zones the Fast-of-
Assumption readings *appear* to band by Easter, but Assumption is solar and
Easter-independent — the correlation is a confound (the real driver is the
Transfiguration→Assumption span, i.e. a running index). The tool therefore refuses
to "separate" a continua-zone coordinate by an Easter-proxy feature and routes it to
the model-gap bucket, keeping the bucket-4 residue honest.

**Computable features tested:** Easter band, leap status, the leap-sensitive
post-Nativity window length (`pn_len = Easter−70 − Jan 14`), the
Transfiguration→Assumption span, and the occurrence's civil date (fixed-feast
collision). The separating feature must leave every variant backed by ≥2 years.

---

## Bucket 1 — Complex-rule-recoverable (183 days)

Recoverable today with a better key, **zero risk** to the 0-wrong guarantee.

| Sub-mechanism | Days | How it recovers |
|---|---:|---|
| **Outlier-isolation** | 105 | The coordinate is a clean consensus in 24–25 years plus a stray outlier; this day is one of the consensus years. Ship the consensus, route the 1–2 anomaly years to their own key. |
| **Static separator — `pn_len`** | 77 | The pre-Lent / eve-of-Catechumens boundary (`E=−70…−72`) splits by the **leap-sensitive post-Nativity window length**, *not* by Easter date. (This is exactly why plain Easter-date fails on the Mar-31 years 2002/2013 vs 2024 — they differ by the Feb-29 leap day in the Jan 14→Easter−70 span.) |
| **Static separator — Easter band** | 1 | A single boundary cell separated cleanly by Easter band. |

Dominant zones: Easter core (`E`, 128), Advent (`HE`, 23), post-Exaltation grid
(`ExSatL`, 18), summer grid (`TrSatL`, 8), post-Nativity saints (`PnSaint`, 6).

> **Verdict:** these are not modelling failures — the rule is *right* and the
> reading *is* cross-year stable. They are dropped only by strict shipping when an
> outlier year shares the coordinate, or because the engine has not yet added the
> finer `pn_len` sub-key. A "needs a more complex rule" case, never date-bespoke.

---

## Bucket 2 — Rule-shaped, single-support (22 days)

The lone outlier *is* this day, but its deviation is the deterministic consequence
of a **computable** calendrical condition that, in 2001–2026, only one year
exhibits. Predictable in principle; shippable only by trusting a single sample or
pinning the condition. Concentrated entirely in the three extreme-Easter years:
**2008 (Mar 23, earliest), 2011 (Apr 24, latest), 2005 (Mar 27)**.

| Date | Coord | Computable condition | Note |
|---|---|---|---|
| 2011-04-24 | `E=0` | Easter = Apr 24 → Genocide-Remembrance collision | `Luke 23.50-56` substituted; canonical. |
| 2008-01-19 | `E=-64` | earliest-possible Easter (Mar 23) | Saint Sargis shoved into a different pre-Lent config. |
| 2008-01-13 | `E=-70` | earliest Easter compresses the run-up | |
| 2008-01-21 | `E=-62` | earliest Easter | |
| 2011-02-12 | `E=-71` | latest Easter | |
| 2008-07-20…08-02 | `TrSun/TrFer/TrSat=*` | earliest Easter stretches the summer span (8 days) | |
| 2011-01-21…02-06 | `PnFerB/PnSat/PnSunB=*` | latest Easter compresses post-Nativity (8 days) | |
| 2005-07-23/30 | `TrSatL=35:*:Sat` | very-early Easter (Mar 27) summer-grid shift (2 days) | |

Per-year tally: **2008 → 11, 2011 → 9, 2005 → 2.** Every entry's condition is
"extreme Easter" — a function of `calculate_gregorian_easter(year)`, hence
computable.

> **Verdict:** not arbitrary and not errors — each is a rule firing in the one year
> the calendar makes it fire. With composite/outlier-aware keys (the report's
> Priority 1) these ship for the extreme years while the 24–25-year consensus ships
> for everyone else. The only obstacle is **cross-validation depth** (1 sample in 26
> years), not predictability.

---

## Bucket 3 — Model-gap (147 days)

Not separable by any *static* feature, because the correct coordinate is a **running
index** or a **transfer/merge**. Predictable with a different model, never a date
hardcode.

| Mechanism family | Days | Zones | Recovers via |
|---|---:|---|---|
| **Continua / merge, multi-variant** | 136 | `AS` (53), `PnFerB` (24), `HEp` (22), `TrSatL` (20), `PnSat*` (7), `TrSat` (7) | Continua-position engine: key on the running fast-day index, not a raw offset. (`WINTER_HINGE_PROGRESS.md` idea #1.) |
| **Singleton continua / saint-merge** | 10 | `PnSaint` etc. | Bidirectional saint merge-folding for split years (2004/2019). |
| **Fixed-feast displacement** | 1 | `E=-61` (2022-02-15) | A saint-transfer rule (see below). |

Dominant blocks: the **Fast of the Assumption** run-up (`AS=−9…−14`, August, 49
days) and the **Fast of the Nativity** tail (`HEp`, late Dec → Jan), exactly the
two daily-continua marches the earlier report flagged as Class B. Their apparent
Easter-banding is the solar/paschal confound; the running fast-day index is the true
key.

### The day that *looked* truly bespoke — and isn't

`dev/predictability_audit.py` initially flagged a single bucket-4 candidate,
**2022-02-15**, "Saints Atom and his soldiers, and Saints Sukiasians the Martyrs."
Investigation shows it is a **deterministic fixed-feast displacement**, not an
editorial whim:

- "Saints Atom and his soldiers" is a *movable* pre-Lent saint that always falls on
  the Monday `E=−62`; the Sukiasian Martyrs follow on Tuesday `E=−61`.
- In 2022, Easter = Apr 17, so `E=−62` = **Feb 14 = the Presentation of Our Lord**
  (a major fixed dominical feast, that year a Monday).
- The Presentation **displaced** Atom from his Monday slot, so Atom transferred
  forward to Feb 15 (`E=−61`) and **merged** with Sukiasians, carrying Atom's proper
  readings (`Wisdom 6.11-20 · Isaiah 18.7-19.7 · 2 Cor 4.10-5.5 · John 16.1-4`).

The condition — a major fixed feast occupying an adjacent movable saint's slot — is
fully computable; the deviation is a transfer/merge, recoverable by a displacement
model. The tool now detects this (`_displaced_by_fixed`) and the truly-bespoke count
is **0**.

> **Verdict:** these need *engineering* (a continua-index engine, saint
> merge-folding, a feast-displacement rule), not date hardcodes. They are the
> deepest block but still rule-governed.

---

## Bucket 5 — Embedded irregular feasts (55 days)

Out of scope under the exact-full-match contract — not unpredictability but a
different problem (feast-proper readings concatenated onto a variable movable slot).

| Coord | Days | Feast |
|---|---:|---|
| `CF=02-13` | 26 | Eve of the Presentation of the Lord |
| `CF=04-07` | 26 | Annunciation to the Theotokos (falls inside Lent/Holy Week) |
| `CF=11-21` | 3 | Presentation of the Theotokos (only when its landing slot is itself unresolved) |

Recoverable only if the project ships **feast-proper readings alone** (the invariant
prefix), accepting a partial match.

---

## The determination

| Category | Days | Truly impossible? | Action |
|---|---:|---|---|
| Needs a finer / outlier-aware **static rule** (bucket 1) | 183 | No | Composite keys + the `pn_len` sub-key. |
| Needs **pin / trust-1-sample** under a computable condition (bucket 2) | 22 | No | Extreme-Easter outlier keys. |
| Needs a **different model** — continua / merge / displacement (bucket 3) | 147 | No | Continua-index engine, saint merge-folding, feast-displacement rule. |
| **Truly date-bespoke** — editorial judgement call or source error (bucket 4) | **0** | **—** | None required. |
| Embedded feasts (bucket 5) | 55 | Out of scope | Feast-proper partial match. |

**No lectionary day in 2001–2026 needs a `mm-dd-yyyy →` hardcode.** The cross-year
cache contains no detectable source errors and no arbitrary per-year choices. Every
remaining estimate is a *computation the engine has not finished building*, ranked
above by how much machinery each needs.

### Caveats

- **`pn_len` separations rest on 26 samples.** Where a bucket-1 variant is backed by
  exactly 2 years, "recoverable" is *low-confidence* until more Easter alignments
  are observed.
- **Bucket 2 = 1 sample each.** Shipping these trusts a single observed year; a
  documented single-sample caveat (or a future Apr-24 Easter) is the only validation.
- **The source-error heuristic finds *candidates*, not verdicts.** It found none
  here, but a positive flag would still need a human source check, not an automatic
  override.
- **Bucket 4 is the residual** of buckets 1–3's claim order (documented in
  `dev/predictability_audit.py`), so its count is reproducible and auditable; today
  it is empty.
