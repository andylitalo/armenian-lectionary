# Blank-day sourcing dossier (2001–2026)

> Companion to `reports/lectionary_disagreements.md`. Records, for every day the engine
> currently ships **blank** (empty `ReadingsList` while the GT cache carries readings —
> `dev/residue_classifier.py:45-47`), the target readings and where they come from in the
> Tōnats'oyts, so the engine fix (Phase 2) has a complete, checkable target list.
>
> **Current residue (post-merge):** 9473 MATCH · 0 WRONG · 5 MISS · **17 BLANK** (9495 days).
> Reproduce: `venv/bin/python dev/residue_classifier.py`.
>
> **Headline:** all 17 blanks are already-digitized composites/positions — **none require
> manuscript transcription.** They fall in two families, resolved by engine coverage:
> **A** = Feb-13 Presentation-eve composites (9); **B** = extreme-Easter movable Sundays /
> fast days (8). Zero Second-Volume floating saints (C) and zero Assumption continua (D).
>
> Easter dates/offsets from `lectionary.calculate_gregorian_easter`; taregir from
> `dev/paschal_index.taregir_for`. Offset = civil date − Gregorian Easter (days).

## The fixed Presentation-eve block

Feb 14 is the Presentation of the Lord; its **eve** (Feb 13) appends a fixed 6-reading tail
onto whatever base proper falls that day. Source: Tōnats'oyts **First Volume p.464/467**
(rubric pp.486-488). The block, in order:

```
Leviticus 12.6-8 · Proverbs 8.22-34 · Ezekiel 44.1-2 · Malach 3.1-4 ·
St. Paul's Epistle to the Galatians 3.24-29 · Luke 2.22-40
```

The engine has a dedicated `PrLE` Easter-offset keyspace for this (`lectionary.py:158-162`,
emitted `:835`), which ships **validated** for offsets seen ≥2× in the cache. The 9 blanks
below are each a **single-sample Easter offset** (every offset distinct → nothing to
cross-validate against), so `PrLE` has no entry and the day abstains.

## Category A — Feb-13 Presentation-eve composites (9)

Each target = **[base proper] ++ [eve block]**. "Base source" notes where the non-eve head
comes from; all are already digitized.

| Date | Taregir / Easter / offset | Feast | Base proper (verbatim) | Eve tail | Base source |
|------|---------------------------|-------|------------------------|----------|-------------|
| 2001-02-13 | Լ / Apr 15 / −61 | Sukiasian Martyrs | Proverbs 22.1-12 · Isaiah 56.6-7 · Hebrews 11.32-40 · Luke 12.4-9 | full 6 | Pre-Lent cohort, First Vol pp.464-465 (`_prelent_cohort`) |
| 2005-02-13 | Ռ / Mar 27 / −42 | 2nd Sun. of Great Lent (Expulsion) | Luke 4.42-5.11 · Isaiah 33.2-22 · Romans 12.1-13.10 · Matthew 5.17-48 | full 6 | Movable ordo (Sunday of Expulsion) |
| 2007-02-13 | Ե / Apr 8 / −54 | Ghevond the Priest & Companions | Wisdom 5.15-22 · Isaiah 35.1-2 · Isaiah 61.6-7 · 1 Peter 1.3-9 · Luke 12.4-10 | **Lev 12.6-8 only** ⚠ | Pre-Lent cohort, First Vol pp.464-465 |
| 2008-02-13 | Ո / Mar 23 / −39 | Tenth day of Great Lent | Exodus 2.11-22 · Joel 2.1-11 · Micah 4.1-7 | full 6 | Movable ordo (Lenten weekday) |
| 2011-02-13 | Յ / Apr 24 / −70 | 5th Sun. after Nativity + Eve of Fast of Catechumens | Isaiah 61.10-62.9 · 2 Timothy 2.15-26 · John 6.15-21 | full 6 | Movable ordo (Nth Sun. after Nativity) |
| 2016-02-13 | Ռ / Mar 27 / −43 | 6th day of Great Lent + St. Theodore the General | Wisdom 8.19-9.5 · Isaiah 62.6-9 · Romans 8.28-39 · Matthew 10.16-22 | full 6 | Saint proper (Theodore) |
| 2019-02-13 | Չ / Apr 21 / −67 | 3rd day of Fast of the Catechumens | *(none)* | full 6 | Eve block only |
| 2020-02-13 | Հ / Apr 12 / −59 | Voskian Priests | Proverbs 24.1-12 · Jeremiah 30.18-22 · 2 Timothy 3.10-12 · Matthew 5.1-12 | full 6 | Pre-Lent cohort, First Vol pp.464-465 |
| 2022-02-13 | Յ / Apr 17 / −63 | 5th Sun. after Nativity | Isaiah 63.7-18 · 2 Timothy 3.1-12 · John 6.22-38 | full 6 | Movable ordo (Nth Sun. after Nativity) |

