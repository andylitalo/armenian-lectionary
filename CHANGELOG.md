# Changelog

All notable changes to **armenian-lectionary** are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [1.2.3] — 2026-07-23

### Fixed
- **Reformed ("Soviet") orthography in three `hy` names.** The `language="hy"` maps carried a
  few reformed-orthography spellings the traditional (Mashtots) contract should have caught.
  Two book names slipped through `dev/fetch_translations.to_mashtots` because its reversal
  tables had no rule that fired on them — `Numbers` shipped as `Թվեր` (want `Թիւեր`) and
  `Deuteronomy` as `Երկրորդ օրենք` (want `Երկրորդ օրէնք`, `ե→է`). One feast title carried a lone
  reform slip the source typed into otherwise-traditional text — the Abgar commemoration's
  `հավատացեալ` (want `հաւատացեալ`, `ավ→աւ`); feast titles bypass `to_mashtots`, so this was
  folded by a new targeted `fix_feast_orthography` step rather than a blanket `/aw/` reversal
  (which would corrupt the genuine consonant `վ` in `Վարդավառ`, `զօրավար`, `նախավկայ`). The
  shipped `book_names_hy.json`/`feast_names_hy.json` carry the corrected forms, the dev
  reversal tables reproduce them on a re-scrape, and the orthography contract test
  (`tests/test_language.py::test_books_use_mashtots_orthography`) is tightened with an
  `օրենք` guard and a general vew (`վ`) check so a reformed book name can no longer ship
  unnoticed. English keys, dates, reading content, and feast wording are unchanged.

## [1.2.2] — 2026-07-22

### Fixed
- **Malachi book-name typo.** The source truncated the book name on the Presentation-eve
  (Feb 13) block, shipping `Malach 3.1-4` where Malachi 3:1-4 (Մաղաքիա) is meant — the same
  book the source and this engine spell `Malachi` on every other day it appears. The engine
  now serves the canonical `Malachi 3.1-4` everywhere: the hardcoded generative block
  (`engine._PRESENTATION_EVE_BLOCK`) and the shipped `lectionary_data.json` carry the fixed
  spelling directly, and the stale `Malach` key was dropped from the `hy` book-name map (its
  `Malachi` twin already mapped to the same Armenian name, so `language="hy"` still localizes
  the reading). The fold is registered as `dev/source_corrections.apply_book_name_fixes` and
  applied by every `reference_data` reader (`apply_source_corrections`), so the built table
  and `hy` map rebuild with `Malachi` and the ground-truth oracle scores the corrected output
  as a hit (0-wrong contract preserved). No date, reading-content, or feast wording changes.
- **English feast-name misspellings.** The source shipped a family of plain misspellings in the
  English feast text, uniformly its modal spelling and thus surfaced verbatim in the
  `"Liturgical Day"` output: `Staint`→`Saint`, `Theordore`→`Theodore`,
  `Transifiguration`→`Transfiguration`, `Grogoris`→`Grigoris`, `Marcarius`→`Macarius`,
  `Hermongenes`→`Hermogenes`, and in the Eugenios cluster `Alerius`→`Valerius`,
  `Canditus`→`Candidus`, `Eugraphius`→`Eugraphus` (the last three confirmed by the engine's own
  saint id and Armenian rendering). They are folded by the new
  `dev/source_corrections.normalize_feast_spelling`, applied in `apply_source_corrections` (so the
  shipped `lectionary_data.json`, `saint_schedule.json`, and `feast_names_hy.json` rebuild with the
  corrected names) and in `canonical_commem` (so the feast-name test compares like-for-like); the
  three shipped artifacts carry the corrected spelling directly. Also dropped now-redundant
  duplicate keys from the `hy` feast map (the stale `Fiest of …` typo twins of `Feast of …`, and a
  `Hermongenes/Eugraphius` twin). Deliberate name-*variants* (`Phillip`, `Nicolas`, `Zachariah`,
  `Eugenios`, `Simeon`, `Sargius`) are left untouched. No date or reading changes.

## [1.2.1] — 2026-07-22

### Fixed
- **Confusable characters in English feast names.** The source typed a few English feast
  strings with wrong-code-point look-alikes: Cyrillic letters (Cyrillic `Е` in `Eighth day
  of Nativity`, Cyrillic `о` in `…Tatoul…`, from a Cyrillic keyboard) and a curly apostrophe
  (`’`, U+2019) in two possessives (`…St. Mary’s Box`, `…Illuminator’s Commitment…`) where
  every other name uses the ASCII `'`. These had propagated into the shipped English table
  (`lectionary_data.json`) and thus into the `"Liturgical Day"` output, so the text looked
  correct but carried the wrong code points. They are now folded to their canonical twins by
  `dev/source_corrections.normalize_confusables()`, applied at scrape ingestion
  (`dev/fetch_reference.py`) and symmetrically inside `canonical_commem`; the shipped `hy`
  feast-map keys are cleaned in lockstep so those feasts still translate (this also restores
  the map to sorted/reproducible order). No reading, date, or feast wording changes.
- **Build-time guard against future contaminants.** The fold above is a narrow, observed-only
  *fixer*. Backing it is a positive *detector*, `dev/source_corrections.unexpected_chars()`,
  which validates feast/book text against the legitimate character set (ASCII ∪ Armenian
  block ∪ Armenian ligatures ∪ the em-dash `FEAST_SEP`). It is asserted at both build steps
  (`dev/build_table.export_table` for `lectionary_data.json`; `dev/fetch_translations.build`
  for the `hy` maps, keys **and** values) and over the shipped artifacts in the tests — so a
  new look-alike fails the build loudly (and gets added to the fold map) instead of shipping.

