# Second Volume — Leap-Year Saint-Reassignment Rules

> **Source:** Տօնացոյց *Tōnats'oyts'* **Second Volume**, per-Dominical-Letter canons.
> Grabar from the human-corrected OCR run
> (`grabar-ocr/runs/human__proj__tess__gemini-min/`), English from its `gemini-flash`
> translation. Codes resolved against `great_paschal_cycle_index.csv` (year→taregir)
> and `second_volume_index.csv` (taregir→page).
>
> **Status: partially wired (2026-07-03).** The one in-window leap taregir that produces a
> genuine leap/non-leap *divergence* on a shared Gregorian Easter date — **ՍՌ** (Easter
> 03-27, served by leap 2016 and non-leap 2005) — is now encoded as a leap-parity summer
> override in `dev/build_second_volume_cycles.py` (`_LEAP_SUMMER`), shipped through the
> cycle tier's leap-conditional `{ "common": …, "leap": … }` records. The other rules
> govern leap-*only* Easter dates in-window (no non-leap counterpart to diverge from) or
> out-of-window taregirs, so they create no cache divergence to resolve and remain
> reference-only. See "Why not encoded" below for the residual analysis.
>
> **Update (2026-07-04) — source-derived floating-saint marches.** The *non-leap*
> sequence-compression misses that §1 below deferred are now sourced too: see
> "Source-derived floating-saint marches" at the foot of this doc. The Ր and Թ summer
> marches and the solar autumn triplet (Andrew / Adrian / Abraham & Khoren) ship exact
> from the cycle tier, converting the 13 cross-validatable saint/continua misses to
> MATCH (`WRONG 0`, `MISS 25→11`).

## The system (preface §Third, p.555)

> "In this Second Volume, under some letters, we have written brief instructions
> regarding leap years. You must observe those instructions **only in that leap year in
> which those same letters are the calendar letters**, and not in other years… Keep this
> same rule for all letters where such instructions are written."

Leap years carry a **two-letter taregir** — always a **reverse-consecutive pair**
(descending-adjacent letters): `Ը/Թ→ԹԸ`, `Ո/Չ→ՉՈ`, `Ռ/Ս→ՍՌ`, `Ր/Ց→ՑՐ`, etc. The
canon is filed under the **lower** letter of the pair. Each rule says: in that leap
taregir, a saint whose nominal slot straddles the Feb-29 boundary was already kept
under the "first letter," so **skip it here and shift the chain**.

## The rules (as received)

| Canon | Leap taregir | Grabar (verbatim, key clause) | Effect |
|---|---|---|---|
| Թ (p.575) | **ԺԹ** | preface cites: «գիր տարւոյ **ԺԹ** … զԹէոդոսն մի՛ տօնիցես» | Skip Theodosius this Saturday |
| Ի (p.580) | **ԼԻ** | «տարեգիրն **ԼԻ**, աստ զԱստուածաբանն միայն տօնեա, զի միւս հայրապետքն [կան] յառաջին գիրն **Լ**» | Keep only Gregory the Theologian; other patriarchs were under first-letter Լ |
| Ն (p.603) | **ՆՅ** | «գիրք տարւոյն **ՆՅ** … զԱնդրէ զօրավարն և զԱդրիանոսն մի՛ տօնիսցես, զի տօնին … ի յետին գիրն **Յ**, զ[կնի] տասներորդ կիւրակէին» | Skip Andrew & Adrian (they fall on last-letter Յ, after the 10th Sunday); instead Mon=Vahan, Tue=Eugenia, Thu=Eugenios |
| Չ (p.610) | **ՉՈ** | «գիր տարւոյն **ՉՈ** … [չ]որս տօնսն, այսինքն զՄակաբայեցիսն և զայլսն, աստ մի՛ տօնեսցես, զի տօնին … [ի] յետին տարեգիրն **Ո**» | Skip the 4 post-Transfiguration feasts (Maccabees & co.; on last-letter Ո); instead Mon=Eugenia, Sat=Gregory, Tue/Thu=Andrew/Adrian |
| Ս (p.619) | **ՍՌ** | «գիրք տարւոյն **ՍՌ** … զԱնդրէ զօրավարն և զԱդրիանոսն մի՛ տօնիսցես, զի տօնին … ի յետին տարեգիրն **Ռ**, զկնի տասնե[րորդ]» | Skip Andrew & Adrian (last-letter Ռ, after 10th Sunday); instead Mon=Vahan, Tue=Eugenia, Thu=Eugenios |
| Ր (p.627) | **ՐՏ** | «տարեգիրքն **ՐՏ**, զայս չորս տօնս … զԿիպրիանոսն, զԱթանագինէն, զՆախահարսն [եւ 12] առաքեան[ն], [ա]ստ մի՛ տօնիցես … [ի] յետին տարեգիրն **Տ**՝ զկնի Վարդավա[ռի]» | Skip 4 feasts (Cyprian, Athenogenes, the Forefathers, the 12 Apostles); they move to last-letter **Տ**, after Transfiguration. *(Code confirmed from the plate 2026-07-02: earlier OCR `ԸծՏ` was garbled.)* |
| Ք (p.638) | — | «[տ]արեգիրն միայն ի նահանջ տարին լինի, և մինչեւ ի վերջ փետրուարի գործ ածի» | Structural: the Ք directory is leap-only, used until end of February |