**⚠ Wrinkle (2007-02-13):** GT appends only `Leviticus 12.6-8`, not the full 6-reading
block. So Fix A cannot blindly append 6; it must reproduce the truncated tail for 2007, or
that day ships as a completeness-superset (GT ⊆ engine) `generative-composite` MISS rather
than an exact match. All other 8 carry the full block.

**Resolution:** all base propers and the eve block are digitized; each is single-sample only
at the *civil* coordinate. Fix A composes them deterministically (Phase 2).

## Category B — extreme-Easter movable Sundays & fast days (8)

Position-determined movable-ordo readings ("Nth Sunday after Transfiguration/Nativity",
fast-day-in-window). Blank only because 2008 (earliest Easter, Mar 23) and 2011/2022 (late
Easter) put these positions on **single-sample civil coordinates**. The readings are a
function of **Easter offset**, so they cross-validate by *position*, not civil date.

| Date | Easter / offset | Feast | Target readings (verbatim) |
|------|-----------------|-------|----------------------------|
| 2008-07-20 | Mar 23 / +119 | 4th Sun. after Transfiguration | Luke 4.14-30 · Isaiah 54.1-13 · 1 Timothy 1.1-11 · John 2.1-11 |
| 2008-07-27 | Mar 23 / +126 | 5th Sun. after Transfiguration | Isaiah 58.13-59.7 · 1 Timothy 4.12-5.10 · John 3.13-21 |
| 2008-08-03 | Mar 23 / +133 | 6th Sun. after Transfiguration | Isaiah 62.1-11 · 2 Timothy 2.15-19 · John 6.39-47 |
| 2011-02-04 | Apr 24 / −79 | Fast day | 1 Corinthians 5.9-6.10 · Matthew 18.23-35 |
| 2011-02-06 | Apr 24 / −77 | 4th Sun. after Nativity | Isaiah 3.16-4.1 · 1 Corinthians 1.25-30 · Matthew 18.10-14 |
| 2011-02-09 | Apr 24 / −74 | Fast day | 1 Corinthians 7.25-35 · Matthew 19.13-26 |
| 2011-02-11 | Apr 24 / **−72** | Fast day | 1 Corinthians 11.1-16 · Mark 1.35-45 |
| 2022-02-04 | Apr 17 / **−72** | Fast day | 1 Corinthians 11.1-16 · Mark 1.35-45 |

**Empirical proof of the offset-invariance hypothesis:** 2011-02-11 and 2022-02-04 are both
Easter offset **−72** and carry **byte-identical** readings. So these movable positions are
offset-keyable and cross-validatable even though each civil date is single-sample. **Fix B**
introduces the offset/position key (Phase 2); where an offset is genuinely single-sample it
ships labeled best-guess (never WRONG).

## Not present (contingency only)

- **C — Second-Volume floating saints:** 0 current. Would source from per-taregir SV cycles
  (`dev/second_volume_cycles.json`); only plate absent from *both* OCR runs is **page 564**
  (cycle Դ, Julian Easter 03-25).
- **D — Assumption continua:** 0 current. Would need First-Volume summer pages **≈ pp.489–531**.

## Resolution map

**Engine state: BLANK 17 → 3, WRONG 0, MATCH +12 (9473 → 9485), 55 tests green.**

| Blank | Fix | Status |
|-------|-----|--------|
| 2005/2008/2016/2019/2020/2022 Feb-13 | **Fix A** — Presentation-eve composite | ✅ MATCH (shipped) |
| 2001-02-13 | **Fix A** (cohort base) | ⚠ best-guess MISS (source versification `Luke 12.4-8` vs cache `12.4-9`) |
| 2007-02-13 | **Fix A** | ⚠ best-guess MISS (GT eve tail truncated to `Lev 12.6-8`; engine ships superset) |
| 2011-02-04/06/09/11, 2022-02-04 | **`_first_volume_continua`** (winter arc, source-derived best-guess) | ✅ MATCH (shipped) |
| 2011-02-13 | **`_first_volume_continua`** base + Fix A eve block | ✅ MATCH (shipped) |
| 2008-07-20/27, 08-03 | summer after-Transfiguration arc | ⛔ BLANK — deferred to next source-modeling pass |

---

# Fix B — the 9 movable blanks are the First-Volume lectio-continua

**Status: all 9 source-confirmed; 6 wired (winter arc), 3 deferred (summer arc).**

