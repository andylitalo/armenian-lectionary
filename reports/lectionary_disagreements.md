# Lectionary Disagreements & Open Data Items (2001–2026)

> Working record for resolution. Engine state at time of writing: **0 wrong**
> (validated contract intact), all 15 tests green. Residue = **42 best-effort misses
> + 29 blanks** (was 46; the co-celebration resolvers below recovered 17). Reproduce
> any figure with the commands noted per section (`dev/residue_classifier.py`).
>
> **Co-celebration recovery (2026-07-03).** The Presentation eve (Feb 13) now ships
> VALIDATED via a dedicated Easter-offset keyspace `PrLE` (the exact analog of `AnnE`
> for the Annunciation eve): 17 days across 8 cross-validated offset buckets, 0 wrong;
> the remaining 9 single-sample offsets stay honest blanks. The Presentation of the
> Theotokos (Nov 21) already ships `validated-composite` for 23/26 years; the band fix
> in `_movable_coords` (emit `HEB`/`HEpB`, mirroring `coords_for`) was applied, but the
> 3 collision years (2004/2010/2021) stay blank: they all have Advent-length band 46,
> whose band-0 Advent Sunday only ever falls on the embedded feast itself, so that slot
> is never learnable. Net: BLANK 46 → 29, MATCH +17, WRONG still 0.
>
> Sources referenced:
> - Human-corrected OCR run: `grabar-ocr/runs/human__proj__tess__gemini-min/` (the run
>   the engine builds from). English: `.../translations/gemini-flash/translated.md`;
>   Grabar per-page: `.../pages/page_XXXX_human.lines.json`.
> - Auto OCR run: `grabar-ocr/runs/auto__proj__tess__gemini-min/` (fallback; some pages
>   the human run lacks).
> - Rules catalogue: `docs/sources/second_volume_leap_rules.md`.

---

## Disagreement A (the scholarly decision) — Tōnats'oyts source vs. modern ground truth

**The 42 floating-saint days where the engine ships a labeled best-guess that does not
match the ground-truth cache.** These are the winter/summer/autumn hinge saints
(Eugenios, Adrian, Andrew the General, Theodosius, Abraham & Khoren, Cyricus,
Peter/Blaise, Vahan, Triphon, Athenogenes, Cyprian, Forefathers…), concentrated in
**extreme-Easter years and mostly NON-leap**.

**What each side says.** For these days the engine's `generative-saint` tier emits the
reading-set implied by the **Tōnats'oyts source laydown** (the canonical saint order,
laid into the movable window). The **ground-truth cache** (modern published calendar)
carries a different reading-set. Example days (`ENGINE` = source-derived guess,
`GT` = cache):

```
2011-01-31 (Cyprian)        ENGINE: Ezekiel 3.16-19 · 2Cor 6.1-14 · Matthew 12.22-32
                            GT    : Isaiah 46.12-13 · Galatians 3.13-22 · Luke 15.1-10
2005-07-26 (Theodosius)     ENGINE: Wisdom 5.1-8 · Baruch 3.31-4.4 · Romans 8.28-39 · John 10.11-16
                            GT    : Wisdom 6.1-9 · Isaiah 45.1-2 · 1Timothy 2.1-7 · Luke 7.1-10
2010-11-16 (Adrian)         ENGINE: Gen 18.33-19.2 · Job 38.4-7 · Isa 6.1-7 · Ezek 1.1-20 · Heb 1.6-14 · Matt 18.10-14
                            GT    : Lamentations 3.22-56 · Romans 8.18-27 · John 16.1-4
```

**Support — source side:** the Second-Volume per-taregir canons + the base saint chain
give a deterministic laydown; the readings come from `dev/saint_readings.json`
(First-Volume propers). **Support — GT side:** the scraped modern calendar
(`dev/reference_data/*.json`), which the residue reports show places these saints by the
*movable season frame*, shifting with Easter, and for these extreme-Easter years lands
them on coordinates seen in no other cache year (single-sample, not cross-validatable —
`reports/unpredictable_days.md`, `reports/residual_estimate_tail.md`).

**The decision to make:** for these 42 days, should the engine follow the **historical
Tōnats'oyts** (re-derive from source canons, accept cache mismatch) or the **modern GT**
(stop shipping a wrong best-guess; mark estimate/blank)? This is a scholarly/editorial
call, not resolvable from the files.

