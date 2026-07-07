# Canon of the Annunciation to the Holy Virgin Mary

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*, the Armenian Church
> Calendar/Typikon), **pp. 486–488**. The inline page break ("Page 487") preserved
> below falls naturally in the middle of this range.
>
> **Digitized text:** pp. 486–487 are auto-OCR'd in the `grabar-ocr` pipeline —
> `runs/auto__proj__trocr500__gemini-min/pages/page_0486_auto.lines.json` and
> `page_0487_auto.lines.json` (fine-tuned TrOCR + Gemini minimal-edit), with the English
> reading in the same run's `translations/gemini/`. The Eastertide collision clause quoted
> below is transcribed from **page_0487**.
>
> **Feast:** Annunciation to the Theotokos — fixed date **April 7** (eve **April 6**,
> the Նախатонак / pre-festive). Celebrated for **seven days**.

---

## The rubric (as received)

We celebrate the Annunciation of the Holy Mother of God for seven days. But in the
evening on April 6th, whichever day it may fall upon, perform the Pre-festive service
(Նախատօնակ) after the proper office of the day.

Sharakan, Tone AK: "The Ineffable Mystery" (Խորհուրդն անճառ), with its proper
variables.

Following Litany: "The Holy Mother of God…"

Prayer: "Receive, O Lord…"

And on the night of April 7th, let the priests gather together in unity and come into
the chancel, and begin the Morning Hymn, Tone AK: "The Ineffable Mystery," with its
proper variables.

Alleluia: Of the Nativity.

Morning Song: "He shall come down like rain…"

Litany: "Holy Mother…"

Holy God (Trisagion): According to the order of the day.

Following Psalm 109 [110]: "The Lord said unto my Lord…" Antiphon: "From the womb…"
to verse 11 "…shall receive you."

Proverbs 11:30: "The fruit of righteousness…" to 12:4 "…is a crown to her husband."

Prophet Isaiah: [Selected text regarding the coming of the Lord]…

Gospel: "…the angel [departed] from her."

Litany: "Let us ask…" and "Save [O Lord]."

Prayer: "To Your almighty…"

And if it coincides with a Sunday of Great Lent, say the hymn "Newly Created"
(Նորաստեղծեալ) for two men.

**Page 487**

If it falls on other days, say the "Creation" hymn, and afterward, "Hidden Mystery."

### Midday Liturgy (Chashou)

Introit (Zhamamout): "Unwedded Mother of God" (Աստուածածին անհարս).

Antiphon: "My soul magnifies…"

Sharakan, Tone GK: "Tabernacle of the Mother of God."

Psalm, Scripture, and Gospel: The same as the morning.

Alleluia: "Rejoice, O favored one…"

Hagiody (Srbatsoutyun): "Multitudes" (Բազմութիւնք).

However, if it falls on **Palm Sunday, Great Thursday, Great Friday, Holy Saturday, or
Easter Sunday**, before the Blessing (Օրհնութիւն), choose the hymn "The Ineffable
Mystery" with its variables, and then read the Scripture and the Gospel. Afterward, the
Litany: "The Holy Mother of God," and Prayer: "Receive, O Lord," and then begin the
proper office of the day.

If it falls on **Lazarus Saturday, Great Monday, Great Tuesday, or Great Wednesday**,
before the Blessing, in place of the usual service hymn, choose the Blessing hymn of
the day with its variables. Read the Scripture and Gospel of the day, and say the song
of Nerses for the souls of the departed. Then begin the celebration of the
Annunciation, singing the Blessing "The Ineffable Mystery" according to the order, and
the rest. Do the same **if it falls during Yinants (the 50 days of Eastertide)**.
However, read the Gospel of the day after the Annunciation book and Gospel, followed by
"Save [O Lord]."

Likewise, if it falls on **World Church Sunday (Green Sunday)**, after the Annunciation
Gospel, read the Scripture and Gospel for the Blessing of the Fields (Անդաստան) and
conduct the Antasdan service. Then read the Gospel of the day, followed by "Newly
Created" and "Save [O Lord]."

At the Midday Liturgy and in the evening, the Psalms, Scriptures, and Gospels are of
the Resurrection. But for the Hambartsi hymn on Saturday evening, say the hymn of the
Coming, and on other days, say the hymn of the Annunciation along with "Holy Mother."

---

## How the engine uses this rubric

The Annunciation has a **fixed proper** reading-set (verified byte-identical across all
26 cached years, 2001–2026):

```
Song of Solomon 1.2-11
Proverbs 11.30-12.4          ← rubric: "Proverbs 11:30 … to 12:4"
Isaiah 52.7-10               ← rubric: "Prophet Isaiah … the coming of the Lord"
Zechariah 2.10-13
Malachi 3.1-2
2 Corinthians 6.16-7.1
Luke 1.26-38                 ← rubric Gospel: "…the angel [departed] from her" (Lk 1:38)
```

Because April 7 is fixed but Easter is movable, the feast collides with a different
movable day every year. The rubric prescribes a **deterministic collision rule**, which
the engine implements as `_annunciation_composite` in `lectionary.py`. The reading-set
is `[movable day's readings]` combined with `[the fixed proper]`, ordered by the rank of
the colliding day — exactly as the cached ground truth shows:

