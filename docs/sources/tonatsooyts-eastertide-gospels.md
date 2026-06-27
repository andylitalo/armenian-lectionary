# Canon of the Eastertide Four-Gospel Rotation

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*), **p. 488** (the rubric opening
> the weekdays after Low Sunday). English from the `gemini-flash` translation; grabar
> from the page-aligned OCR (`grabar-ocr/.../merged.md`, page_0488).
>
> **Season governed:** **Eastertide** (Յինանց, the 50 days Easter → Pentecost),
> specifically the ferial Gospel cycle that begins the Monday after Low Sunday.

---

## The rubric (as received)

> "**Today begin to read the four Gospels in order**: **Luke** in the morning, and
> **John** at midday, **Matthew** at the first evening [service], and **Mark** at the
> dismissal; **until Pentecost you shall complete the four Gospels up to the discourses
> on the Passion**."

Grabar (p. 488): «Այսօր **սկիզբն արա ընթեռնուլ զչորս գլուխ աւետարանսն կարգաւ**.
**զՂուկասուն յառաւօտուն**. եւ **զՅովհաննուն ի ճաշուն**. **զՄատթէոսին յերեկոյին
առաջին**. եւ **զՄարկոսին յարձակմանն**, որ **մինչեւ ի Հոգեգալուստն վերջացուսցես
զչորեսին աւետարանսն մինչեւ ի չարչարանաց ճառսն**։»

So through Eastertide each day carries **four** Gospels — one per office — read
*lectio continua* through Luke, John, Matthew, and Mark in parallel, stopping at the
Passion narratives by Pentecost.

---

## How the engine uses this rubric

Eastertide days are Easter-anchored, so they resolve through the validated `E` (and
band-refined `EB`) keyspace. The data exhibits the rubric exactly. Beginning the Monday
after Low Sunday (Easter + 8) and continuing to Pentecost, every ferial day's
reading-set ends with **four Gospels in the order Luke · John · Matthew · Mark** — the
four parallel continua of the rubric. Verified byte-identical across years (e.g. 2018
and 2025 agree day-for-day):

| Day | Gospels (Luke · John · Matthew · Mark) | Source |
|---|---|---|
| Easter + 8 | Luke 4.31-41 · John 1.18-28 · Matthew 4.12-25 · Mark 1.14-20 | `validated-table` |
| Easter + 15 | Luke 7.1-10 · John 3.13-21 · Matthew 9.9-17 · Mark 3.13-19 | `validated-table` |
| Easter + 30 | Luke 12.32-48 · John 7.37-8.11 · Matthew 14.13-21 · Mark 7.1-16 | `validated-table` |

The steadily advancing chapter numbers confirm the *continua* march (each Gospel
progresses a few chapters per week), and the parallel four-Gospel structure confirms
the one-per-office assignment. Bright Week (Easter + 1 … + 7) precedes this and carries
the Resurrection-appearance Gospels (Luke 24…), consistent with the rubric's *"Today
begin"* being placed *after* Low Sunday.

**Code impact this round:** *report-only / confirmatory.* The Eastertide rotation is
already shipped validated for every cached year; no code change is needed. This canon
documents the primary-source rule and exhibits the engine's exact agreement with it —
useful when demonstrating to authorities that the engine's Eastertide output is not a
statistical coincidence but the prescribed four-Gospel continua.

---

## Residual subtleties

1. **The Passion cut-off.** The rubric stops the continua "up to the discourses on the
   Passion" by Pentecost. The engine reproduces the attested readings rather than
   computing the cut-off, so the stopping chapters are inherited from the cache; a
   generative continua model could derive them, but that is unnecessary while the
   validated table covers every Eastertide day.
2. **Feasts within Eastertide.** Fixed feasts that land in Eastertide (e.g. the
   Annunciation) reorder against this cycle — handled separately by
   [`tonatsooyts-annunciation-canon.md`](tonatsooyts-annunciation-canon.md), whose
   Eastertide branch reads "the Gospel of the day after the Annunciation Gospel,"
   i.e. the four-Gospel cycle resumes after the feast's proper.
