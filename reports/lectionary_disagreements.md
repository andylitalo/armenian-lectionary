# Lectionary Disagreements & Open Data Items (2001–2026)

> Working record for resolution. Engine state at time of writing: **0 wrong**
> (validated contract intact), all 41 tests green. Residue = **4 best-effort misses
> + 26 blanks**. Reproduce any figure with the commands noted per section
> (`dev/residue_classifier.py`).
>
> **Tail-compression misses resolved (2026-07-05).** The 7 summer/winter/autumn tail saints
> (Eugenia/Eugenios/Andrew/Adrian/Abraham on 2004-01-27/29, 2004-11-15/16, 2008-07-31/08-04,
> 2009-01-29) now ship VALIDATED from the cycle tier, via per-taregir source sequences fed into
> the existing per-season anchoring (summer Vardavar-march, autumn Heesnak, winter Jan-14 fill).
> The right canon per taregir was identified in analysis via a Julian-Easter computation (leap
> years take the pair's lower letter post-Feb-29, per the p.610 rubric `... ի յետին տарегիրն Ո
> ... զկնի Վարդավառին`); the sequences themselves are keyed by **Gregorian** Easter md (the same
> collision-keying the existing `_SOURCE_SUMMER` uses), and the drop-guard confirms every
> placement against cached GT (0 wrong). **Note — an Easter-offset transfer was
> tried and empirically falsified** (transferring the Չ canon's Andrew @ manuscript Sept-3 lands
> at civil 2019-09-09, but GT has 2019 Andrew at 01-29): these floating saints are NOT at a fixed
> Easter offset — each season has its own anchor and per-taregir window compression. The fix is
> therefore the sequence *content/order* per taregir, not a new date rule. Implemented in
> `dev/build_second_volume_cycles.py` (`_SOURCE_SUMMER["03-23"]`, `_SOURCE_WINTER`,
> `_SOURCE_AUTUMN_LEAP`, plus a parity-split in the drop-guard so a leap cache year of the same
> Gregorian Easter — 2020 for 04-12 — cannot drop the non-leap winter). Locked by
> `tests/test_regression.py::TestSummerSourceMarch` / `TestAutumnSolarMarch` / `TestWinterSourceMarch`.
> Net: MISS 11 → 4 (the remaining 4 are the Apr-7 Annunciation composites).
>
> **Provenance closed (2026-07-05, plate read).** All four sequences are now line-for-line
> source-confirmed — no divergence. The crux is a **Julian/Gregorian taregir-selection** rule:
> the engine keys cycles by *Gregorian* Easter md, so a year uses the canon whose *Julian* Easter
> equals its Gregorian Easter (2004 → Յ/04-11, 2009 → Ն/04-12), **not** its true-Julian taregir
> (ԹԸ, Հ). Under the correct canon the source matches GT exactly:
> - **Winter 2004** — Յ canon (p.601): Eugenia Jan 26 / Eugenios Jan 28, +1 leap shift → 01-27/29.
> - **Winter 2009** — Ն canon (p.603): Eugenios+Andrew merged on 27, Adrian on 29 (exact).
> - **Autumn 2004** — the **ՆՅ leap rubric** (p.603) *sends* Andrew & Adrian out of January to
>   Yeghem's (Յ) November "after the tenth Sunday" (`... տօնին սոքա ի յետին գիրն Յ, զկնի
>   տասներորդ կիւրակէին`), joining native Abraham & Khoren; order witnessed in Մ (p.600).
> - **Summer 2008** — the ՉՈ rubric (p.610) moves the same saints past Vardavar to letter Ո.
>
> An earlier draft wrongly called autumn 2004 a "source-vs-modern divergence" by reading Ը (the
> true-Julian taregir, an August outlier the modern calendar does not use) instead of the ՆՅ rule.
>
> **Co-celebration recovery (2026-07-03).** The Presentation eve (Feb 13) now ships
> VALIDATED via a dedicated Easter-offset keyspace `PrLE` (the exact analog of `AnnE`
> for the Annunciation eve): 17 days across 8 cross-validated offset buckets, 0 wrong;
> the remaining 9 single-sample offsets stay honest blanks. The Presentation of the
> Theotokos (Nov 21) — already `validated-composite` for 23/26 years — now also resolves
> its 3 Advent-Sunday collision years (2004/2010/2021, Advent-length band 46). Band 46's
> Advent Sunday is always Nov 21 and thus structurally unlearnable, but the Tōnats'oyts
> names it the "Eleventh Sunday after the Holy Cross" — identical to band 47, whose
> readings are validated — so the co-celebration composite (proper ++ 11th-Sunday) ships
> validated, exact-matching GT. Confirmed against the printed Tōnats'oyts (pp. 543, 551;
> digitized in `grabar-ocr/runs/human__proj__tess__gemini-min/pages/page_0543,0551`):
> see `docs/sources/tonatsooyts-presentation-theotokos.md`.
> Net: BLANK 46 → 26, MATCH +20, WRONG still 0.
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
- **4 — Class D, Annunciation-in-Lent:** ~~editorial / out-of-scope~~ **RESOLVED for
  completeness (2026-07-04)** — see the Class-D note below.
- **3 — Class B, Assumption continua:** needs the continua-index engine.

> **Class D — Annunciation-in-Lent, resolved for completeness (2026-07-04).** The four
> Apr-7 composites (2001, 2008, 2018, 2019) are single-sample Easter offsets the `AnnE`
> keyspace can never cross-validate, so they ship best-guess `generative-composite`.
> Byte-exactness is **provably not derivable**: the published calendar reduces the
> co-celebrated day (drops a Matins/vespers set, keeps only a Gospel), but *which sub-run
> is which* is recorded in **no reachable source** — sacredtradition.am (all language
> views) and the reference cache are flat, type-tagged lists with no service boundaries,
> and the grabar-ocr corpus is the Tōnats'oyts typikon, not a per-day service-slotted
> Ճաշоց. Reproducing the reduction from the flat data would be cache-fitting (the day-first
> cases disprove any flat rule: 2001 keeps through its first Gospel, 2004 keeps its whole
> set). Per the editorial decision, the composite therefore targets **completeness, not
> exactness**: it errs toward a superset (extra day readings acceptable) and guarantees it
> never *drops* a reading the calendar keeps. Two faithful rule fixes closed the only two
> cases that previously dropped a key reading — a deep-Lent **Sunday** co-celebrates its
> Liturgy (2019 `Luke 21.5-38`), and Eastertide appends the **eve's** resurrection Gospel
> (2018 `John 21.1-14`). Now **GT ⊆ engine output for all 26 cached Apr-7 collisions**;
> 2004/2011/2022/2023 stay exact, validated years untouched, WRONG still 0. Implemented in
> `_annunciation_composite` (`lectionary.py`); locked by
> `tests/test_regression.py::TestAnnunciationCompositeCompleteness`; rubric in
> `docs/sources/tonatsooyts-annunciation-canon.md`. A genuinely byte-exact fix remains
> possible only by enriching the slot data with service structure from a digitized Ճаշоц
> (out of scope).

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

Update (2026-07-03, parser-hygiene + leap-parity + winter-march pass, shipped): **0 wrong**,
best-effort-exact 49 → 56, 28 tests green.
- **Parser hygiene — done.** `_match` now aliases Anthony/Anton, excludes normalized
  generic folds (the stray `holi` collision that made every "Holy …" entry hit
  `seventy_two_holy`), guards name collisions (David-the-Prophet, Gregory+Nicholas), strips
  `[Note: …]`, and derives month context per canon span (no cross-canon leak). Unit tests in
  `tests/test_parser.py`.
- **Leap-shift — done for the one in-window divergence.** The cycle tier is now
  leap-conditional (`{ "common": …, "leap": … }` records; `_LEAP_SUMMER` override + parity-
  partitioned drop-guard). Easter 03-27 ships **Peter in 2005 (non-leap)** and **Athanasius
  in 2016 (leap)** — both exact — via the documented ՍՌ rubric. Locked by
  `tests/test_regression.py::TestLeapSummerParity`.
- **Winter (PN) march — done; autumn (As) already clean (0 misses).** A post-Nativity
  consecutive-saint-weekday march (`_WINTER_SEQUENCE`, generated per leap parity since the
  January weekdays shift with Feb-29, shipped through the leap-conditional records) fixes
  the long-window (2011) tail saints — winter misses 7 → 3. Locked by
  `tests/test_regression.py::TestWinterMarch`.

**Reclassification:** the summer misses were *not* all leap-shift. Only the 2005/2016 pair
(Easter 03-27) genuinely diverged by leap parity, and that is now fixed. The remaining ~9
summer misses are **sequence-compression** on tail saints (Eugenios/Eugenia/Andrew/Adrian
in long or late-Easter windows) and hit **non-leap** years too (2002, 2013, 2015, 2026) —
a fixed weekday-march can't model the variable spacing. No documented leap rule addresses
them.

Remaining, in rough priority for lectionary accuracy:

1. **Summer + winter + autumn tail-compression misses — RESOLVED (2026-07-05).** The 7
   remaining tail-saint misses (Eugenia/Eugenios/Andrew/Adrian/Abraham across 2004/2008/2009)
   now ship validated from the cycle tier via per-taregir source sequences fed into the existing
   per-season anchoring; see the header note. A Julian-Easter computation identified each canon in
   analysis (leap → lower letter post-Feb-29); `_SOURCE_SUMMER["03-23"]`, `_SOURCE_WINTER`,
   `_SOURCE_AUTUMN_LEAP` (keyed by Gregorian Easter md) supply
   the orders; a drop-guard parity-split protects the non-leap winter from same-Easter leap cache
   years. An Easter-offset transfer was tried and falsified (autumn/winter are solar/Jan-14
   anchored, not Easter-relative). Residue: MISS 11 → 4.
2. **Un-scramble the two-column OCR reading order (LOW priority for accuracy).** The
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
   reading the lines-JSON. Sequence this **after** item 1.