Additionally, the Ը canon (page 574) — **now in the human run** (added 2026-07-02;
previously auto-OCR only):

| Ը (p.574) | **ԹԸ** | «Եթէ նահանջ ամի **ԹԸ** … զԱնտոնն մի՛ տօնիցէս, զի տօնեցա[ւ] … [ի] առաջին գիրն **Թ** յետ ծննդեանն» | Skip Anthony (kept 9 days after Nativity); instead Sat=Theodosius, Mon=Cyriacus, Tue=Vahan, Thu=Tryphon |

## Mapping to the 2001–2026 cache

Leap taregirs in-window: **2004=ԹԸ, 2008=ՉՈ, 2012=ԽԼ, 2016=ՍՌ, 2020=ՁՀ, 2024=ՑՐ.**
Rules that therefore *could* fire in-cache: ԹԸ(2004), ՉՈ(2008), ՍՌ(2016).
No rule exists for ԽԼ(2012), ՁՀ(2020), or **ՑՐ(2024)** — the p.627 Ր-canon governs leap
taregir **ՐՏ** (an out-of-window year), not ՑՐ; confirmed from the plate 2026-07-02.

## Why the rest are NOT encoded into the engine

Verified against ground truth and the live engine:

1. **Only ՍՌ needed wiring; the rest are redundant or non-divergent.** The 2016 leap year
   and the 2005 non-leap year share Gregorian Easter **03-27**, so a cycle tier keyed by
   Easter date alone could ship only one saint on the shared civil dates 07-23/07-30 — and
   the drop-guard therefore *withheld both*, leaving 2005 best-effort. The leap-parity split
   (a distinct `"leap"` record for 03-27) fixes this: 2005 ships Peter, 2016 ships
   Athanasius, both exact. The other rules do **not** create such a divergence: ԹԸ(2004),
   ՉՈ(2008), ՑՐ(2024) govern Easter dates that in-window are served by leap years *only*
   (no non-leap counterpart to conflict with), so the common march already serves them and
   encoding a leap variant adds ~0 exact-match. The remaining summer misses in those years
   are **sequence-compression** on tail saints (Eugenios/Eugenia/Andrew/Adrian in long or
   late-Easter windows), affecting non-leap years equally — not a leap rubric; see
   `reports/lectionary_disagreements.md`.
2. ~~One rule appears to contradict GT.~~ **Resolved (2026-07-02).** The p.627 code was
   garbled (`ԸծՏ`); the plate reads **ՐՏ** (feasts move to last-letter **Տ**). The rule
   therefore governs leap taregir **ՐՏ**, not ՑՐ(2024) — so 2024 correctly celebrates
   Cyprian & Athenogenes (Jul 15/16, `validated-table`). No contradiction; nothing to wire.
