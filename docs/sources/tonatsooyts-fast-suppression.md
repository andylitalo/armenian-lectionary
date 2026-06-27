# Canon of the Penitential Fasts: "No Feasts Are Held"

> **Source / provenance:** Տօնացոյց (*Tōnats'oyts'*, the Armenian Church
> Calendar/Typikon). Three parallel rubrics, one closing each of the major
> penitential fasts: the **Fast of the Transfiguration** (Vardavar) — **p. 512**;
> the **Fast of the Assumption** of the Theotokos — **p. 519**; and the **Fast of
> the Nativity and Theophany** — **p. 549**. English from the project's
> `gemini-flash` translation (`translated.md`); grabar (classical Armenian) from the
> page-aligned OCR (`grabar-ocr/.../merged.md`).
>
> **Rule governed:** which days inside a fast carry a *saint's* commemoration (and
> hence a saint's reading-set) versus which are purely ferial.

---

## The rubric (as received)

**Fast of the Transfiguration (Vardavar) — p. 512.** Closing the Eve (the Sixth
Sunday after Pentecost):

> "… And then the Fast of the Transfiguration [Vardavar] begins, but **no feasts are
> held**."

Grabar (p. 512): «Եւ ապա պահ Վարդավառի, բայց **տօնք ոչ լինին**։»

**Fast of the Assumption — p. 519.** Closing the Eve of the Assumption fast:

> "… And then the Fast of the Assumption of the Holy Mother of God, **during which
> there are no feasts**."

Grabar (p. 519): «Եւ ապա պահք Վերափոխման սրբուհւոյ Աստուածածնին, յորում **տօնք
ոչ գոն**։»

**Fast of the Nativity and Theophany — p. 549.** Closing the run-up to Theophany:

> "… And then begins the Fast of the Nativity and Theophany of Christ our God, and
> **no feasts are celebrated**."

Grabar (p. 549): «Եւ ապա պահք Ծննդեան և Յայտնութեանն Քրիստոսի Աստուծոյ մերոյ. և
**տօնք ոչ լինին**։»

The three phrasings — *տօնք ոչ լինին* / *տօնք ոչ գոն* ("feasts are not held / do
not exist") — are interchangeable; the rule is the same in all three fasts.

---

## How the engine uses this rubric

The lectionary engine learns its readings from a cross-year-consistent statistical
build under a **0-wrong contract**. The hardest residual block is the *variable-gap
hinge zones*, where saints are laid in a canonical order onto the free
Mon/Tue/Thu/Sat slots between two governing feasts, and a single saint's
merge/drop shifts every downstream day onto a different key. The "no feasts"
rubric **bounds those zones**: a fast window contains *no* floating saint, so it
carries no saint coordinate at all — every day there is ferial and resolves through
the plain Easter-/solar-anchored keyspaces.

The engine already encodes exactly this. In `lectionary.py`:

- `_hinge_anchors` computes `AS_FAST_MON = Assumption_Sunday − 6` and
  `EX_FAST_MON = Exaltation_Sunday − 6`, and the saint zones terminate **one day
  before** the fast begins: `SUMMER_EVE = AS_FAST_MON − 1`,
  `AUTUMN_EVE = EX_FAST_MON − 1`.
- `_hinge_coords_raw` emits the summer (`Tr…`) grid only for `TR < d ≤ SUMMER_EVE`
  and the autumn (`As…`) grid only for `AS < d ≤ AUTUMN_EVE`. The Fast of the
  Assumption and the Fast of the Holy Cross therefore receive **no** `*Saint*` /
  `*Sat*` coordinate.

Verified over the 2014–2026 eval window: for every day inside the Fast of the
Assumption and the Fast of the Holy Cross, `coords_for` emits **zero** saint keys;
the days resolve through the generic `EB` / `AS` / `EX` anchored tables — i.e. as
pure ferial days, precisely as the rubric requires. (The lone Sep 8 exception is the
*Nativity of the Theotokos*, a fixed Marian feast resolved by its own embedded
composite, not a floating saint — it does not contradict the rule.)

| Fast | Window (computed) | Saint coordinates emitted | Resolves via |
|---|---|---|---|
| **Transfiguration (Vardavar)** | the week up to Vardavar = Easter + 98 | none (inside Easter core) | `EB` / `E` |
| **Assumption** | `AS_FAST_MON … Assumption − 1` | **none** (zone ends at `SUMMER_EVE`) | `EB` / `AS` |
| **Nativity / Theophany** | the strict fast before Jan 6 | none laid by the winter grid here | `EB` / `HEp` |

**Code impact this round:** *confirmatory — no change.* The rule was previously
inferred empirically (the hinge zones were cut at the fast boundary because the data
showed no saint there); this canon supplies the **primary-source justification** for
that boundary, which is the load-bearing fact when defending the zone cut-offs to a
skeptical reviewer.

---

## Residual subtleties

1. **Transfiguration & Holy-Cross fasts fall inside already-validated cycles.** The
   Vardavar fast sits in the Easter core (`E`/`EB`) and the Holy-Cross fast in the
   Exaltation cycle (`EX`); both already ship validated, so the rubric here only
   *confirms* there is no saint to disturb them.
2. **The exact bound of the "Fast of the Nativity and Theophany" is not fully fixed
   by the available translation.** The rubric states the principle, but the precise
   first day of this strict fast (as distinct from the long Advent/Heesnak fast,
   during which the winter grid *does* lay saints) depends on rubrics in the
   untranslated pages. The engine's winter Advent grid is therefore left unchanged;
   tightening the strict-fast boundary is deferred (see
   `reports/residual_estimate_tail.md`).
