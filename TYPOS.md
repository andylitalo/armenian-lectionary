# Տօնացոյց (Tōnatsooyts) — Source Typos & Errata

A registry of **confirmed typographical errors** in the printed Տօնացոյց
(*Tōnatsooyts*, the Armenian Church Calendar/Typikon) that this engine digitizes and
validates against. The governing principle (see `dev/source_corrections.py`) is that the
printed source is authoritative and sacredtradition.am is a test oracle — but a genuine
*typo* in the source is not authoritative. Each entry records the location, what the
source prints, the correct value, and the evidence. Where a typo would yield a wrong
reading, the engine ships the **corrected** value.

This is distinct from `dev/source_corrections.py`, which records systematic
*versification-convention* differences (the same pericope numbered on a different scale).
The entries here are outright errors in the printed text.

---

## 1. Proverbs 8 endpoint — Eve of the Presentation of the Lord (Feb 13), First Volume p. 462

| | |
|---|---|
| **Source prints** | `Առակ. Ը. 22 … վ. 24` — "Proverbs 8:22 … to verse 24", endpoint quoted «որ զճանապարհս իմ պահիցէ» |
| **Correct** | **`Proverbs 8:22-34`** |
| **Classification** | Transposed digit — printed `24`, should be `34` |
| **Engine behavior** | Ships `Proverbs 8.22-34` (`_PRESENTATION_EVE_BLOCK` in `lectionary.py`); already correct, no override needed |

**Why it is a typo, not a versification variant.** The Տօնացոյց cites the reading's
endpoint by quoting its closing words: «...որ զճանապարհս իմ **պահիցէ**» ("...who keeps my
ways"). In the Grabar (Classical Armenian) Proverbs, that phrase is verbatim the close of
**verse 34**, not verse 24:

- **8:24** — «Նախ քան զանդունդս գործել, նախ քան զբղխել աղբերաց ջրոց» — *"When there were no
  depths, I was brought forth; when there were no fountains abounding with water"* — has
  nothing to do with "keeping [my] ways".
- **8:32** — «Արդ, որդեակ, լուր ինձ. եւ երանելի են՝ որ զճանապարհս իմ **պահեսցեն**» — *"Now
  therefore hearken unto me... blessed are they that keep my ways"* — near-identical, but
  uses the **plural** «պահեսցեն».
- **8:34** — «Երանելի է այր որ լուիցէ ինձ, եւ մարդ որ զճանապարհս իմ **պահիցէ**, տքնիցի առ
  դրունս իմ հանապազ...» — *"Blessed is the man that heareth me... that keepeth my ways,
  watching daily at my gates..."* — the **singular** «պահիցէ» matches the Տօնացոյց's quoted
  endpoint **exactly**.

The singular verb form «պահիցէ» disambiguates against the 8:32 twin and fixes the endpoint
at **8:34**. So the pericope is `8:22-34`; the printed verse number "24" is a
`3`→`2` transposition.

**Independent cross-check.** sacredtradition.am renders this reading `Proverbs 8:22-34`
unanimously — **23/23** Feb-13 eve years and **26/26** Feb-14 (Presentation feast) years in
the reference cache. The Grabar Proverbs 8 source consulted:
<https://arak29.org/bible/book/tProv_8.htm>.

**History.** Initially mis-read (by this project) as an OCR error, then investigated as a
possible short-pericope versification variant, and finally confirmed as a printed-source
typo by the maintainer via the Grabar endpoint text. See the README "Source fidelity &
known typos" section.