**Full inventory** (tier · leap? · feast). Reproduce with the snippet in
`reports/unpredictable_days.md` Method, or:
`venv/bin/python -c "..."` iterating `compute_armenian_lectionary` vs `dev.analyze.load_all`.

```
2001-04-07  generative-compo         Annunciation @ Great Lent day 41
2002-08-05  generative-saint         Eugenios, Makarios, …
2004-01-27  generative-saint  LEAP   Eugenia the Virgin …
2004-01-29  generative-saint  LEAP   Eugenios, Makarios …
2004-11-15  generative-saint  LEAP   Abraham & Khoren …
2004-11-16  generative-saint  LEAP   Andrew the General …
2005-07-23  generative-saint         Peter the Patriarch, Blaise …
2005-07-26  generative-saint         Theodosius & Children of Ephesus
2005-07-28  generative-saint         Cyricus & Julitta …
2005-07-30  generative-saint         Athanasius & Cyril of Alexandria
2008-04-07  generative-compo  LEAP   Annunciation @ Eastertide day 13
2008-07-19  generative-saint  LEAP   Peter the Patriarch, Blaise …
2008-07-21  generative-saint  LEAP   Anton the Hermit
2008-07-22  generative-saint  LEAP   Theodosius & Children of Ephesus
2008-07-24  generative-saint  LEAP   Cyricus & Julitta
2008-07-28  generative-saint  LEAP   Vahan, Gordius, Polyeuctus, Grigoris
2008-07-29  generative-saint  LEAP   Triphon, Barsauma, Onouphrius
2008-07-31  generative-saint  LEAP   Eugenia the Virgin …
2008-08-04  generative-saint  LEAP   Eugenios, Makarios …
2009-01-29  generative-saint         Adrian & Natalia …
2010-11-16  generative-saint         Adrian & Natalia …
2010-11-18  generative-saint         Abraham & Khoren …
2011-01-31  generative-saint         Cyprian the Bishop …
2011-02-01  generative-saint         Athenogenes the Bishop …
2011-02-03  generative-saint         Forefathers: Adam, Abel, Seth …
2011-02-12  generative-saint         Thaddeus, Apostle of Armenia …
2013-08-05  generative-saint         Eugenios, Makarios …
2015-08-04  generative-saint         Andrew the General …
2015-08-05  generative-conti         Fast day (Assumption continua)
2015-08-06  generative-saint         Adrian & Natalia …
2016-07-26  generative-saint  LEAP   Theodosius & Children of Ephesus
2016-07-28  generative-saint  LEAP   Cyricus & Julitta …
2018-04-07  generative-compo  LEAP   Annunciation @ Easter day 7
2018-08-03  generative-conti         Fast day (Assumption continua)
2019-01-29  generative-saint         Andrew the General …
2019-04-07  generative-compo         Annunciation @ 6th Sun of Lent
2021-11-16  generative-saint         Adrian & Natalia …
2021-11-18  generative-saint         Abraham & Khoren …
2024-08-05  generative-saint  LEAP   Eugenios, Makarios …
2026-08-04  generative-saint         Andrew the General …
2026-08-05  generative-conti         Fast day (Assumption continua)
2026-08-06  generative-saint         Adrian & Natalia …
```

(The remaining 29 blanks are separate: mostly February Class-D embedded feasts —
single-sample Presentation-eve offsets, Annunciation-in-Lent — out of scope under
exact-match. The cross-validatable Presentation-eve offsets were recovered via `PrLE`;
see the co-celebration recovery note in the header.)

---

## Item 1 — Garbled leap code + apparent GT contradiction (Ր canon / ՑՐ / 2024)

> **RESOLVED (2026-07-02).** Plate read confirms the code is **`ՐՏ`** (Ր = first/higher
> letter, Տ = last/lower letter; feasts move to last-letter **Տ**, after Transfiguration —
> the same pattern as the Չ/Ս/Ն canons). The doc's `ՑՐ` guess wrongly assumed Ր was the
> *lower* letter. Since 2024 = **ՑՐ ≠ ՐՏ**, the p.627 rubric governs a *different,
> out-of-window* leap taregir and never applied to 2024 — so there is **no contradiction**:
> 2024 correctly celebrates Cyprian (07-15) and Athenogenes (07-16), both `validated-table`
> matches. OCR corrected in `page_0627_human.lines.json` (`region_02_right/line_002` →
> `տարեգիրքն ՐՏ …`; `line_006` → `յետին տարեգիրն Տ …`). Residue unchanged (this was never a
> shipped wrong reading). Leap-rules catalogue updated.

