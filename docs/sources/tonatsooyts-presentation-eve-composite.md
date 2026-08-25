# Presentation-eve (Feb 13) collision composite

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*, the Armenian Church
> Calendar/Typikon), **p. 462** — the canon "Of the Forty-Day Coming of Christ our God
> into the Temple" (Candlemas / Տեառնընդառաջ), whose rubric states the feast is "always
> celebrated ... on February 14" and lays out an eve office for "the 13th day of
> February, in the evening."
>
> **Digitized text:** auto-OCR'd in the `grabar-ocr` pipeline —
> `runs/auto__proj__tess__gemini-min/pages/page_0462_auto.lines.json`
> (Tesseract + Gemini minimal-edit), with the English reading in the same run's
> `translations/gemini/`; also mirrored at `corpus/pages/page_0462.md`. Not yet
> promoted to a `human__*` gold run.

## What the page actually settles

p.462's eve office is stated unconditionally — "always... February 14," eve service on
"the 13th day" — with no stated exception for what the day's *own* proper is. The page
lists the eve block's own six readings in order:

> Leviticus 12.6-8 · Proverbs 8.22-24(-34) · Ezekiel 44.1-2 · Malachi 3.1-4 ·
> Galatians 3.24-29 · Luke 2.22-40

— which is exactly `engine._PRESENTATION_EVE_BLOCK`, byte for byte (the Proverbs upper
bound is transcribed `24` here against the engine's `34`; not resolved further, since it
does not affect which verses are *included*, only where the auto-OCR line break fell).

It does **not** say anything about how this composes with a day that already has its own
proper (a Lenten weekday, a saint) — that combination rule is
`engine._presentation_eve_composite`'s own construction (base proper ++ this block),
documented at the composite's definition, not stated on this page. p.462 is warrant for
*what the eve block itself contains*, not for the composition rule.

## The single-sample problem, and its resolution for 2027-02-13

`_presentation_eve_composite` is the **best-guess** fallback for an Easter offset the
strict, cross-year-validated `PrLE` keyspace cannot cover — i.e. an offset appearing in
no other year of the 2001–2027 supported range, so the strict learner has nothing to
cross-check it against.

**2027 is not actually alone.** 2027-02-13 is Easter+(-43) (Gregorian Easter 2027-03-28);
**2016-02-13 is the same offset** (Easter 2016-03-27, also -43) and carries the identical
served name, `"Sixth day of Great Lent — St. Theodore the Tyron"`. 2016 is inside the
ground-truth range, and `dev/reference_data/2016-02-13.json` (sacredtradition.am) reads:

```
"feast": "Sixth day of Great Lent — Saint Theodore the General",
"readings": [
  "Wisdom 8.19-9.5", "Isaiah 62.6-9",
  "St. Paul's Epistle to the Romans 8.28-39", "Matthew 10.16-22",
  "Leviticus 12.6-8", "Proverbs 8.22-34", "Ezekiel 44.1-2", "Malach 3.1-4",
  "St. Paul's Epistle to the Galatians 3.24-29", "Luke 2.22-40"
]
```

`compute_armenian_lectionary(2016-02-13)` reproduces this **exactly** — same 10 readings,
same order (the one difference, `Malach` vs `Malachi`, is the source's own typo, already
normalized on the engine side; "the General" vs "the Tyron" is the same
`dev/source_corrections`-registered spelling fold applied everywhere else that name
occurs). Both 2016 and 2027 stay tagged `generative-composite`/`best-guess` — the strict
`PrLE` builder still requires **two** cross-validating cache years at the same offset to
promote a coordinate, and 2016 is the only cache year at offset -43, so one exact match is
support, not statistical proof. But it is now a **direct, checked precedent** rather than
an abstract citation to the general rule: the same composite construction, on the nearest
available same-offset year, ships what was actually published, with zero readings dropped
and zero extra.

## Bottom line for 2027-02-13

- **Name** — `"Sixth day of Great Lent — St. Theodore the Tyron"` — is validated-table
  text (recurs identically across 7 other cache years at other offsets); not in question.
- **Readings** — the `generative-composite` best-guess is now backed by an exact match at
  the one available same-offset analog (2016), on top of the general p.462 citation for
  the eve block's own contents. `Source`/`Confidence` stay honest (`generative-composite`
  / `best-guess`) because a single analog is not the two-year cross-validation the strict
  tier requires — but the best-guess is no longer merely plausible, it is checked.
