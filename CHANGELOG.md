# Changelog

All notable changes to **armenian-lectionary** are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- **Calendar-position labels were frozen from the wrong year.** The validated table is keyed
  by liturgical *coordinate*, and many civil years share a key. The commemoration is
  invariant across them, but the position label the source packs into the same string
  ("Fourth Sunday after Nativity", "Third day of Advent") counts from an anchor whose
  distance to that coordinate changes year to year. `dev/build_table.modal_feast` stored
  the **modal** year's ordinal and the engine served it for every year, so the shipped
  `"Liturgical Day"` contradicted the source on **41 days** across 2001–2026 — e.g.
  2011-02-20 read `Fifth Sunday after Nativity` where the source says `Sixth`, and 17 days
  read `Third Sunday after Transfiguration` for the 4th/5th/6th/7th. Six further days
  shipped a bare placeholder (`(movable ordinary-time reading)` on 2011-02-04/06/09/11 and
  2022-02-04) or an invented eve (`Eve of the Presentation of the Lord` on 2011-02-13,
  where the source says `Fifth Sunday after Nativity — Eve of Fast of Catechumens`).

  Fixed in two halves. `dev/build_table.unanimous_feast` now drops a calendar-derived
  component unless every year sharing the key states it identically, so the table stops
  asserting what it cannot reproduce; commemorations are exempt, since the source varies a
  saint's companion list and dropping on disagreement would leave those days nameless.
  `engine._position_label` then regenerates the label per date, from families whose
  counting rules were derived from the ground truth and verified against **every**
  occurrence in it (`dev/verify_position_labels.py`: 6068 matched, 0 mismatched, 0
  spurious). Season-heading feasts are suppressed — the Assumption Sunday is
  `ASSUMPTION OF THE HOLY MOTHER OF GOD`, not `Fourth Sunday after Transfiguration` — and
  any family without an exact rule emits nothing, since an omitted label is incomplete but
  a wrong one is wrong.

  Net over the ground truth: contradictions 41 → **0**, days with no Armenian name 6 → **0**,
  omissions 63 → 15, exact 9373 → **9481** of 9496. **Readings are unchanged** — the
  0-wrong contract holds with every coverage floor untouched.
- **Eve notes were dropped where a fast opened on a fixed-date feast.** The same defect one
  step out: an eve sits at a fixed offset from a *movable* anchor, so when it lands on a
  fixed civil date the table key is that feast's date and the years sharing it disagree —
  `unanimous_feast` dropped the eve and the day lost its fast marker. 15 days across
  2001–2026, every one of them the opening of a fast: `Eve of Fast of Advent` on
  2004/2010/2021-11-21 (the Presentation of the Theotokos), `Eve of Great Lent` on
  2010/2021-02-14 (the Presentation of the Lord), `Eve of Fast of Saint James the bishop of
  Nisibis` on four Dec 9ths, `Eve of Fast of Exaltation of Holy Cross` on four Sep 8ths, and
  `Eve of Fast of Catechumens` on 2008-01-13 and 2011-02-13.

  `engine._eve_label` regenerates the eve per date and `_apply_eve_label` appends it where
  the name does not already carry one — the source prints the eve last, so this appends
  where the position label prepends. All twelve movable families plus the two solar ones
  (Dec 29, Jan 5) are exact offsets, verified on every occurrence in the ground truth
  (`dev/verify_eve_labels.py`: 338 matched, 0 mismatched, 0 missing, 0 spurious). The
  Advent eve is reproduced in both of the source's wordings — it keeps the article in the
  19 years Heesnak falls nine weeks after Exaltation and drops it in the seven where it
  falls ten.

  With this the ground-truth match is complete: omissions 15 → **0** and exact 9481 →
  **9496 of 9496**. The engine now reproduces sacredtradition.am's feast-name string on
  every day it publishes. Readings again unchanged.