**The rule** (`docs/sources/second_volume_leap_rules.md`, Ր canon): in the leap taregir,
*skip* the four feasts Cyprian, Athenogenes, the Forefathers, and the 12 Apostles here;
instead Mon=Eugenia, and (per the same passage) Gregory the Theologian takes Thaddeus'
slot.

**The garbled code — exact location for correction:**
- File: `grabar-ocr/runs/human__proj__tess__gemini-min/pages/page_0627_human.lines.json`
- Page: **page_0627** · Region **region_02_right** (**column 2**) · line_id
  **`region_02_right/line_002`** (index 2).
- OCR'd Grabar (verbatim): **`արեզիրքն ԸծՏ. զայս չորս տօնս, այ-`**
  — the code reads **`ԸծՏ`**, which is not a valid leap pair. By canon position
  (page 627 = letter **Ր**; leap pairs are reverse-consecutive; 2024 = **ՑՐ**) the
  intended code is almost certainly **`ՑՐ`**. Please confirm from the plate.
- Related line to check on the same page: index 6, `region_02_right/line_006`:
  **`յյէտին տարեգիրն Տ՝ զկնի Վարդավա-`** — states the feasts move "to the last
  year-letter **Տ**, after Transfiguration." Verify whether that is **Տ** or **Ց**
  (it disambiguates where the four feasts land).

**The disagreement.** *Rule side:* in ՑՐ (2024), do **not** celebrate Cyprian /
Athenogenes in this interval. *GT side:* 2024 **does** celebrate them —
`2024-07-15` Cyprian, `2024-07-16` Athenogenes (both `validated-table`, match=True).
So either the code is not ՑՐ (then 2024 is not governed and there is no conflict), or
the modern calendar does not apply this rubric. Resolving the code settles it.
Reproduce: `venv/bin/python -c "from lectionary import compute_armenian_lectionary as C; import datetime; print(C(datetime.date(2024,7,15)))"`.

---

## Item 2 — ԹԸ / 2004 (Anthony) rule: missing from human run → use auto-OCR

> **RESOLVED (2026-07-02).** Page 574 has been run through the translation pipeline and is
> now in the human run (`page_0574_human.lines.json`, and in `translated.md`), so the ԹԸ
> Anthony rule is captured for completeness. As already noted below, this rule targets
> Anthony/Theodosius/Cyriacus/Vahan/Tryphon — **not** the 2004 residue saints
> (Eugenia/Eugenios/Andrew/Abraham) — so it does not reduce the residue; the 2004 misses
> remain part of Disagreement A. No engine-output change.

**Why the human run can't supply it:** the human OCR run **does not contain page 574**
(it has `page_0573_human` then jumps to `page_0575_human`). The ԹԸ Anthony rule sits on
**page 574**, so it is absent from the human translation — which is why it never
appeared in the human-run search. Page 574 needs human correction to enter the build.

**Auto-OCR provides it** — `grabar-ocr/runs/auto__proj__tess__gemini-min/pages/page_0574_auto.lines.json`,
region **region_01_left** (**column 1**), lines idx 5–14. Verbatim Grabar:

```
[idx 3]  Շբ. ԴՁ. Անտոնի, - և Տրիփոնի,
[idx 4]  Պարսամայ եւ Ոնոփրիոսի ճգնա-
[idx 5]  ւորացն։ Եթէ նահանջ ամի ԹԸ իցէն
[idx 6]  տարեգիրքն, դու յայս շաբաթի օրս
[idx 7]  զԱնտոնն մի՛ տօնիցէս, զի տօնեցա-
[idx 8]  յյառաջին գիրն Թ յետ ծննդեանն. [6]
[idx 9]  այլ ի շաբաթի օրն զթէոդոսն. յեր-
[idx 10] կուշաբաթին՝ զԿիրակոսն. յերեքշաբա-
[idx 11] թին՝ զՎահանն, և 'ի հինգշաբաթին՝
[idx 12] զՏրիփոնն տօնեսցես իւրեանց ընկերօն։
[idx 13] Իս ի հասարակ ամս, որպէս եդեալ[ք]ս
[idx 14] էևն, այսպէս տօնէա։
```