### Changed
- **Read-time source corrections consolidated.** The on-read corrections (Easter reading-order
  fix + confusable fold) now live in one helper, `dev/source_corrections.apply_source_corrections()`,
  used by every `reference_data` reader (`dev/analyze.load_all`, `dev/fetch_translations`),
  replacing several ad-hoc call sites. Also fixed a `dev/fetch_reference.py` import
  inconsistency (now uses the same `sys.path` bootstrap + `dev.source_corrections` import as
  its sibling tools) and a file-handle leak in the feast tests.

## [1.2.0] — 2026-07-22

### Added
- **Armenian (`hy`) output.** `compute_armenian_lectionary(date, language="hy")` (and
  `GET /readings?date=…&language=hy`, and `armenian-lectionary --language hy`) now returns
  the feast (`"Liturgical Day"`) and the scripture book names in Classical Armenian.
  `language` defaults to `"en"`; an unsupported value raises `ValueError` (HTTP 400 in the
  API). Provenance fields (`Season`, `Source`, `Confidence`, `Note`) stay in English — they
  are engine annotations, not scraped source data. Every result now carries a
  `"Language"` key (`"en"` or `"hy"`) naming the language of its names. Any feast
  component or book with no known Armenian form is left in English rather than dropped.
- The names ship as two static maps under `armenian_lectionary/data/`
  (`feast_names_hy.json`, `book_names_hy.json`), so the runtime stays fully offline. They are
  scraped once from sacredtradition.am (`iL=0`, Classical Armenian) by the new dev tool
  `dev/fetch_translations.py`, which pairs each English reading with its Armenian counterpart
  by matching the language-independent `chapter.verse` tail and votes the most common
  rendering per feast/book (including per-`FEAST_SEP`-component feast votes so
  engine-composed labels translate too).
- **Traditional (Mashtots) orthography.** The source enters feast titles in Mashtots
  orthography but the book/reading names in Modern-Eastern reformed ("Soviet"/Abeghyan)
  orthography; `dev/fetch_translations.py` reverses the reform on the book names
  (orthography only, preserving the source's words) — e.g. `Ավետարան ըստ Հովհաննեսի` →
  `Աւետարան ըստ Յովհաննէսի`, `…մարգարեությունը` → `…մարգարէութիւնը`. A data-contract test
  guards that both shipped maps are pure Armenian script (no Cyrillic/Latin lookalikes) and
  that the book names carry no reformed markers.

## [1.1.1] — 2026-07-22

### Fixed
- **Feast names no longer run their components together.** The source packs a day's
  calendar-position label, commemoration, and any eve/status note into one field separated
  by `<br>`; the reference fetcher (`dev/fetch_reference.py`) was stripping every tag —
  including `<br>` — to the empty string, mashing them (e.g.
  `Twentieth day of EastertideRemembrance of the Armenian Genocide (1915)`). The fetcher now
  preserves the `<br>` boundary as a ` — ` separator, so the whole pipeline — the ground-truth
  cache, the shipped tables, and the `"Liturgical Day"` output — carries the components
  already split. Example: `Twentieth day of Eastertide — Remembrance of the Armenian Genocide
  (1915)`.

### Changed
- The engine now serves these authoritatively-delimited names directly and composes the
  April-24 Genocide Remembrance note and the Annunciation-collision names on the real
  separator. The previous approach re-derived the component boundary at runtime from a
  position-label vocabulary; that reverse-engineering is **removed** (the boundary comes
  from the source now, not a regex).

Readings are unaffected (one Easter-Sunday reading-order outlier in the source, 2011-04-24,
is normalized to the cross-year consensus so the shipped tables rebuild identically). The
0-wrong readings contract and the 100%-match feast-name contract both still hold.

## [1.1.0] — 2026-07-19

### Added
- **Feast-name accuracy contract.** The `"Liturgical Day"` feast/fast name — returned
  by `compute_armenian_lectionary(...)` and the web `/readings` endpoint — is now a
  supported, source-matched output. The new `tests/test_feast.py` suite locks the
  engine's commemoration against the authoritative ground truth on **all 9,495 days of
  2001–2026 (100% match, no allowlist, no exceptions)**. See the README "Feast-name
  accuracy" section; audit with `python dev/feast_audit.py`.

### Fixed
- Aligned engine feast names to the source wording: the pre-Lent martyr cohort labels
  (Sargis / Atom / Sukias / Voskian / Ghevond) and the embedded Marian / Forerunner /
  Naming / Annunciation composites.
- **Remembrance of the Armenian Genocide (1915)** re-anchored to its fixed civil date
  (April 24); the Easter-keyed table had let the note float onto the wrong day.
- **Fixed/movable collision days** (Feb-13 Presentation-eve, Apr-7 Annunciation) are now
  named by the movable commemoration the source headlines, with the fixed feast composed
  alongside in the source's rank order — instead of the fixed-feast label alone.

Readings are unaffected: these are **name-only** corrections. The readings 0-wrong
contract (`test_full_dataset`) and all coverage/accuracy figures are unchanged.

## [1.0.1]

Prior release. See the git history for details.
