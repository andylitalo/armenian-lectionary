# Canon of Low Sunday and the Antasdan (Blessing of the Fields)

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*), **p. 487** (the Antasdan rubric
> within the Annunciation canon) with the festal precedent on **pp. 462–463**. English
> from the `gemini-flash` translation; grabar from the page-aligned OCR
> (`grabar-ocr/.../merged.md`, page_0487).
>
> **Feast:** **Low Sunday** — Աշխարհամատրան Կիւրակէ (World Church / "New" Sunday),
> the octave of Easter, movable at **Easter + 7**.

---

## The rubric (as received)

From the Annunciation canon, governing the case where the Annunciation lands on Low
Sunday, but stating the **Antasdan order of Low Sunday itself** (p. 487):

> "Likewise, if it falls on **Low Sunday** (Ashkharhamatran Kiurake): after the Gospel
> [of the Annunciation], read the **Scripture and Gospel of the Antasdan [Blessing of
> the Fields]**, and perform the Antasdan. Then [read] the **Gospel of the day**, and
> 'Newly Created' (Norasteghtseal) and 'Save, O Lord' (Ketso)."

Grabar (p. 487): «Նոյնպէս եթէ յ**Աշխարհամատրան Կիւրակէ**ին հանդիպիցի, զկնի Աւետեաց
աւետարանին **զգիրք եւ զաւետարանն անդաստանին կարդա, եւ անդաստան արա**. եւ ապա
**զաւուր աւետարանն**, եւ Նորաստեղծեալ եւ Կեցո։»

The Antasdan itself is the four-corners blessing described at the head of the volume
(pp. 462–463): *"they shall bless the four corners of the world [Antasdan] … and they
shall read the four Gospels in the four corners of the church"* (grabar p. 463: «… եւ
ընթերցցին զչորս աւետարանս ի չորս կողմանս եկեղեցւոյն»).

---

## How the engine uses this rubric

Low Sunday is a fixed movable point (Easter + 7), so it resolves through the
already-validated Easter-core table (`E`). The Antasdan structure is **already present
and cross-year-invariant** in that table: the engine returns, for every year
2014–2026 byte-identically, the "Octave of Easter (New Sunday)" with the field-blessing
reading-block —

```
Luke 4.14-30
Acts of the Apostles 5.34-6.7
St. James General Epistle 3.1-12
John 1.1-17 · John 21.15-25 · Matthew 27.50-61 · John 20.26-31   (the four-corners Gospels)
```

— shipped as `validated-table` under keyspace `E`. The rubric explains *why* this
Sunday carries multiple Gospels (the four-corners Antasdan) and confirms the ordering
the data already shows.

**Code impact this round:** *report-only / confirmatory.* Low Sunday already ships
validated for every year; no estimate-tier day is recovered by a code change, and none
is needed. This canon documents the source for the Antasdan reading-block and ties it
to the corresponding branch in
[`tonatsooyts-annunciation-canon.md`](tonatsooyts-annunciation-canon.md) (the
Annunciation-on-Low-Sunday composite).

---

## Residual subtleties

1. **The Antasdan also occurs outside Low Sunday** (e.g. Palm Sunday eve, certain
   feast days). Those instances resolve on their own anchored keys; this canon scopes
   only the Low-Sunday occurrence, which is the one that interacts with the
   Annunciation collision rule.
2. **Order vs. content.** The rubric prescribes the *order* (Antasdan readings, then
   the day's Gospel); the engine ships the *set* of readings the source attests for the
   day. The two agree in the cache, so the validated table needs no adjustment.
