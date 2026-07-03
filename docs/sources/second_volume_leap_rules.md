# Second Volume — Leap-Year Saint-Reassignment Rules

> **Source:** Տօնացոյց *Tōnats'oyts'* **Second Volume**, per-Dominical-Letter canons.
> Grabar from the human-corrected OCR run
> (`grabar-ocr/runs/human__proj__tess__gemini-min/`), English from its `gemini-flash`
> translation. Codes resolved against `great_paschal_cycle_index.csv` (year→taregir)
> and `second_volume_index.csv` (taregir→page).
>
> **Status: reference only — NOT wired into the engine.** See "Why not encoded" below.

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

## Why NOT encoded into the engine

Verified against ground truth and the live engine:

1. **Redundant.** The engine's movable-season frame (Transfiguration/Assumption/
   Exaltation "closest-Sunday" anchors, Easter-offset keying) + the Second-Volume
   cycle tier **already reproduce these leap placements**. Every day the ՍՌ(2016) and
   ՑՐ(2024) rules govern already matches GT exactly; the ՉՈ(2008) target days largely
   match. Encoding the rules adds ~0 exact-match.
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