| Colliding day (Easter offset of Apr 7) | Rubric clause | Reading order |
|---|---|---|
| **Palm Sunday (−7), Great Thursday (−3), Great Friday (−2), Holy Saturday (−1), Easter (0)** | "read the Scripture and the Gospel [of the Annunciation] … then begin the proper office of the day" | **proper → day** |
| **Lazarus Saturday (−8), Great Monday (−6), Great Tuesday (−5), Great Wednesday (−4)** | "Read the Scripture and Gospel of the day … Then begin the celebration of the Annunciation" | **day → proper** |
| **Yinants / Eastertide (≥ +1)** | "the Psalms, Scriptures, and Gospels are of the Resurrection … read the Gospel of the day after the Annunciation book and Gospel" | **proper → day**; the eve's resurrection Gospel is added **only inside the Easter octave** (offset ≤ +8) — see below |
| **Lenten Sunday with its own readings** (offset ≤ −9 and offset % 7 == 0, e.g. the Sunday of the Coming) | the day has a Liturgy, so its readings co-celebrate | **day → proper** |
| **Aliturgical Lenten *weekday* feria** (offset ≤ −9, non-Sunday; no proper Liturgy readings) | nothing to combine | **proper only** |

The movable day's readings are taken from the engine's already-validated Easter-core
table (`E` / `EB`), so the composite is computable even for Easter offsets never seen
in 2001–2026 (e.g. **2027**, where Apr 7 = Easter + 10, the 11th day of Eastertide).

> **Completeness, not byte-exactness.** The published calendar liturgically *reduces*
> the day portion in co-celebration — e.g. an Eastertide day contributes only its
> Gospel; a Lenten day drops its trailing vespers set. Which sub-run is Matins vs.
> Liturgy vs. vespers is **not recorded** in any reachable source: sacredtradition.am
> (in every language view) and the reference cache are flat, type-tagged reading lists
> with no service boundaries, and the Tōnats'oyts is the typikon, not a per-movable-day
> service-slotted lectionary (that would need the Ճաշоց). So the engine does **not**
> attempt the reduction. It errs toward a **superset** — a few extra day readings are
> acceptable — and only guarantees it never *drops* a reading the calendar keeps
> (verified: GT ⊆ engine output for every cached Apr-7 collision, 2001–2026).
>
> **Two faithful completeness fixes** (both close a case that previously dropped a key
> reading, without cache-fitting):
> - **Lenten Sunday (2019).** A deep-Lent *Sunday* has a Divine Liturgy, so its readings
>   co-celebrate; only aliturgical *weekdays* leave the proper standing alone. Previously
>   the engine suppressed the whole day and dropped `Luke 21.5-38`.
> - **Eastertide eve (2018).** The eve (April 6, the Նախатонак pre-festive) is celebrated
>   the day before, and in the Easter octave its resurrection Gospel is co-read; the
>   composite appends any eve Gospel the day slot lacks. Previously the engine dropped
>   `John 21.1-14` (the 6th-day-of-Easter Gospel).

### Eastertide eve-Gospel folding is octave-only (source-corrected via page_0487)

The digitized rubric (page_0487) says only that in Eastertide you read the Annunciation
book+Gospel, then *"the Gospel of the day,"* and that *"the Midday and Evening … are of the
Resurrection"* — i.e. the day keeps its own Eastertide readings. It says **nothing** about
re-reading the **eve's** Gospels on April 7. The eve is celebrated on April 6 alone. Folding
the eve Gospels into April 7 is justified **only inside the Easter octave** (offset ≤ +8),
where the octave repeats the feast-day resurrection Gospel. For a **non-octave** Eastertide
year the composite therefore returns `proper ++ day` and takes nothing from the eve
(`_annunciation_composite`, the `e_off >= 1` branch, gated on `e_off <= 8`).

**Empirical validation against the cache** (Apr 7 in non-octave Eastertide):

| Year | Apr 7 offset | GT readings | Engine now | Result |
|---|---|---|---|---|
| 2005 | Easter + 11 | 11 | 11 | **exact match** (byte-for-byte) |
| 2016 | Easter + 11 | 11 | 11 | **exact match** (byte-for-byte) |
| 2008 | Easter + 15 | 11 | 13 | superset-safe (2 extra day readings, 0 dropped) |

The two Easter+11 years reproduce ground truth exactly — confirming that non-octave
Eastertide GT carries **no eve readings** — while the octave path (2018, Easter+6) is
unchanged and still superset-safe. Before this correction the engine folded the eve Gospels
unconditionally, over-reading in every non-octave Eastertide year.

**2027 (Easter + 10, the 11th day of Eastertide, non-octave).** The engine now ships the
reduced 13-reading set `proper(7) ++ day(6)` instead of the earlier 17 (which had 4 spurious
eve Gospels). The true published set is likely ~11 (as in 2005/2016: proper + a ~4-Gospel day
subset); the composite stops at the superset-safe reduction rather than guessing the exact
day-subset, because GT shows that subset varies per-offset in a way the flat `E`/`EB` slot
cannot express (e.g. 2008 keeps its `Acts 9.32-43` but drops a Catholic epistle).
