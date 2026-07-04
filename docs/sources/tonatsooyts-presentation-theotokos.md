# Canon of the Presentation of the Holy Mother of God to the Temple (Nov 21)

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*, the Armenian Church
> Calendar/Typikon):
> - **p. 543** — the full canon of the feast (proper readings + the Sunday-collision
>   rubric), laid out immediately after the **Eleventh Sunday after the Holy Cross**.
> - **p. 551** — a brief note listing the Presentation (Ընծայմանն) among the three
>   feasts of the Theotokos kept at Sunday rank.
>
> Both pages are digitized in this project's OCR corpus (human-corrected gold):
> `grabar-ocr/runs/human__proj__tess__gemini-min/pages/page_0543_human.lines.json`
> and `…/page_0551_human.lines.json`. The engine's runtime table is independently
> distilled and cross-year-validated from the **sacredtradition.am** Tōnats'oyts
> (2001–2026; `lectionary_data.json` `source`); the printed pages below confirm the
> proper, the fixed Nov-21 date, and the numbered-Sunday placement that closes the gap.
>
> **Feast:** Presentation of the Holy Theotokos to the Temple (Տօն Ընծայման
> Ս. Աստուածածնի ՚ի տաճար) — fixed date **November 21**. A feast of the Theotokos.

---

## The rubric (as received)

November 21 carries a **fixed proper** reading-set for the Presentation of the Theotokos
(verified byte-identical across all 26 cached years, 2001–2026):

```
Song of Solomon 1.2-11
Proverbs 11.30-12.4
Isaiah 52.7-10
Zechariah 2.10-13
Malachi 3.1-2
St. Paul's Second Epistle to the Corinthians 6.16-7.1
Luke 1.39-56                 ← the Visitation (Magnificat) Gospel
```

**Canonical co-celebration rule.** Like every Theotokos feast that is not a Great
(dominical) feast, the Presentation does **not** suppress the Sunday Liturgy when it
lands on a Sunday: the two are **co-celebrated**. The Sunday keeps its own proper
Liturgy readings, and the feast's proper is prepended. This is the same displace/
co-celebrate rubric the engine already applies to every embedded fixed-feast (see the
"Embedded fixed-feast composites" section of `lectionary.py` and
[`tonatsooyts-annunciation-canon.md`](tonatsooyts-annunciation-canon.md) for the
parallel Annunciation case):

- **Falls on a Saturday or a dedicated saint-weekday slot** → the feast **displaces**
  it (proper only).
- **Falls on a Sunday / ferial-fast / post-feast continua slot** → the feast
  **co-celebrates**: **proper ++ that slot's own readings**.

The ground truth confirms this directly: for the 23 of 26 cached years where Nov 21 is
an ordinary weekday or Sunday, the engine already ships `validated-composite` =
`proper ++ slot`, exact-matching the cache.

---

## The printed canon (Tōnats'oyts p. 543)

Page 543 lays out the **Eleventh Sunday after the Holy Cross** and then, on the same page,
inserts the fixed Presentation — the printed book itself places Nov 21 right after that
numbered Sunday. Transcribed from the human-corrected OCR (`page_0543_human.lines.json`),
with the reading identifications:

**Eleventh Sunday after the Holy Cross** — *Մետասաներորդ Կիւրակէ։ Հարց Յարութեան։*
(the Resurrection lections):

| Grabar | Reading |
|---|---|
| Մարգարէ Եսայ. **ԻԹ. 11** … վ. **20** | **Isaiah 29.11-20** |
| Առաքեալն Փիլիպ. **Դ. 8** … վ. **24** (excl.) | **Philippians 4.8-23** |
| Աւետարան Ղուկ. **ԺԱ. 1** … վ. **13** | **Luke 11.1-13** |