Translation: *"Saturday [Tone 4]: Anthony, Tryphon, Barsauma, Onuphrius the hermits.
**If the year-letters in a leap year are ԹԸ**, do not celebrate Anthony this Saturday,
for he was kept on the first-letter Թ, 9 days after the Nativity; instead celebrate
Theodosius on Saturday, Cyriacus on Monday, Vahan on Tuesday, and Tryphon on Thursday
with their companions. But in ordinary years, celebrate as set down here."*

ԹԸ = 2004 in-cache. **Note:** this rule targets Anthony/Theodosius/Cyriacus/Vahan/Tryphon;
the actual 2004 misses (Disagreement A) are Eugenia/Eugenios/Andrew/Abraham — different
saints — so this rule does not by itself resolve 2004's residue. Recommended action:
have a human confirm page 574 (auto-OCR is legible above) so it can join the human run
if the ԹԸ rule is wanted for completeness.

---

## Item 3 — Missing Second-Volume cycle: taregir Բ (Julian Easter 03-23)

> **RESOLVED (2026-07-02).** Pages 560–561 have been human-corrected into the human run,
> `dev/build_second_volume_cycles.py` re-run, and the Բ cycle (`03-23`) is now present —
> **35/35 taregirs** (was 34/35). As stated below, no civil year in 2001–2026 is taregir Բ,
> so engine output for the window is unchanged; this closes a completeness gap. All 12
> tests still green.

**What the cycle is.** `dev/second_volume_cycles.json` holds, per year-type, the
per-date saint laydown distilled from the Second-Volume canon —
`{ julian_easter_md : { "MM-DD" : [zone, saint_id] } }`. It has **34 of 35** taregir
cycles (341 dated entries). The one absent is **`03-23`**, i.e. the **taregir Բ** canon
(Julian Easter **March 23** — the *earliest-Easter* year-type), whose plate is
**Second-Volume pages 560–561** (`second_volume_index.csv`: `Բ,03-23,560,3`).

**Why it's missing.** The build reads the human run, and the human run **does not
contain pages 560 or 561** (`page_0560`/`page_0561` absent). No source → no parse.

**Impact on 2001–2026: none.** No civil year in the window is taregir Բ (the window's
taregirs are Լ,Ր,Ո,ԹԸ,Ռ,Մ,Ե,ՉՈ,Հ,Ա,Յ,ԽԼ,Ր,Ձ,Թ,ՍՌ,Խ,Ե,Չ,ՁՀ,Ս,Յ,ՑՐ,Ձ,Թ). Բ recurs
only outside the window (past/future extreme-early-Easter years). It is a
**completeness gap, not a cache gap**.

**How to fill it.** The **auto OCR run has pages 560 and 561**
(`auto__proj__tess__gemini-min/.../page_0560.txt`, `page_0561.txt`), so the Բ cycle can
be built from auto-OCR, or by human-correcting those two plates into the human run and
re-running `dev/build_second_volume_cycles.py`.

---

## RESOLUTION (2026-07-02): Disagreement A is not scholarly — it's a fixable placement bug

Investigation of `2005-07-26` (Theodosius) and the full 42 proved there is **no
source-vs-modern conflict**. Each saint has one canonical reading-set (unanimous across
26 cache years); the feast identity per day is agreed. The engine's `generative-saint`
tier merely **mis-orders the saint chain** in compressed years. Reclassification of the 42:

- **35 — Class A, weekday-anchored floating saints (FIXABLE, 0-wrong):** 21 summer,
  8 winter, 6 autumn. Deterministic from the Second-Volume canon.
- **4 — Class D, Annunciation-in-Lent:** editorial / out-of-scope.
- **3 — Class B, Assumption continua:** needs the continua-index engine.

### Root cause of the empty 03-27 (Զ) cycle — three compounding errors

1. **Missing pages in the human run.** The Զ canon spans manuscript pages 566–570, but
   the human run has only **566 and 568** (567, 569, 570 absent). The **auto run has all
   three**. The summer section is on **page 567**.
