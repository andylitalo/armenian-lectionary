# Canon of the Annunciation to the Holy Virgin Mary

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*, the Armenian Church
> Calendar/Typikon), **pp. 482–483**. Transcribed/translated text supplied by the
> project owner. One inline page break ("Page 487") appears in the received text and
> is preserved below as it was given.
>
> **Feast:** Annunciation to the Theotokos — fixed date **April 7** (eve **April 6**,
> the Նախատօնակ / pre-festive). Celebrated for **seven days**.

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
| **Yinants / Eastertide (≥ +1)** | "the Psalms, Scriptures, and Gospels are of the Resurrection … read the Gospel of the day after the Annunciation book and Gospel" | **proper → day** |
| **Lenten Sunday with its own readings** (e.g. the Sunday of the Coming) | the day has a Liturgy, so its readings co-celebrate | **day → proper** |
| **Aliturgical Lenten weekday** (no proper Liturgy readings) | nothing to combine | **proper only** |

The movable day's readings are taken from the engine's already-validated Easter-core
table (`E` / `EB`), so the composite is computable even for Easter offsets never seen
in 2001–2026 (e.g. **2027**, where Apr 7 = Easter + 10, the 11th day of Eastertide).

> **Residual subtleties not fully fixed by this rubric:** (1) the exact concatenation
> on the supreme days where the day's office dominates, and (2) the **eve, April 6**
> (Նախատօնակ), which the data shows largely takes the *day's own* readings — the
> pre-festive does not override them — consistent with the rubric's "perform the
> Pre-festive service after the proper office of the day."