- **Eighteen errors in the source's own feast text**, registered in
  `dev/source_corrections._FEAST_TEXT_FIXES` and found by the new
  `dev/audit_source_anomalies.py`. This became worth doing precisely because the engine now
  matches the source everywhere: from here on, each of the source's typos is a name the
  engine serves. Every fix is the source contradicting itself, never an editorial
  preference:
  - **factual**, caught by comparing a feast's English name with its own Armenian one —
    the Council of Ephesus is dated `AD 341` in English and `431 թ.` in Armenian, and
    Pentecost reads `Fifteenth day of Eastertide` where the Armenian says
    `յիսներորդ` (fiftieth), which is also what the day is (Easter+49, the day after the
    source's own `Forty Ninth day of Eastertide`);
  - **grammatical**, where the Armenian settles the sense — `the poor mans` → `poor men`,
    `many faithfuls` → `many faithful`, `Gregory of Theologian` → `Gregory the
    Theologian`, `Saint Patriarchs`/`Saint Virgins` → `Saints …` (both Armenian forms are
    plural), `Clement the Bishop Rome` → `Bishop of Rome`;
  - **mechanical** — `Saints Saints Jacoc`, `Saints St. Aret`, a trailing period on
    `Discovery of the Holy Cross.`, `Begining` → `Beginning`, `Antiosh` → `Antioch`, and
    `Fast day, Remembrance of the Ten Virgins`, whose fast marker was comma-joined into
    the commemoration where the source's own Armenian separates it;
  - **one saint, two spellings** — the Apostle `Phillip`/`Philip`, St. `Nicolas`/`Nicholas`
    of Myra, `Gregoris`/`Grigoris` of Aghvank, each folded to the source's dominant form.

  Left alone, and listed by the audit script instead, are the strings where nothing
  established the intended form: `Jacoc`, `Theodoron`, `coming out of Pit`, `Twelve Holy
  Doctors of Church`, and the source's lowercase `Saints martyrs` / `Saints virgins`.
- **Seven source self-contradictions registered** in `dev/source_corrections.POSITION_LABEL_FIXES`
  (a stray trailing period on `the Fast of Nativity.`, two comma-for-period variants of
  `Great Lent. Sunday of …`, and one wrong ordinal word on 2008-04-07 that its own
  neighbours pin), plus a case fold for the Theotokos' Presentation, which the source
  shouts in 19 of 26 years and title-cases in the other 7.

### Added
- **`tests/test_feast_name_raw.py`** — locks the **raw** `"Liturgical Day"` string
  component-wise, the value downstream actually stores. Contradictions must be 0; omissions
  and exact matches are ratchets. `tests/test_feast.py` compares only the *commemoration
  component*, which strips the position and eve components from both sides and so compared
  `"" == ""` on over half the corpus — that blind spot is what hid all of the above.
- **`tests/test_feast_contract.py`** — source-independent invariants (no placeholder, no
  empty name, `hy` differs from `en`, no repeated or runaway component, no contaminant
  characters) across the whole supported 2001–2027 window. Needs no ground-truth cache, so
  it also covers **2027**, for which sacredtradition.am publishes nothing and no oracle
  test can exist. It asserts no storage limit: the engine serves whatever name the source
  states — the longest is 289 characters, a feast enumerating twelve saints — and how to
  store that belongs to the consumer.
- **`tests/test_source_text.py`** — locks the quality of the SOURCE's feast text rather
  than the engine's fidelity to it. Without it, a re-fetch could pull a new typo from the
  live site into the cache, rebuild it into the shipped artifacts, pass every oracle test
  (the engine would match the source perfectly) and reach the client. A failure means a
  string no human has judged yet; judging it either way — a fix in `source_corrections`, or
  a named clearance in the audit script — makes it quiet again.
- **`dev/audit_source_anomalies.py`** — nine detectors over the source's own text, the
  two strongest cross-checking a feast's English name against its Armenian one.
- **`dev/refresh_artifact_names.py`** — pushes registered text fixes into
  `saint_schedule.json`'s served labels, text only: ids, ordering and every reading stay
  byte-identical, so a name fix cannot smuggle in a readings change.
- **`dev/feast_discrepancy_report.py`** — a classified inventory of every remaining
  feast-name difference, each shown with the two days either side of ground truth for
  context. It now reports no contradiction, no omission and no casing variant on any of
  the 9,496 days with ground truth, so the report itself is no longer committed.

## [1.2.3] — 2026-07-23

### Fixed
- **Reformed ("Soviet") orthography in the `hy` name maps.** The `language="hy"` maps carried
  reformed-orthography spellings the traditional (Mashtots) contract should have caught.
  Two **book** names slipped through `dev/fetch_translations.to_mashtots` because its reversal
  tables had no rule that fired on them — `Numbers` shipped as `Թվեր` (want `Թիւեր`) and
  `Deuteronomy` as `Երկրորդ օրենք` (want `Երկրորդ օրէնք`, `ե→է`). Five **feast** titles carried
  proper-noun reform slips the source typed into otherwise-traditional text: `Դանիել→Դանիէլ`
  (Daniel, three feasts), `Եզեկիել→Եզեկիէլ` (Ezekiel), `Անգե→Անգէ` (Haggai), and the Abgar
  commemoration's `հավատ→հաւատ` (`ավ→աւ`). Feast titles previously bypassed the reversal
  entirely; they now run through the specific-word (proper-noun) pass via a shared
  `to_mashtots_names`, which is safe on feasts — the blanket systematic `/aw/` swap is *not*
  applied there because it would corrupt the genuine consonant `վ` in `Վարդավառ`, `զօրավար`,
  `նախավկայ`. The shipped `book_names_hy.json`/`feast_names_hy.json` carry the corrected forms,
  the dev reversal tables reproduce them on a re-scrape, and two contract tests
  (`tests/test_language.py`) lock it: the book guard gains an `օրենք` marker plus a general vew
  (`վ`) check, and a new feast guard asserts the shipped feast map is a fixed point of
  `to_mashtots_names`. English keys, dates, and reading content are unchanged.

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
