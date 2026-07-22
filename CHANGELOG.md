# Changelog

All notable changes to **armenian-lectionary** are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [1.1.1] — 2026-07-21

### Changed
- **Readability separator in feast names.** The `"Liturgical Day"` name now joins a
  leading calendar-position label ("Nth day of \<Season\>", "Nth Sunday after/of
  \<Anchor\>", bare "Nth Sunday", "Octave of Easter (New Sunday)") to the commemoration
  the source mashes onto it with a ` — ` separator — e.g. `Twentieth day of Eastertide —
  Remembrance of the Armenian Genocide (1915)` instead of the previously run-together
  `Twentieth day of EastertideRemembrance of the Armenian Genocide (1915)`. This is a
  **presentation-only** change: the internal source-matched labels and the feast-name
  accuracy contract (`test_feast`, canonicalization blind to the separator) are unchanged,
  as are all readings.

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