2. **Summer saints are weekday-anchored, not dated.** On page 567 the post-Transfiguration
   saints are listed by weekday with **no leading day-number** (`Saturday. Peter/Blaise`,
   `Tuesday. Theodosius`, `Thursday. Cyricus`, `Saturday. Athanasius/Cyril/Gregory`). The
   build's parser requires a leading `NN.` date, so it captures **none** of them — this is
   why every canon's summer section yields zero entries.
3. **Parser bugs on the inline autumn/winter entries:** month value inherits stale across
   page breaks (Sept "Exaltation" tagged month 02), and `_match` false-positives
   ("Gregory **and Nicholas**"→`gregory_the_illuminator`; "**David the prophet**"→
   `david_of_dvin`; "Conception…"→`seventy_two_holy`). The cache drop-guard then correctly
   discards the whole corrupted cycle → 0 entries.

### The fix (verified end-to-end on 2005)

Anchor the summer chain to Transfiguration: `Vardavar = Gregorian Easter + 98d`; the canon
says start "on the Saturday after Friday of the 3rd week" = **Vardavar + 19d → next Sat**.
Then walk the canon's weekday list. For 2005 (Easter 03-27 → Vardavar 07-03 → +19 = 07-22
Fri): Sat **07-23 Peter/Blaise**, Mon 07-25 Anthony, Tue **07-26 Theodosius**, Thu **07-28
Cyricus**, Sat **07-30 Athanasius/Cyril/Gregory** — matches GT exactly (same for 2016, also
03-27).

**Build required (gated on green-light):** (a) fall back to the auto run for pages the
human run lacks (or human-correct 567/569/570); (b) extend `build_second_volume_cycles.py`
to parse weekday-anchored post-Transfiguration/Assumption entries and assign dates via the
Vardavar+19d walk; (c) fix the month-inheritance and false-positive-match bugs. The cache
drop-guard keeps every step 0-wrong. Expected: ~35 of the 42 misses convert to validated.

---

## Follow-ups / TODO

Status after the summer pass (2026-07-03, shipped): **0 wrong**, best-effort-exact
39 → 49, summer misses 21 → 14, 12 tests green. Implemented in
`dev/build_second_volume_cycles.py` as the canonical Vardavar-anchored summer march
(`_SUMMER_SEQUENCE`), merged with `setdefault`; runtime unchanged; drop-guard validates.

Remaining, in rough priority for lectionary accuracy:

1. **Winter (PN, post-octave) + autumn (As, post-Assumption) marches** — same
   canonical-weekday mechanism as summer; targets the 8 winter + 6 autumn floating-saint
   misses. Highest-value next step.
2. **Leap-shift exceptions** — the 14 remaining summer misses are Easter-dates served by
   both a leap and a non-leap year that place the first Saturday differently (e.g.
   2005-07-23 Peter vs 2016-07-23 Athanasius). Needs leap-aware placement to recover; the
   drop-guard currently leaves them best-effort (0-wrong).
3. **Parser hygiene** — the `_match` false-positive (`Anthony`≠`anton` normalization; also
   "Gregory and Nicholas"→Illuminator, "David the prophet"→David of Dvin) and the
   month-header inheritance across page breaks; recovers dated-entry coverage.
4. **Un-scramble the two-column OCR reading order (LOW priority for accuracy).** The
   Second-Volume canon pages are two-column, and the layout step concatenates the columns
   back-to-front (right column emitted before left), so the flat text puts the Easter
   marker mid-page and breaks calendar order (see the Զ canon, page_0569: `region_01_right`
   holds Jul28→Sept, `region_02_left` holds the winter tail + Easter + summer start; each
   column is internally ordered). The summer fix sidesteps this (the canonical march never
   reads page order), and it does **not** affect the summer or leap-shift misses. Value is:
   (a) cleaner dated-line parser for fixed-date autumn/winter saints, and (b) it would let
   the build **derive** the summer/winter/autumn sequences (and any per-canon leap
   exceptions) from source instead of the hardcoded `_SUMMER_SEQUENCE` — better provenance,
   not better cache numbers. Suggested fix: reorder lines by `(page, column, index)` when
   reading the lines-JSON. Sequence this **after** items 1–3.
