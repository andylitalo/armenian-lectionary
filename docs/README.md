# Lectionary documentation

Primary-source rubrics and liturgical rules behind the Armenian lectionary engine.

The engine (`lectionary.py`) reproduces the Armenian Church's readings by *algorithm*,
but the algorithm encodes rules that originate in the authoritative liturgical books —
chiefly the **Տօնացոյց** (*Tōnats'oyts'*, the Calendar/Typikon) and the **Ճաշոց**
(*Chashots*, the Lectionary). This directory preserves the relevant primary-source
passages, with provenance, so each modeling decision can be traced back to the rubric
that governs it.

## Contents

| File | Source | What it governs |
|------|--------|-----------------|
| [`sources/tonatsooyts-annunciation-canon.md`](sources/tonatsooyts-annunciation-canon.md) | Տօնացոյց, pp. 486–488 | The Annunciation (Apr 7) + its eve (Apr 6): the deterministic collision rule by which the feast's readings combine with the movable Lent / Holy Week / Eastertide day it lands on. |
| [`sources/tonatsooyts-fast-suppression.md`](sources/tonatsooyts-fast-suppression.md) | Տօնացոյց, pp. 512, 519, 549 | "No feasts are held" during the Fasts of the Transfiguration, the Assumption, and the Nativity/Theophany — justifies cutting the summer/autumn saint zones at the fast boundary. |
| [`sources/tonatsooyts-nativity-octave.md`](sources/tonatsooyts-nativity-octave.md) | Տօնացոյց, p. 464 | The Nativity octave (Jan 6→13) and its 1–2-day encroachment on the following fast by Dominical letter — the principle behind the Jan-13 / Eve-of-Fast collision (`PnOct`). |
| [`sources/tonatsooyts-low-sunday-antasdan.md`](sources/tonatsooyts-low-sunday-antasdan.md) | Տօնացոյց, pp. 487, 462–463 | Low Sunday (Easter+7) and its Antasdan (Blessing of the Fields) four-corners Gospels — source for the validated `E` reading-block. |
| [`sources/tonatsooyts-eastertide-gospels.md`](sources/tonatsooyts-eastertide-gospels.md) | Տօնացոյց, p. 488 | The Eastertide four-Gospel continua (Luke·John·Matthew·Mark, Easter+8→Pentecost) — confirms the validated `E`/`EB` Eastertide output. |

> **Citation convention.** Each canon quotes the English (`gemini-flash` translation,
> `translated.md`) immediately followed by the page-aligned grabar (classical Armenian)
> from `grabar-ocr/.../merged.md`, so a reviewer can check the translation against the
> source. Page numbers refer to the Տօնացոյց and are shared by both texts.
>
> **Scope of the 2026 Տօնացոյց-resolution pass.** The four canons above were the
> "low-hanging fruit" — ambiguities for which the *available* partial translation
> contains **all** the needed rules. Ambiguities still blocked on untranslated pages
> are logged as deferred in [`../reports/residual_estimate_tail.md`](../reports/residual_estimate_tail.md)
> (§ "Deferred — pending Տօնացոյց translation"). Three of the four turned out
> *confirmatory* (the engine already encoded the rule); their value is the
> primary-source justification for defending the algorithm to Church authorities.

## Why these matter to the engine

A passage is recorded here when it explains an otherwise-opaque modeling rule —
especially the "embedded irregular feasts" whose readings *looked* unpredictable to a
cross-year statistical build but are in fact prescribed by a rubric. The Annunciation
canon is the first such case: it turns the single largest residual block of
`algorithmic-estimate` days (Apr 7 + Apr 6, ~55 days in the 2001–2026 cache) into a
computable **composite** — see `lectionary.py` (`_annunciation_composite`) and the
audit in `reports/certainty_2027.md`.
