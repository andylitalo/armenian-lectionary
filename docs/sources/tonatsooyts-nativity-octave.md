# Canon of the Nativity Octave and Its Encroachment on the Fast

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*), **p. 464**. English from the
> `gemini-flash` translation; grabar from the page-aligned OCR
> (`grabar-ocr/.../merged.md`, page_0464).
>
> **Rule governed:** how far the eight-day octave of the Nativity/Theophany (Jan 6 →
> Jan 13) extends, and how the boundary between the octave and the following fast
> moves with the **Dominical letter** (letter of the year).

---

## The rubric (as received)

> "Again, know this: that when the letter of the year is 'Alis' [letter **Ա**], the
> eight-day octave of the Nativity of Christ **takes two days from the fast**. And if
> the letter of the year is 'E' [letter **Ը**], it **takes one day from the fast**,
> during which, although the feast of the Nativity is celebrated with services and
> Liturgy, yet the fast is **unbreakable**. Furthermore, from here until the Great
> Barekendan [Pre-Lenten Sunday], although feasts are set as immovable, yet you must
> not let the annual calendar out of your hands."

Grabar (p. 464): «… զի յորժամ գիր տարւոյն **Ա**լինիցի, ութօրեակ Ծննդեան Քրիստոսի
**զերկու օրն ի պահոցս առնու**. եւ թէ **Ը** լինիցի գիր տարւոյն **զմի օր առնու ի
պահոցս**, յորս թէպէտ պաշտամամբ և պատարագօք Ծննդեան տօն կատարին. **բայց պահք են
անլուծանելի**։ Այլ եւ աստի մինչեւ ՚ի Բուն բարեկենդանն՝ թէպէտ դնին տօնք որպէս
անշարժմք, սակայն դու **զտարեգիրն ի ձեռաց մի թողուր**։»

---

## How the engine uses this rubric

Two facts are encoded here:

1. **The octave is a fixed eight-day unit (Jan 6 → Jan 13) with cross-year-invariant
   proper readings.** The eighth day, **Jan 13** (the Naming/Octave of the Nativity),
   carries the same proper every year and is given a dedicated constant key in
   `coords_for`:

   ```python
   if md == (1, 13) and e_off != -70:
       cs["PnOct"] = "01-13"
   ```

   The `e_off != -70` guard is the one exception below.

2. **The octave/fast boundary is *not* purely solar — it shifts with the Dominical
   letter.** In a year of letter Ա the octave reaches two days into the following
   fast; in a year of letter Ը, one day; and the fast itself is never broken
   regardless. This is the rubric's reason for the closing warning — *"do not let the
   annual calendar out of your hands"* — i.e. the boundary must be read off the
   year-letter, not assumed fixed.

This is exactly the mechanism behind the **Jan 13 / Eve-of-the-Fast-of-Catechumens
collision**. In a rare extreme-Easter year the movable Eve of the Fast of Catechumens
(Easter − 70) lands on Jan 13 and the octave *co-celebrates* with the eve. The constant
`PnOct` key is withheld precisely when `e_off == -70` (so the plain octave ships for
every normal year), and the collision year is instead resolved by a dedicated
composite. The rubric supplies the underlying principle: the boundary between the
*octave count* and the *fast count* is governed by the year-letter, so the two counts
can coincide on the same civil date in different years.

**Code impact (2026-07-05): two January days recovered from BLANK.** In the one cached
extreme-early-Easter year (2008, Easter Mar 23 → eve of the Fast of Catechumens on
Jan 13), the winter grid's post-Nativity window `(Jan 14 … eve)` is *empty* — Jan 14 is
already inside the fast — so its `PnJohn` and octave slots never fire and both days blanked.
Two compute-level composites now serve them (`_john_forerunner_composite`,
`_nativity_octave_composite` in `lectionary.py`), both grounded on this page's rubric that
the octave/fast boundary tracks Easter:

- **Jan 19 — Nativity of John the Forerunner** (nominal **Jan 14**), transferred out of the
  aliturgical fast week to the first saint-weekday after it. The transfer date is pure
  Easter-anchored calendar math and the readings are the cross-year-validated `PnJohn`
  proper, so the day ships **byte-exact** (`validated-composite`; exact vs GT).
- **Jan 13 — octave/eve co-celebration.** Both feasts are kept "with services and Liturgy"
  (p. 464), so the day combines the octave proper with the eve's validated Liturgy. The flat
  slots carry no Matins/Liturgy structure, so *which* portion the printed calendar reduces
  is not derivable; like the Annunciation composite this errs toward a **completeness
  superset** (GT ⊆ output; `generative-composite`, best-guess) rather than a byte-exact
  claim from a single sample.

Byte-exactness for Jan 13 still awaits the **Dominical-letter** refinement (the Ա/Ը
encroachment count), whose derivation lives in the Տօնացոյց's 532-year Paschal tables
(pp. ~538–641) — present in the OCR but not yet translated — and the First-Volume
Matins/Liturgy structure. Until then the superset is the honest ceiling.

---

## Residual subtleties

1. **Year-letter machinery is the blocker, not the rule.** The encroachment rule is
   fully stated and unambiguous; only the letter-of-the-year lookup is missing in
   translated form. Once the Paschal-table application is translated, the octave-tail
   days (Jan 13–15) could be sub-keyed by year-letter to separate the Ա/Ը years
   cleanly — a future, additive, 0-wrong-safe change.
2. **The single observed collision (Easter − 70 on Jan 13) is now served by a superset
   composite**, and the fast-displaced John (Jan 19) is byte-exact; no day ships wrong.
   The year-letter refinement would tighten Jan 13 from superset to byte-exact — an
   accuracy/justification improvement, not a correctness fix.