**Finding.** Fix B as originally planned (cross-validate by position from the cache) is
**not achievable** — the movable readings are a continuous *lectio-continua* whose
alignment is not a function of any single coordinate (Easter offset, forward index, and
Exaltation offset all tested non-invariant). This is a **data-coverage** problem, not a
rubric one (`reports/residual_estimate_tail.md:317`): the readings exist in the
ground-truth cache but the strict learner will not emit a single-sample extreme-Easter
coordinate. The independent source is the First Volume (below); with it confirmed, the
winter arc is now wired as source-derived best-guess (`_first_volume_continua`), and the
summer arc awaits a fuller model.

## B-feasibility findings (groundwork for the general continua model — next pass)

Tested against the cache to find a position key that makes the continua invariant:

- **Winter Sundays (after Theophany octave):** **INVARIANT by forward index** (1st…4th).
  ✅ derivable.
- **Winter Wed/Fri fasts:** **INVARIANT by their own weekday-index** *only away from the
  Aṙajawor*; near it the anchor flips — 2011-02-04 and 2022-02-04 are both "Fri#4" yet read
  different continua points (1Cor 5 vs 1Cor 11), because 2022's shorter winter pushes its
  last Friday further along. So the fast continua needs a **dual anchor** (forward from the
  octave *and* backward from the Aṙajawor), not a single index.
- **Summer Sundays (after Transfiguration octave):** **NOT invariant** by naive index — the
  2008 arc borrows the winter Timothy continua via the reverse of the line-75 bridge, and
  the alignment depends on the taregir-determined interval length.

**Interim wiring (shipped):** because the winter extreme positions are single-sample in the
cache, they're keyed by **Easter offset** (which fixes position in the fixed 70-day pre-Lent
interval) with **source-confirmed** readings, guarded to *after the Nativity octave* (offset
−70 = Jan 13 in earliest-Easter years is the octave, not the Aṙajawor). Best-guess Source
`first-volume-continua`, so the 0-wrong contract is untouched.

**A correct general B still needs, in a later pass:** (1) the dual-anchor fast model;
(2) the winter↔summer bridge indexing worked out both directions (line 75 forward, and the
2008 reverse borrow); (3) the taregir interval-length rule that both rubrics invoke
("look in the year-letter for the length"); ideally driven off a clean transcription of the
full continua laydown rather than per-offset constants.