3. The residual misses (see `reports/unpredictable_days.md`) are **not** on the
   leap-rule days and are mostly in **non-leap** extreme-Easter years (2005, 2011,
   2013, 2015, 2021, 2026) — a generative-tier accuracy tail, not a missing rubric.

**Open items for a human reviewer:**
- (a) ~~confirm the Ր/2024 code~~ **DONE (2026-07-02):** plate reads **ՐՏ**; no ՑՐ/2024
  contradiction.
- (b) ~~confirm the Ը/ԹԸ (2004, Anthony) rule from the human run~~ **DONE:** page 574 is
  now in the human run.
- (c) ~~taregir **Բ** (Julian Easter 03-23) has no parsed Second-Volume cycle~~ **DONE:**
  pages 560–561 are now in the human run and the Բ cycle is built
  (`dev/second_volume_cycles.json`, 35/35 taregirs).
- (d) **NEW:** the Ն-canon leap code (p.603, `region_05_single/line_004`) OCRs as `Ն3`
  (with a digit `3`); intended **ՆՅ** (reverse-consecutive, out-of-window). Confirm from
  the plate.

## Source-derived floating-saint marches (2026-07-04)

Three clusters of the §1 "sequence-compression" residue turned out to be
**cross-validatable** (multiple ground-truth years of one type carry byte-identical
readings), so they are not unpredictable — the correct laydown *repeats*. All three are
now derived from the canon source and shipped through the cycle tier
(`dev/build_second_volume_cycles.py`), validated by the parity-partitioned drop-guard.
Keying note: the cycle tier selects by **Gregorian** Easter, so each canon's march is
stored under the Gregorian Easter md its taregir-years query — *not* the canon's own
Julian label (they differ; e.g. taregir Ր = Julian 04-22 = Gregorian 03-31).

| Cluster | Cycle key (Greg.) | Canon / source | Encoded as | Fixes |
|---|---|---|---|---|
| Summer Ր | `03-31` | Ր, p.627 (winter saints, human) + p.628 (post-Assumption, auto); leap rubric p.627 names Andrew/Adrian | `_SUMMER_R` (full 17-saint march, `start_off=5`) | 08-05 Eugenios · 2002 ≡ 2013 ≡ 2024 |
| Summer Թ | `04-05` | Թ, p.576 (auto): Sat-Athanasius → Mon-Eugenia → **Tue-Andrew → Thu-Adrian**, dropping the Cyricus/Vahan/Triphon/Gregory-Theol middle | `_SUMMER_T` (compressed 13-saint march) | 08-04 Andrew, 08-06 Adrian · 2015 ≡ 2026 |
| Autumn (solar) | `04-04` | Ր p.628 weekday pattern (Mon-Andrew / Tue-Adrian / Thu-Abraham&Khoren); anchor from the **"after the tenth Sunday [of the Cross]"** rubric (Ս p.619, Ն p.603 above) | `_AUTUMN_MARCH`, anchored `Heesnak − {6, 5, 3}` | 11-16 Adrian, 11-18 Abraham & Khoren · 2010 (Ա) ≡ 2021 (Ս) |

The autumn triplet **cross-validates across different taregirs** (2010 Ա, 2021 Ս share
Gregorian Easter 04-04), which is the proof it is solar-anchored, not Easter-keyed: it is
laid on the engine's Heesnak (Advent-eve) Sunday = `sunday_closest_to(y, 11, 18)`, Andrew
on the Monday (HE−6), Adrian Tuesday (HE−5), Abraham & Khoren Thursday (HE−3). Applied to
every cycle; the drop-guard withholds the November copy wherever a type keeps these saints
in August/September (e.g. taregir Ր), so it ships only where the cache agrees.

Separately, the two continua misses (2015/2026-08-05) were a **bucket collision**, not a
saint march: the Fast-of-the-Assumption Wed/Fri continua at span-28 index 7 carries a
genuine per-type variant (`2Tim 2.20-26` for Easter 04-05 vs `1Tim 5.17-6.5` for 04-04)
that the old `(span, idx, wd)` modal shipped wrong. `dev/build_continua.py` now bands the
bucket by Gregorian Easter md as well, separating them (0 ambiguous buckets).
