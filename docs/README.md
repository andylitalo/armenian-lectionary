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
| [`sources/tonatsooyts-prelent-cohort.md`](sources/tonatsooyts-prelent-cohort.md) | Տօնացոյց, pp. 464–465 | The pre-Lent martyr cohort (Sargis · Atom · Sukias · Voskian · Ghevond) and its propers, plus the Mark/Pionius canon a week later — source for the `first-volume-cohort` tier and for when that canon is packed onto the Generals' day. |
| [`sources/tonatsooyts-packed-saint-pools.md`](sources/tonatsooyts-packed-saint-pools.md) | Տօնացոյց, pp. 461–462, 526, 556, 574 | When one printed line carries several canons **and when it must not**: preface Sixth's abbreviation warrant and the clause that conditions it, the variable gap that causes packing (p. 526, stated of the autumn interval), and the book unpacking a pair by hand (p. 574). The rule behind `engine._drop_owned_companions`. |
| [`sources/great_paschal_cycle_index.md`](sources/great_paschal_cycle_index.md) | Տօնացոյց, p. 637 | The 532-year year-letter table: Taregir decoded as a **Julian** Easter-date code (closed form in `dev/paschal_index.py`, validated 171/171). Why it is not a Gregorian year-key, and how a Julian source transfers to the Gregorian engine via Easter-offset. |
| [`generative-saint-tier.md`](generative-saint-tier.md) | engine self-scan (no ground truth) | Why `_tier_generative_saint` still exists after `_tier_cycle_saint` superseded its original job — its territory is the complement of `build_table`'s two-year rule and the Second Volume's truncated pages — and the two coordinates it actually serves over the next century, each verified against the validated table. Plus `_tier_fallback`'s out-of-range wins, which are unmodeled gaps. |
| [`observance-name-corrections.md`](observance-name-corrections.md) | sacredtradition.am (English vs. its own Armenian) | Every place the engine deliberately departs from the source's feast text, with the evidence for each — plus the questions still open. Companion to [`dev/observance_name_review.tsv`](../dev/observance_name_review.tsv), the approved-name ground truth. |
| [`sources/second_volume_index.md`](sources/second_volume_index.md) | Տօնացոյց Second Volume, pp. ~555–643 | Per-year-type "Roman cycle" calendars: saint groups (preface §6), the floating-feast list (§7), leap-year rules. Coverage: **42/50** non-validated days (and **22/22** floating saints) are named in the Second Volume. Plus the section→calendar-letter index (`second_volume_index.csv`) and how to verify/label it. |

### Per-year observance tables

[`dev/observance_year_table.py`](../dev/observance_year_table.py) writes
`docs/observance-names-<year>.tsv`: what every day of a year is called, and by which
catalog id — the ids of a day in order, positionally aligned with the English and Armenian
they stand for. It is a reviewing artifact for the id contract, ahead of exposing those ids
downstream; nothing at runtime reads it.

```bash
python dev/observance_year_table.py 2026 2027 --write
```

**No year is checked in yet, deliberately.** Reading the generated 2027 table is what
surfaced the duplicate-commemoration defect
([`observance-name-corrections.md` §7b](observance-name-corrections.md)), and 4 of those
are still open — a table published now would be a table to republish. Generate it when they
are closed.

> **Reading the id columns.** A numeric suffix minted by `--mint` is a **collision counter
> over a truncated slug, not an ordinal**: two different observances whose first four slug
> words agree (e.g. *Third day of the Fast of Nativity* and *Third day of the Fast of
> Advent*, both truncating to `third_day_of_the`) get `_2`, `_3`, … appended in the order
> they were minted, saying only which claimant got there first. The ids that shipped this
> way (`third_day_of_the_4`, `third_day_of_the_2`, …) have since been hand-renamed to
> descriptive ones (`nativity_fast_day_3`, `advent_fast_day_3`, …), but a fresh collision
> mints the same unhelpful way — read the `en` column beside an unfamiliar id, never the
> slug, and rename it by hand in `dev/observance_name_review.tsv` before it ships further.

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