**The source exists and is named by the Tōnats'oyts itself.** The Second-Volume typikon
repeatedly defers movable readings to the **First Volume** ("see the others *in order in
the First Volume*" — translated.md lines 1664/1831/1849/2238/2496/2539/3119; for
Transfiguration explicitly, line 2238: "Look in the First Volume up to Friday of the third
week"). The **First-Volume movable ordo** (pp.453–556) lays these out as a numbered
continua — "First Sunday / First Friday / Second Sunday / Second Wednesday …" after
Theophany — and **bridges winter↔summer** with rubrics like line 75: *"If here a Fourth
Sunday is required, see the second Sunday after Transfiguration."* The readings there are
**byte-identical** to the blanks' GT (e.g. translated.md line 87 "Third Sunday … Isaiah
62:1-11, 2 Timothy 2:15-19, John 6:39-47" = 2008-08-03 exactly).

**Per-blank map to the First-Volume continua** (position → source page → transcription state):

Two segments feed the continua. The **winter segment** (after-Theophany, pp.457–460)
carries the First/Second/Third Sunday + Wed/Fri, reading `1–2 Timothy` + `John`. When a
long (late-Easter) winter needs a **Fourth Sunday onward**, the source does *not* extend
the winter pages (pp.461–481 are fixed feasts → Presentation Feb 14 → Fast of Catechumens →
Lent, with no continua readings until Jonah on the Friday); instead the **line-75 bridge**
routes it to the **after-Transfiguration segment** (summer ordinary time, which reads
`1 Corinthians` + `Matthew`/`Mark`). So the 2011/2022 deep-winter blanks are sourced from
the after-Transfiguration cycle, ≈ the summer First-Volume pages after the Assumption.

| Blank | Feast | Continua position | Readings | Source page | State |
|-------|-------|-------------------|----------|-------------|-------|
| 2008-07-27 | 5th Sun a. Transfig | winter **2nd Sunday** | Isa 58.13-59.7 · 1Tim 4.12-5.10 · John 3.13-21 | 460 | ✅ transcribed (line 83) |
| 2008-08-03 | 6th Sun a. Transfig | winter **3rd Sunday** | Isa 62.1-11 · 2Tim 2.15-19 · John 6.39-47 | 460 | ✅ transcribed (line 87) |
| 2008-07-20 | 4th Sun a. Transfig | winter **1st Sunday** | Luke 4.14-30 · Isa 54.1-13 · 1Tim 1.1-11 · John 2.1-11 | 458–459 | ✅ **source-confirmed** (transcribed 2026-07; byte-matches GT) |
| 2011-02-06 | 4th Sun a. Nativity | "2nd Sunday after Vardavar" (line-75 bridge) | Isa 3.16-4.1 · 1Cor 1.25-30 · Matt 18.10-14 | **517** | ✅ source-confirmed (auto OCR; human transcription pending) |
| 2011-02-04 | Fast day (Fri) | after-Vardavar Wed/Fri | 1Cor 5.9-6.10 · Matt 18.23-35 | **518** | ✅ source-confirmed (auto OCR) |
| 2011-02-09 | Fast day (Wed) | after-Vardavar Wed/Fri | 1Cor 7.25-35 · Matt 19.13-26 | **519** | ✅ source-confirmed (auto OCR) |
| 2011-02-11 | Fast day (Fri) | after-Vardavar Wed/Fri | 1Cor 11.1-16 · Mark 1.35-45 | **519** | ✅ source-confirmed (auto OCR) |
| 2022-02-04 | Fast day (Fri) | after-Vardavar Wed/Fri | 1Cor 11.1-16 · Mark 1.35-45 | **519** | ✅ source-confirmed (auto OCR) |
| 2011-02-13 (base) | Aṙajawor Barekendan (Fast-of-Catechumens eve Sunday) | dedicated eve proper | Isa 61.10-62.9 · 2Tim 2.15-26 · John 6.15-21 | **462** | ✅ source-confirmed |

**ALL 9 Fix-B blanks source-confirmed (2026-07).** No blank remains unlocated.
- **pp.517–519** (auto OCR, treated as source-of-record — clean, verse-numbers match GT
  byte-for-byte; e.g. p.517 "Երկրորդ Կիւրակէ զկնի Վարդավառին" → Եսայ Գ.16–Դ.1 · ա.Կորն
  Ա.25→30 · Մատթ ԺԸ.10→14 = 2011-02-06): the after-Vardavar master continua, 5 blanks.
- **p.458–459** (human-transcribed): winter continua opening, 2008-07-20.
- **p.460** (human run): winter 2nd/3rd Sunday, 2008-07-27 / 08-03.
- **p.462** (human-transcribed): the Aṙajawor Barekendan proper "Իսկ յԱռաջաւորի բարեկենդանի
  կիւրակէին … Եսայ ԿԱ.10→ԿԲ.9 · բ.Տիմ Բ.15→26 · Յովհ Զ.15→21" = 2011-02-13 base exactly.

**Fix A eve-block source corrected:** the Presentation-eve block is the **Feb-14
Տեառնընդառաջ** feast readings on **p.462** (Lev 12.6-8 · Prov 8.22-[3]4 · Ezek 44.1-2 ·
Malachi 3.1-4 · Gal 3.24-29 · Luke 2.22-40), and p.462 also carries the Feb-13
co-celebration rubric ("if it coincides with the Fast of Catechumens … on Feb 13 at Midday
read *the day's Scriptures* … then in the evening the eve service") — i.e. `[base] ++ [eve
block]`, exactly Fix A.

**Transcription worklist (First Volume, raw plates `grabar-ocr/data/pages/NNN.pdf`):**
1. ~~pp.458–459~~ — **DONE** (2026-07): winter continua opening ("First Sunday after
   Theophany": `1 Timothy` + `John`). 2008-07-20's readings confirmed byte-exact vs GT.
2. **The after-Transfiguration Sunday + Wednesday + Friday continua** (summer ordinary
   time, reading `1 Corinthians` chs.1–11 + `Matthew`/`Mark`), which the line-75 bridge
   points to for the extended (4th-Sunday-onward) winter positions. Present summer pages
   (527/528/530/531) are the after-Assumption/pre-Exaltation octave, not this cycle; the
   ordinary "Sunday after Transfiguration" continua is on the untranscribed summer gaps.
   Exact page TBD with the source-holder. Unblocks 2011-02-04/06/09/11 + 2022-02-04.
3. **Winter continua Fourth/Fifth Sunday** (the `2Tim 2.15-26` / `John 6.15-21` extension) —
   for 2011-02-13's base. Likely co-located with (2) via the bridge.

Once transcribed, the follow-up **engine work** (deferred) is a build step that parses the
First-Volume numbered continua + the line-75 winter↔summer bridge and validates the
single-sample days from it — the source-derived pattern
`docs/sources/tonatsooyts-eastertide-gospels.md` documents for the Eastertide rotation.
Until then these blanks stay honest (no speculative readings shipped).
