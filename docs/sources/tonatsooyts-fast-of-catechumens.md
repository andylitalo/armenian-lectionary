# The Fast of the Catechumens (Առաջաւորաց պահք) — an aliturgical week

> **Source / provenance:** Տօնացոյց (*Tōnatsʿoyts*), **First Volume** — the pre-Lent
> section around **pp. 462–465** (the Barekendan eve proper on p. 462, the Nativity-octave /
> fast-boundary rubric on p. 464; see
> [tonatsooyts-nativity-octave.md](tonatsooyts-nativity-octave.md) and
> [tonatsooyts-prelent-cohort.md](tonatsooyts-prelent-cohort.md)).
>
> **Rule governed:** why the four ferial days of the Fast of the Catechumens carry **no
> scripture readings**, and how the engine/API must present that emptiness.

---

## The fast is a penitential week without a Divine Liturgy

The Fast of the Catechumens (Առաջաւորաց / *Aṙaǰawor*) is a fixed five-day fast in the
pre-Lent interval, opened by its **Barekendan eve Sunday at Easter − 70**. Its weekday
course is:

| Civil position | Easter offset | Day | Liturgy? | Readings |
|---|---|---|---|---|
| Barekendan eve | −70 | **Sunday** | yes | proper (First Vol p. 462) |
| First day | **−69** | **Monday** | **no** | **none** |
| Second day | **−68** | **Tuesday** | **no** | **none** |
| Third day | **−67** | **Wednesday** | **no** | **none** |
| Fourth day | **−66** | **Thursday** | **no** | **none** |
| Fifth day | −65 | Friday | yes | Jonah (the fast's one lection) |

Monday–Thursday are kept **aliturgically** — a strict penitential fast with no Eucharistic
synaxis, hence **no appointed lectionary readings**. This is not a gap in the source or the
digitization; the Tōnats'oyts simply appoints nothing there. The Friday resumes with the
book of Jonah, and the eve Sunday and the surrounding pre-Lent martyr cohort
([tonatsooyts-prelent-cohort.md](tonatsooyts-prelent-cohort.md)) carry their own propers.

The ground-truth oracle (sacredtradition.am) agrees: it returns these days with a feast
label (`"First … Fourth day of the Fast of the Catechumens"`) and an **empty** reading set.

---

## How the engine / API presents this (`lectionary.py`)

These four days resolve through the **`validated-table`** tier with an **empty**
`ReadingsList`. Because an empty reading set could be misread as "not yet modeled," the
engine attaches an explicit signal so consumers treat the emptiness as a validated fact:

```json
{
  "Liturgical Day": "First day of the Fast of the Catechumens",
  "Season": "Pre-Lent",
  "ReadingsList": [],
  "Source": "validated-table",
  "Confidence": "validated",
  "Note": "No scripture readings are appointed for this day; it is kept as a penitential
           fast without a Divine Liturgy (an aliturgical day … the ferial days of the Fast
           of the Catechumens). The empty reading set is intentional and validated against
           the Tōnats'oyts, not missing data."
}
```

Any `validated-table` response with an empty `ReadingsList` carries this
`Confidence: "validated"` + aliturgical `Note`. Over 2001–2027 the **only** such days are
these four ferial days each year (Easter offsets −69…−66); there are no "withheld" or
unmodeled empties. A day with genuinely unresolved readings would instead surface under a
best-guess tier or the `algorithmic-estimate` fallback, never as `validated-table`.
