# The Pre-Lent Martyr Cohort (Sargis · Atom · Sukias · Voskian · Ghevond)

> **Source / provenance:** Տօնացոյց (*Tōnatsʿoyts*), **First Volume, pp. 464–465**, the
> section immediately after the Nativity-octave rubric (see
> [tonatsooyts-nativity-octave.md](tonatsooyts-nativity-octave.md), p. 464). Grabar from
> the page-aligned OCR; pp. 464–465 were captured in the **auto** run
> (`runs/auto__proj__tess__gemini-min/…/translated.md`) — the human-corrected run has a
> gap over these pages — and the Monday/Tuesday entries were **hand-transcribed from the
> grabar** (the auto OCR merged the Monday header onto the Tuesday body).
>
> **Rule governed:** the five fixed martyr feasts of the pre-Lent gap between the Fast of
> Catechumens and the Great Barekendan, and where their readings come from.

---

## Why this section is the answer to a long-standing gap

The Second Volume names these feasts per year-type (taregir) but prints only the feast
title + hymn tone, then cross-refers: **«… see the First Volume up to Vardavar, keeping
the order of this place»** (e.g. Second-Volume lines for St. Sarkis). The referenced
propers live **here**, in the First Volume's own pre-Lent laydown. Because the Second
Volume defers rather than repeats, and because the human OCR run skipped pp. 464–465, the
cohort's readings were long treated as "not in the source." They are — verse for verse.

The feast identities and dates are therefore **source-derived, not fitted to the
sacredtradition.am cache** (the cache remains a test oracle only).

---

## The five propers (as received, First Vol pp. 464–465)

The section lays the cohort on consecutive saint-weekdays after the Barekendan rubric:

| Day | Feast | Old Testament | Prophet | Apostle | Gospel |
|---|---|---|---|---|---|
| **Sat** | **Sargis** the General, his son Martiros & the fourteen soldiers | Prov 3:13-17 | Isa 41:1-3 | Eph 6:10-17 | Luke 21:10-19 |
| **Mon** | **Atom**ian Generals | Wisd 6:12-21 | Isa 18:7 – 19:7 | 2 Cor 4:10 – 5:5 | John 16:1-5 |
| **Tue** | **Sukias**ans (Sukiasian martyrs) | Prov 22:1-12 | Isa 56:6-7 | Heb 11:32-40 | Luke 12:4-8 |
| **Thu** | **Voskian** (Voskeank) priests | Prov 24:1-12 | Jer 30:18-22 | 2 Tim 3:10-12 | Matt 5:1-12 |
| **Tue⁺** | **Ghevond**ian priests | Wisd 5:16-23 | Isa 35:1-2 + 61:6-7 | 1 Pet 1:3-9 | Luke 12:4-10 |

Grabar for the Monday (Atom) and Tuesday (Sukias) entries, hand-transcribed from p. 464
(the two the OCR conflated):

> **Երկուշաբաթ. սրբոց Ատովմեանց զօրավարացն։** … Ճաշու Սաղ. ԽԳ. … Առակ, Իմաս. Զ. 12 … վ. 21
> … Մարգարէ Եսայ. ԺԸ. 7 … վ. ԺԹ. 7 … Առաքեալն, բ. Կորն. Դ. 10 … վ. Ե. 5 … Աւետարան Յովհ.
> ԺԶ. 1 … վ. 5։
>
> **Երեքշաբաթ. սրբոց Սուքիասանց վըկայից։** … Ճաշու Սաղ. ԽԱ. … Առակ. ԻԲ. 1 … վ. 12 …
> Մարգարէ Եսայ. ԾԶ. 6 … վ. 7 … Առաքեալն Եբր. ԺԱ. 32 … վ. 40 … Աւետարան Ղուկ. ԺԲ. 4 … վ. 8։

---

## How the engine uses this (`lectionary.py: _prelent_cohort`)

1. **Placement — fixed Easter offsets.** Each feast sits at a fixed offset from Easter
   (which also fixes its weekday, since Easter−70 is always a Sunday): **Sargis −64 (Sat),
   Atom −62 (Mon), Sukias −61 (Tue), Voskian −59 (Thu), Ghevond −54 (Tue)**.

2. **Displacement — rank-based.** When a higher feast occupies a slot — the transferred
   **John the Forerunner** on Sargis's Saturday (extreme-early-Easter, e.g. 2008) or the
   **Presentation of the Lord (Feb 14)** on a cohort weekday (e.g. 2022) — the senior
   *Generals* (Sargis, Atom) shift forward onto the next cohort slot and **win the merge**;
   the junior martyrs/priests (Sukias, Voskian, Ghevond) are absorbed. On the embedded
   **Presentation-eve (Feb 13)** the feast co-celebrates via the embedded composite, so the
   cohort abstains there. The layout is **drop-guard-validated 0-wrong** over 2001–2026.

3. **Tier.** Served as `Source: "first-volume-cohort"` (a source-authoritative validated
   tier). Because it is source-derived, it carries **forward years that have no cache**.

---

## Source vs. cache: reviewed versification corrections

The verse ranges follow the **source**. On four readings the sacredtradition.am cache uses
a slightly different convention — the pericope is identical:

| Feast | Source | Cache | Nature |
|---|---|---|---|
| Atom | `Wisdom 6.12-21` | `Wisdom 6.11-20` | Wisdom-of-Solomon numbering (source = cache + 1) |
| Atom | `John 16.1-5` | `John 16.1-4` | inclusive/exclusive endpoint (+1) |
| Sukias | `Luke 12.4-8` | `Luke 12.4-9` | inclusive/exclusive endpoint (−1) |
| Ghevond | `Wisdom 5.16-23` | `Wisdom 5.15-22` | Wisdom-of-Solomon numbering (source = cache + 1) |

Sargis and Voskian are byte-identical to the cache. These four are recorded in
`dev/source_corrections.py` and applied **only on cohort-tier days** (the strings
`John 16.1-4` / `Luke 12.4-9` legitimately occur on unrelated feasts — Gayiane, the summer
martyrs, All Saints — where the cache is authoritative and the source itself uses those
very ranges, so the corrections are never applied globally).