**The Presentation, inserted here** — *Իսկ Տօն Ընծայման՝ երից ամաց սուրբ Կուսին ՚ի
տաճարն… **որ կատարի միշտ ՚ի նոյեմբերի 21*** ("And the Feast of the Presentation of the
three-year-old holy Virgin to the Temple … **which is always celebrated on November
21**"). Its Chashou (Midday Liturgy) proper:

| Grabar | Reading |
|---|---|
| Գիրք Երգ երգոց **Ա. 1** … վ. **11** | **Song of Solomon 1.2-11** |
| Առակ. **ԺԱ. 30** … վ. **ԺԲ. 4** | **Proverbs 11.30-12.4** |
| Մարգարէ Եսայ. **ԾԲ. 7** … վ. **10** | **Isaiah 52.7-10** |
| Մարգարէ Զաքար. **Բ. 10** … վ. **13** | **Zechariah 2.10-13** |
| Մարգարէ Մաղաք. **Գ. 1** … վ. **2** | **Malachi 3.1-2** |
| Առաքեալն բ. Կորն. **Զ. 16** … վ. **Է. 1** | **2 Corinthians 6.16-7.1** |
| Աւետարան Ղուկ. **Ա. 39** … վ. **56** | **Luke 1.39-56** |

The seven match the engine's fixed proper byte-for-byte. And the page carries the
**explicit Sunday-collision rubric**:

> *Արարչական, ըստ պատշաճին. **եթէ ՚ի Կիւրակէի հանդիպիցի՝ Նորաստեղծեալ**։*
> ("The Creation hymn, as fitting; **but if it falls on a Sunday — [sing] 'Newly
> Created' (Նորաստեղծեալ)**.")

— the same clause the Annunciation canon uses for its own Sunday collision (p. 486,
"if it coincides with a Sunday … say 'Newly Created'"), confirming the feast is written
to *anticipate* landing on a Sunday and to be observed *together with* it.

## The Sunday rank of the feast (Tōnats'oyts p. 551)

Page 551 groups the Presentation with the other Theotokos feasts kept at Sunday rank —
i.e. observed with a full Liturgy, which is *why* it co-celebrates instead of being
suppressed:

> *Սուրբ Աստուածածնի երից տօնից աւուրքն. այսինքն՝ Յղութեանն, եւ Ծնընդեանն, եւ **Ընծայմանն**։*
> ("The days of the three feasts of the Holy Theotokos: the Conception, the Nativity,
> and the **Presentation**.")

These are exactly the three embedded Theotokos feasts the engine already carries
(`EMBEDDED_PROPER`): Conception (Dec 9), Nativity of the Theotokos (Sep 8), and the
Presentation (Nov 21).

---

## The three-year collision, and why it needed source support

In **2004, 2010, 2021** (and, going forward, every year whose Advent is at its shortest),
Nov 21 is not merely *a* Sunday — it is the **Advent (Heesnak) Sunday itself**, the Sunday
that opens the Fast of Advent. The engine keys the movable Advent-Sunday reading by
Advent-length band (`HEB = "{advent_length}:{days_after_Heesnak_Sunday}"`), and the
shortest Advent is band **46** (Heesnak Sunday = Nov 21, the latest it can fall;
`advent_length` = Nov 21 → next Jan 6 = 46 days).

The band-46 offset-0 slot is **structurally unlearnable**: band 46 ⇔ the Advent Sunday
*is* Nov 21, and Nov 21 is *always* the embedded feast, so no year ever contributes that
slot's bare readings to the learned table. These three years therefore previously shipped
as honest **blanks** (`algorithmic-estimate`, empty) to preserve the 0-wrong contract.

**The gap is closable because the Tōnats'oyts names the Sunday.** The ground-truth label
for all three collision years reads, verbatim:

> *"Eleventh Sunday after the Holy Cross · Presentation of the Holy Mother of God to the
> Temple · Eve of Fast of Advent"*

So the movable slot is the **Eleventh Sunday after the Holy Cross** — and *that* Sunday's
readings **are** already validated in the engine's table, learned from the years where the
Eleventh Sunday after the Holy Cross fell on a non-embedded date (band 47, Heesnak Sunday
= Nov 20):

```
Isaiah 29.11-20
St. Paul's Epistle to the Philippians 4.8-23
Luke 11.1-13
```

### Evidence: bands 46 and 47 are the same numbered Sunday

The Advent Sunday's numbered identity ("Nth Sunday after the Holy Cross") is monotone in
its date, and bands 46 and 47 (Nov 21 / Nov 20) both land on the **Eleventh**; only the
longer Advents (bands 48–52, Heesnak Sunday Nov 15–19) drop back to the **Tenth**. Every
cached year agrees, with no counterexample:

| Band | Heesnak Sunday | Numbered Sunday | Advent-Sunday readings | Years |
|---|---|---|---|---|
| **46** | Nov 21 | **Eleventh** | *(embedded — GT shows `proper ++` the below)* | 2004, 2010, 2021 |
| **47** | Nov 20 | **Eleventh** | Isaiah 29.11-20 · Phil 4.8-23 · Luke 11.1-13 | 2005, 2011, 2016, 2022 |
| 48 | Nov 19 | Tenth | Isaiah 25.9-26.7 · Phil 1.1-11 · Luke 9.44-50 | 2006, 2017, 2023 |
| 49–52 | Nov 15–18 | Tenth | *(same as band 48)* | 2001, 2007, 2012, 2018, 2002, 2013, 2019, 2024, 2003, 2008, 2014, 2025, 2009, 2015, 2020, 2026 |

Removing the fixed proper from any band-46 ground-truth day leaves **exactly** the band-47
"Eleventh Sunday" reading-set — confirming the co-celebration decomposition is the correct
one, not an accidental fit. The printed Tōnats'oyts corroborates this independently: on
p. 543 it inserts the Nov-21 canon **directly after the Eleventh Sunday after the Holy
Cross**, i.e. at exactly the point in the movable Sunday sequence where Nov 21 falls when
it is itself a Sunday.

---

## How the engine uses this rubric

`_movable_coords` (the movable slot an embedded feast lands on) emits the band-46 offset-0
Advent-Sunday slot **through band 47**, because both bands are the Eleventh Sunday after
the Holy Cross. `_embedded_composite` then returns `proper ++ slot`, and the day ships as
`validated-composite` — the same tier and provenance as the other 23 Nov 21 years. Both
components are independently validated (the proper across 26 years; the Eleventh-Sunday
readings across 4 band-47 years), and the composite reproduces the ground truth **byte-for-
byte** for 2004/2010/2021:

```
proper (7)                       ++   Eleventh Sunday after the Holy Cross (3)
Song of Solomon 1.2-11                 Isaiah 29.11-20
Proverbs 11.30-12.4                    St. Paul's Epistle to the Philippians 4.8-23
Isaiah 52.7-10                         Luke 11.1-13
Zechariah 2.10-13
Malachi 3.1-2
2 Corinthians 6.16-7.1
Luke 1.39-56
```

This is the only place the engine resolves a slot it could never *learn* from the cache;
it does so strictly by the Tōnats'oyts's own naming of the day plus the already-validated
Sunday readings, so it remains inside the "never emit a wrong validated reading" contract.

> **Contract note (2026-07-03).** The 0-wrong contract is unchanged. What changed is that
> a gap the cross-year learner structurally *cannot* reach is now filled from the source
> text where — and only where — the Tōnats'oyts states the rule unambiguously (the feast's
> co-celebration + the day's numbered-Sunday identity). Regression: `tests/test_regression.py::
> TestCocelebrationResolvers::test_nov21_advlen46_collision_recovered`.
