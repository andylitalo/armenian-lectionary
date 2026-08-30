# CLAUDE.md

Guidance for working in this repo. The core is a self-contained, **offline**
engine that returns Armenian Church (Տօնացոյց / Ճաշոց) scripture readings for a
date. It is packaged for PyPI as **`armenian-lectionary`** (import name
`armenian_lectionary`) and also served by a thin Flask API on Cloud Run. No
network is used at runtime — readings come from a calendar algorithm
(`armenian_lectionary/engine.py`) plus an embedded validated table
(`armenian_lectionary/data/lectionary_data.json`).

The layout is **flat** (package at repo root), so the dev/test
`sys.path.insert(repo_root)` bootstrap resolves `import armenian_lectionary.engine`
with no install step.

## Layout

| Path | Purpose |
|------|---------|
| `pyproject.toml` | Hatchling build config + metadata; `armenian-lectionary` dist, dynamic version from `armenian_lectionary/__init__.py`, `armenian-lectionary` console script. |
| `armenian_lectionary/__init__.py` | Package init: re-exports the public API and `__version__`. |
| `armenian_lectionary/engine.py` | Offline engine. Public entry: `compute_armenian_lectionary(datetime.date) -> dict`. Internal helpers/constants importable from here. |
| `armenian_lectionary/cli.py` | `armenian-lectionary` console entry point (`main()`). |
| `armenian_lectionary/observance_catalog.py` | `ObservanceCatalog` — `id -> {en, hy}` plus the reverse indexes (`id_of`, `names_for`, `text_of`), built in its constructor so they cannot go stale, and `own_day_cache`, the engine's per-liturgical-year own-day scan held per instance. `engine._OBSERVANCE_CATALOG` is one of these. Reads dict-like (`[]`, `.get`, `.items()`, `in`); never written in place. |
| `armenian_lectionary/observance_name.py` | `ObservanceName` — the ordered components of a day's name, and the **only** place the ` — ` component separator is spelled at runtime. Owns the encoding (split/join, drop sets, placement, immutability); holds no domain opinion, so predicates like `engine._is_position_component` are passed in. See "A day's name is a list, not a string" below. |
| `armenian_lectionary/data/lectionary_data.json` | Embedded, cross-year-validated readings table (shipped; loaded once at import). |
| `armenian_lectionary/data/{second_volume_cycles,saint_readings,saint_schedule,continua_sequence}.json` | Shipped source-derived saint & continua data feeding the `second-volume-cycle` and `generative-continua` tiers (Tōnats'oyts Second Volume laydown + Fast-of-Assumption continua). Loaded at import; each degrades to `{}` if absent. |
| `armenian_lectionary/data/observance_catalog.json` | Shipped `id -> {en, hy}` catalog for every liturgical-observance display-text component (commemoration/position/eve). The runtime resolution point for `language="hy"` feast/fast text (`engine._resolve_observance_names`). A **projection** of the `id` column of `dev/observance_name_review.tsv` — see "Observance ids are stated, not derived" below. Loaded at import; degrades to `{}` if absent (→ English fallback). |
| `armenian_lectionary/data/observance_readings_index.json` | Shipped `readings-hash -> id` index, for the subset of the catalog whose observance is fully determined by its offset from a movable anchor (a dedicated fast weekday, an eve — never a day sharing its table key with a rotating saint). Lets English position/eve text resolve through the catalog too, the same way Armenian already does — see "A rename is a TSV edit, not an `engine.py` edit" below. Built by `dev/build_observance_catalog.py`; loaded at import, degrades to `{}` if absent (→ literal template text). |
| `armenian_lectionary/data/book_names_hy.json` | Shipped English→Armenian map for Bible book heads, for `language="hy"` readings. Scraped once from sacredtradition.am by `dev/fetch_translations.py`; loaded at import, degrades to `{}` if absent (→ English fallback). |
| `app.py` | Flask web app: `/readings`, `/health`, `/` doc. Imports the package. Range guard + rate limiting live here. |
| `Dockerfile` / `.dockerignore` | Container image for Cloud Run (`pip install .` + gunicorn on `0.0.0.0:$PORT`). |
| `dev/` | **Dev-only** tooling (ground-truth fetch, table build, analysis). Not used at runtime; excluded from the image and package. Writes the shipped JSON via the engine's PATH constants. |
| `dev/observance_names_hy.json` | Dev-only Armenian feast/fast map, scraped by `dev/fetch_translations.py` (`OBSERVANCE_MAP_PATH`). Never read at runtime and not bundled into the wheel — unlike its book-name counterpart below, superseded here by `observance_catalog.json`. Feeds the `source_hy` column in `dev/observance_name_review.tsv`, `dev/audit_source_anomalies.py`'s cross-language contradiction detectors, and `tests/test_language.py`'s orthography guards. |
| `tests/` | `unittest` suite. |
| `.github/workflows/release.yml` | Builds and publishes to PyPI (Trusted Publishing) on a `v*` tag. |

## Local development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt     # web layer
pip install -e .                    # engine package (editable)
python app.py                       # http://127.0.0.1:5001
curl "http://127.0.0.1:5001/readings?date=2026-04-05"
```

Run the container entrypoint locally (mirrors production):
```bash
PORT=8090 gunicorn --bind "0.0.0.0:$PORT" --workers 2 --threads 4 --timeout 60 app:app
```

### Tests
```bash
# self-contained, no cache needed:
python -m unittest tests.test_calendar tests.test_parser tests.test_language \
                   tests.test_observance_contract tests.test_build_registration \
                   tests.test_tier_ladder
python -m unittest discover -s tests -t .                  # everything
```
`test_build_registration` is the only test that drives the shipped-artifact **build**
(`dev/build_observance_catalog.py`) rather than the serving path — it rebuilds the catalog and
the readings index from the tracked ground truth over a simulated TSV rename, so it needs no
cache. See "The build asks for the declaration" below for what it exists to catch.
The full-dataset regression tests (`test_regression`, `test_full_dataset`,
`test_table_build`, `test_observance`, `test_observance_name_raw`) need the git-ignored
`dev/reference_data/` ground-truth cache; they SKIP without it (`@requires_reference_cache`).
Rebuild the cache with `python dev/bulk_fetch.py` (see README).

The feast/fast NAME (`"Liturgical Day"`) — the value bahk persists into `Feast.name` — is
locked by **six** tests at different strengths. Keep all six; each covers what the
others structurally cannot:

| Test | Compares | Needs cache? |
|------|----------|--------------|
| `test_observance_name_raw` | the **raw string**, component-wise on ` — `. Contradictions (engine emits a component the source lacks) must be **0**; omissions and exact matches are ratchets, both now at their limits (0 omissions, 9,496/9,496 exact). | yes (2001–2026) |
| `test_observance_contract` | source-**independent** invariants — no placeholder, no empty name, `hy` differs from `en`, no repeated or runaway component, clean characters. Deliberately asserts **no storage limit**: how to store a name is the consumer's problem. | **no** (2001–2027) |
| `test_observance` | only the *commemoration component*. Narrowest: it strips the position/eve components from both sides, so >50% of days compare `"" == ""`. | yes (2001–2026) |
| `test_source_text` | the **source's own** text quality, not the engine's fidelity to it — see below. | yes (2001–2026) |
| `test_observance_name_review` | the engine against **our own** approved names (`dev/observance_name_review.tsv`) — the only one that can fail because a name is *wrong*. | mostly **no** |
| `test_label_rules` | the position/eve **rule** against the source, not the served name — `engine._position_label` / `_eve_label` directly. The only one that can see a rule regression the validated table masks. MISMATCH, EXTRA and END-TO-END LOST are hard 0s; it imports `collect()` from the two verifier scripts so report and test cannot drift. | yes (2001–2026) |

That last stripping is why `test_observance` alone was not enough — the engine shipped a name
the source contradicted on 41 days, and six more as bare placeholders, entirely invisible
to it. `test_observance_contract` needs no ground truth, so it is the only cover for **2027**:
sacredtradition.am publishes nothing for that year, so the cache's 365 days for it are
empty and no oracle test can assert anything about them.

The governing rule for any new difference from the source: it must be either counted by a
ratchet or registered in `dev/source_corrections`. Nothing passes silently.

### The tier ladder is data, so its order is asserted

`_compute_lectionary` resolves a date by walking `engine._TIERS`, an ordered tuple of
thirteen `_tier_*` adapters, each returning a `_TierResult` or `None`. Precedence **is**
that order — it used to be the physical order of thirteen `if`/`return` paragraphs, where
moving one was a conspicuous edit.

It is now a one-token change that reads like tidying, and nothing in CI was watching.
Swapping the first two (`_tier_prelent_cohort` above `_tier_validated_table` — the
precedence that adapter's own comment argues for) changes what **117 days** serve, under a
different `Source`, and the whole suite stayed green: it is caught by one
`test_regression` test, and the cache that test needs is git-ignored, so CI skips it.
`_tier_presentation_eve` above `_tier_first_volume_winter_continua` was a second such gap.
The tuple also looks more forgiving than it is — 8 of its 12 adjacent swaps change no
output at all, because those tiers never claim the same date.

`tests/test_tier_ladder.py` states the ladder instead: every adapter is on it **once, in
definition order** (so the file still reads top-to-bottom as the precedence it
implements), `_tier_fallback` is last and unconditional, and each of the **21 real
precedence relations** is pinned to a date where *both* tiers apply. Needs no cache, so it
runs on every push; it fails on all 12 adjacent swaps and on a dropped, duplicated or
non-`_TierResult`-returning adapter.

Working rules:

- **Reordering `_TIERS` means moving the adapter's definition too.** That is deliberate
  friction: it is what makes a precedence change look like one again.
- **A tier's `Note` lives in a module-level `_NOTE_*` constant**, not inline in the
  adapter. Twelve of them, hoisted above the ladder so it reads as thirteen short
  decisions rather than thirteen paragraphs of prose. The text is served verbatim, so
  reflowing one changes the API response — verify against the reference dump, not by eye.
- **The ladder ends in a `for`/`else` that raises.** Unreachable while `_tier_fallback` is
  last and unconditional, and stated so that a bad reorder fails naming the date and the
  ladder rather than as an `AttributeError` on `None` three lines later.
- **A new tier needs a pin.** `test_the_pins_cover_every_contended_adjacency` fails if a
  new adapter makes a fifth adjacency contended and nothing pins it. Find the date by
  scanning the range for days where more than one tier returns non-`None`.
- **A pin's `loser` must genuinely apply on that date**, or it asserts coverage rather
  than precedence; `test_every_pin_actually_contends` enforces it.
- `_tier_generative_saint` and `_tier_fallback` **win on no date** in 2001–2027 — the
  first is fully shadowed by `_tier_validated_table` and `_tier_cycle_saint` (though it
  applies on 1,904 days), the second because every day in range is claimed earlier. Both
  are reachable outside the range, which is env-overridable, so neither is dead code.
  `tests/test_shadowed_tiers.py` is what exercises the two bodies: it finds the dates each
  tier actually wins on out to 2130 and asserts, for every one, that the readings served
  are attested by the validated table (a twin at the same zone-saint coordinate, or the
  identity's dominant validated reading set) and that the fallback serves none at all.
  The **shadowing itself is not pinned** — that is a fact about the current data, and one
  more validated coordinate would change it; `dev/audit_shadowed_tiers.py` reports it:

  ```bash
  python dev/audit_shadowed_tiers.py          # applies/wins per tier, and every win day verified
  python dev/audit_shadowed_tiers.py --list   # plus every shadowed disagreement
  ```
- **`_tier_generative_saint` is not leftover scaffolding, despite winning nothing.** Its
  original job — filling in-range blanks — did go to `_tier_cycle_saint`. What it covers
  now is the complement of two deliberate conservatism rules: `build_table`'s
  `_consistent(items, 2)` drops any coordinate seen in only one year, and `_CYCLE_SAINTS`
  carries only the days each year-type's Second Volume page prints, and the pages
  truncate. Five days per century fall in both holes; both of their coordinates verify.
  Its 16%-agreement-with-`_tier_cycle_saint` figure describes the floating-saint days it
  is never allowed to serve, not the days it does — see
  [`docs/generative-saint-tier.md`](docs/generative-saint-tier.md).

### The source is not automatically right

The engine now matches the source on every day it publishes, which means each of the
source's own typos is a name the engine serves. `dev/audit_source_anomalies.py` looks for
those, and `test_source_text` keeps its detectors silent. The strongest of them compare a
feast's English name against **its own Armenian name** — the source stating the same fact
twice, so it can be caught contradicting itself. That is how the Council of Ephesus was
found dated `AD 341` in English and `431` in Armenian, and Pentecost called the
`Fifteenth day of Eastertide` where the Armenian says fiftieth.

Registered repairs live in the `approved_en` column of `dev/observance_name_review.tsv`, each
justified by the source contradicting itself rather than by editorial preference (with one
declared exception — see the doc). `apply_ground_truth` resolves a component by **looking
it up whole**: `source_en` is a key into that table and a record for the reviewer, never an
ingredient in the answer, which is always `approved_en` verbatim. When one lands, the
shipped artifacts must be rebuilt with it — including `saint_schedule.json`, whose feast
labels are served directly (`dev/refresh_artifact_names.py`). Every correction is written
up, with its evidence, in [`docs/observance-name-corrections.md`](docs/observance-name-corrections.md).

### Our own ground truth: `dev/observance_name_review.tsv`

`dev/reference_data/` is *sacredtradition.am's* ground truth. **`dev/observance_name_review.tsv`
is ours** — one row per distinct name component with the English a human approved, the
source's own Armenian beside it, and the questions still open. It is the only name test
that can fail because a name is *wrong* rather than because it differs from the source.

The columns are symmetric across the two languages, which is the whole shape of the file:

| | English | Armenian |
|---|---|---|
| what sacredtradition.am published, never edited | `source_en` | `source_hy` |
| what the engine must serve — the decision | `approved_en` | `approved_hy` |

On a **composite** row (a packed day whose approved name splits into several canons) the
two `approved_*` cells are not a decision but a projection of the halves' rows — see
`component_ids` under "Observance ids are stated, not derived".

`source_en` is also the stable key everything downstream joins on. `approved_hy` is stated
on **every** row, not only where it differs from the scrape (394 of 397 are equal), for the
same reason `approved_en` is: it is a decision about what we serve, not a patch on someone
else's text. Keeping `source_hy` separate is what lets the Armenian remain the independent
witness that justifies most of the English corrections — an edit to `approved_hy` cannot
quietly erase the evidence for one.

The review loop, and why it is safe to hand to a non-programmer:

1. open the TSV (a spreadsheet, or GitHub, which renders it as a table);
2. edit `approved_en` (or `approved_hy`) where the text should read differently, and say
   why in `note`. Leave the `source_*` columns alone — they are the record of what was
   published. `id` (below) is preserved the same way;
3. `tests/test_observance_name_review.py` now fails, naming the row;
4. rebuild (order below), and it passes. The row **is** the registration — there is no
   second place to state a name. `build_ground_truth.py` freezes it and
   `apply_ground_truth` looks it up.

`python dev/observance_name_review.py` refreshes the file and **never discards human edits**;
`--check` reports rows whose approved name the engine does not yet serve. Rows come from
two places: every distinct component the source published (from the cache, keyed by its raw
text) and every position/eve label the engine *composes*, which the source may print less
specifically — `status = generated` marks the latter.

### Observance ids are stated, not derived

`observance_catalog.json` is the `id -> {en, hy}` table the engine resolves Armenian
through, and its keys are meant to be what a consumer stores instead of display text.
That only works if an id never moves. bahk keyed `Feast` on the name, and 1.3.0's
corrections made 158 of its 429 stored names unreachable, stranding curated icons and
generated contexts behind them with nothing raised; an id that shifted when its text was
corrected would reproduce that exactly, only harder to notice.

So the id lives in the **`id` column of `dev/observance_name_review.tsv`**, beside the human
decision about what the observance is called, and the catalog is a straight projection:

```
{row.id: {"en": row.approved_en, "hy": row.approved_hy}}
```

Correcting a name edits `approved_en`; the id stays put because nothing recomputes it. There
is no reuse-by-text lookup and no registry of superseded spellings — both existed only to
paper over ids being derived from the text they were supposed to outlive.

Working rules:

- **Never change an id.** Renaming one is a breaking change for every consumer that
  persisted it, with no way for them to detect it.
- **A genuinely new observance needs an id**, and `build_observance_catalog.py --mint`
  assigns one, writing it back to the TSV. The build refuses to write until every served
  component has one.
- **A composite row states its halves in `component_ids`**, and its `approved_en` /
  `approved_hy` are a **projection** of them — `build_ground_truth._compose` rejoins the
  halves' current text every rebuild, so the stored text is a record, not a source. Edit
  the HALF's row to rename a canon; the twelve composites follow on their own. The link is
  frozen once (by `observance_name_review._component_ids_for`, while the halves still
  resolve by text) and is immutable thereafter, exactly as `id` is — because text is what a
  rename moves. Three rows pack the Atomian generals, and while they quoted that canon by
  text, renaming it left all three quoting the old name and the catalog build refused.
  Pinned by `tests/test_rename_reaches_the_served_name.py`.
- **Leave `id` empty** for a row that is not one served observance: a whole day (the
  comma-joined "Fast day, Remembrance of the Ten Virgins", whose halves have their own
  ids), or a minority source spelling nothing reaches. Text the table *stores* keeps its id
  even where a higher-precedence tier shadows it at runtime — the artifacts still resolve.
  **Say why in `note`**, via `observance_name_review.NO_ID_REASONS` so it survives a rebuild:
  `test_every_id_less_row_says_why` fails on a bare empty id, because an id missing on
  purpose and an id missing by accident are otherwise indistinguishable, and the accident
  leaves a served observance unaddressable.
- **Retiring an id is declared**, in `_RETIRED_IDS` with the reason, or the build fails
  naming it. Reviving one fails too.
- **One observance is one CANON, not one printed line.** The Tōnats'oyts sets each saint's
  feast out as its own canon (First Volume pp.460–462, 464–465) and the Second Volume packs
  several onto one line when the taregir leaves few days for them, naming only the first
  "for the sake of brevity" (preface, Sixth, p.556). So a line like `Sts. Vahan of Goghtn,
  Gordius, Polyeuctus and Grigoris` is a **day**. Its `approved_en`/`approved_hy` split it
  on `_OBSERVANCE_SEP`, each canon keeps its own id, and the row itself gets none — the same
  shape as the comma-joined `Fast day, Remembrance of the Ten Virgins`. Group or split only
  on First Volume evidence, never on how similar two strings look.
  - A canon the source never publishes alone still needs a row and an id;
    `observance_name_review.py` emits one (`status = split`) from the halves of a split approved
    name, and its Armenian is stated by hand because there is no standalone scrape of it.
  - `engine._PACKED_POOLS` enumerates the two pools **by id** (`engine.packed_pool(sid)`;
    `dev/observance_ids.pool_of_text` is the text-keyed wrapper the reports use). It is what
    lets the discrepancy reports call a day where the engine serves more canons than the
    source printed an `EXPANSION` rather than a contradiction — the book's own instruction,
    kept visible and ratcheted. It lives in the engine because the runtime needs it too:
    see the next bullet.
  - **The preface-Sixth warrant is conditional, and the condition is enforced per date.**
    A companion is packed only where the taregir left it no day of its own;
    `engine._drop_owned_companions` asks that against `engine._canons_with_own_day(ly)`,
    the liturgical year's own laydown. It is a **per-date overlay**, in the
    `_apply_position_label` family and for the same reason: the packing is stored against a
    liturgical coordinate that civil years disagree about. A head canon is never dropped, so
    this only ever removes a name. Warrant and pages:
    `docs/sources/tonatsooyts-packed-saint-pools.md`; results and residual: docs §7b and
    `dev/audit_duplicate_commemorations.py`.
  - The engine serves **one packing per liturgical coordinate**; which canons the source
    names varies by year-type. That is the residual 5 English / 4 Armenian omissions, and
    closing it is a readings-provenance change (docs §7).

Invariants the build enforces, each of which was violable before: ids unique, English
unique (no two observances under one display string), no component carrying `_OBSERVANCE_SEP` in
its own text, every served component covered, nothing shipped silently dropped.

Dev tooling:
```bash
python dev/audit_source_anomalies.py     # errors in the SOURCE's own feast text
python dev/observance_name_review.py          # refresh dev/observance_name_review.tsv (our own GT)
python dev/refresh_artifact_names.py     # push registered fixes into saint_schedule.json
python dev/observance_discrepancy_report.py   # engine vs. source, classified (now: 0 findings)
python dev/verify_position_labels.py     # engine._position_label vs. every cached label
python dev/verify_eve_labels.py          # engine._eve_label vs. every cached eve note
                                         #   (both ratcheted by tests/test_label_rules.py)
python dev/observance_audit.py                # residual commemoration mismatches
python dev/audit_duplicate_commemorations.py  # a canon kept twice in one liturgical year
python dev/observance_year_table.py 2026 2027 --write   # docs/observance-names-<year>.tsv
```

The last two are **cross-day** checks, and that is the point: every other name check above
compares one day to the source, so a canon the engine keeps twice a year is invisible to
all of them (the packed day is a declared `EXPANSION`, the canon's own day is exact —
neither is wrong alone). `audit_duplicate_commemorations.py` needs no ground truth, which
is also what lets it cover **2027**; its ratchet is `tests/test_duplicate_commemorations.py`
and the by-design recurrences are declared in `observance_ids._RECURRING_OBSERVANCES`. See
docs §7b. `observance_year_table.py` writes the reviewing artifact that surfaced it —
a year per page, each day's ids positionally aligned with the words they stand for. Its
output is **not checked in**: 4 duplicates are still open, so a published table would be a
table to republish. Generate it when they close (docs/README.md).

**After any change to `dev/source_corrections`**, rebuild in this order and re-run the
suite — the table and the `hy` map are keyed on the corrected English, so a partial
rebuild leaves days with no Armenian name:
```bash
python dev/fetch_translations.py               # feast/book *_names_hy.json (offline
                                               #   from dev/reference_data_hy/)
python dev/observance_name_review.py                # refresh the TSV (never discards edits)
python dev/build_ground_truth.py               # freeze observance_name_review.tsv edits
python dev/build_observance_catalog.py         # observance_catalog.json + observance_readings_index.json
python dev/build_table.py                      # lectionary_data.json
python dev/refresh_artifact_names.py --write   # saint_schedule labels
```
The catalog comes **before** the table, not after: `dev/build_table.py` stamps an
`observance_ids` list onto every entry and fails loudly on a component the catalog does not
cover. And `observance_name_review.py` comes first, because a correction that introduces new
served text needs a row (and an id) before anything downstream can resolve it.
`dev/build_second_volume_cycles.py` used to be excluded from that list for not reproducing
its checked-in artifact; it does now, and `tests/test_second_volume_cycles.py` keeps it that
way by re-running the build and comparing. It stays out of the *routine* order only because
it reads the grabar-ocr translation rather than anything in this repo, so nothing above can
invalidate it. It refuses to run without `dev/reference_data/`: the cache-consistency filter
is the only thing keeping the tier honest, and it used to skip silently and ship ~269
entries ground truth contradicts.

`dev/saint_schedule.py` **is** still excluded, and measurably so: regenerating it changes 155
days' tier or name and 72 days' readings. That drift predates this work and needs its own
reviewed change.

### A day's name is a list, not a string

`"Liturgical Day"` is an ordered list of observances — a calendar-position label at the
head, one or more commemorations, an `Eve of ...` note at the tail — each of which is one
canon with its own id (see "One observance is one CANON" above). It is *written* as a
` — `-joined string, and the engine composes it in stages: a tier states the
commemorations, then the per-date overlays below add what a shared table key cannot hold.

**`armenian_lectionary/observance_name.ObservanceName` owns that encoding.** Every stage
used to re-derive it — split, drop the placeholders, find the component matching a
predicate, replace or insert, join, remember a served name is never empty — 21 times in
`engine.py` alone, with four different ideas of which components to drop and three
spellings of the empty-name fallback. `engine.py` now has **zero**; the overlays read as
what they liturgically are:

```python
ObservanceName.parse(label, drop=_PLACEHOLDER_LABELS).with_tail(eve).render()
ObservanceName.parse(label).without(drop).render()
name.insert_after_head(fixed, _is_position_component)
```

Working rules:

- **Never split or join a name in `engine.py`.** `tests/test_observance_name.py`'s
  `TestTheEngineDoesNotReDeriveTheEncoding` fails if you do. `_OBSERVANCE_SEP` stays in
  `engine.py` as a re-export because dev tooling imports it from there.
- **The module holds no domain opinion.** What counts as a position component, which
  strings are placeholders, which observance outranks which — all of that stays in
  `engine.py` and reaches the module as predicates and explicit `drop` sets. That is what
  keeps it importable without a cycle, and what keeps a new position family a one-file
  change.
- **`drop` is stated at every call site**, never defaulted: the sites genuinely disagree
  (the position overlay drops the bare fast markers too; `_anchor_genocide_remembrance`
  drops nothing, because it runs *before* the overlays that consume placeholders).
- **The "a served name is never empty" contract is the caller's.** `render()` returns `""`
  for an empty name; each site states its own fallback (`or label`). The module will not
  invent a name.
- Instances are immutable — every operation returns a new name. The overlays chain, so a
  mutating operation would corrupt the stage before it.

`dev/` still spells the separator out in 15 files; adopting the module there is a
follow-up. `dev/fetch_reference.py` and `dev/fetch_translations.py` keep their own copy on
purpose — they collapse the source's `<br>`-delimited HTML onto it before this package
sees the text.

### A generated label's id is declared, not recovered from its text

`_EVE_FAMILIES` and `_EVE_CIVIL` carry `(anchor, offset, **id**, literal)` — the same shape
`_FIXED_DATE_OBSERVANCES` has always had. The id is stated beside the rule that fires it,
not recovered by looking the literal up in the catalog.

Why: an eve is exactly one observance, so it has exactly one id, and the id is the only
thing about it a rename cannot move. Recovering it from text worked only while the engine's
literal happened to equal the row's `approved_en`. The Nativity fast's eve shows what
happens when a correction parts them — `_EVE_CIVIL` reads `"Eve of the Fast of Nativity"`
against a `source_en` of `"Eve of Fast of Nativity"`, so the row was **pinned**: renaming
`approved_en` left the literal matching neither column, the build reported a served
observance as unregistered, and forcing past that served the eve twice, once under each
name.

Rules:

- **A new eve declares its id** in the family table, and a new position family in
  `_POSITION_IDS`. `build_observance_catalog` reads both through one accessor,
  `engine.generated_observance_id(d, kind)`, so the label stays registered and keeps its
  readings-index entry through any rename.
- **A declared id outranks both inferences.** `_resolve_generated_id` takes it before the
  readings hash and the coordinate: those infer through an index built from display text,
  and some labels have no entry in it at all. The Advent eve is one — Heesnak itself, whose
  readings vary and whose coordinate is one of two — so a rename of it used to reach
  nothing. Pinned by `tests/test_rename_reaches_the_served_name.py`, which sweeps all 13.
- **The literal stays** as the thin-checkout fallback and as what
  `dev/verify_eve_labels.py` compares against the source. `_eve_label` still returns it.
- **A position family declares its ids in `engine._POSITION_IDS`**, not in its tuple: one
  family renders one observance *per ordinal* ("First day of Great Lent", "Second day of
  …", each its own catalog row), so the id belongs to the `(template, ordinal)` pair. 203
  entries over 39 templates. Keyed on the **template**, which belongs to `engine.py` and
  does not move on a TSV rename — unlike the served text, which is exactly what a rename
  moves. **Editing a template is a change to which observance the family names, so update
  this table with it**; `tests/test_rename_reaches_the_served_name.py` fails naming the
  uncovered label rather than letting the edit silently strand a rename.
- **The declared id is withheld under the coordinate guard**, like the coordinate itself.
  The guard is not about how strong the rule's evidence is; it is about the table and the
  rule naming *different observances* for a day, and there the stored, cross-year-validated
  value wins whatever the rule knows about itself.

Stored components are located by **id** too (`engine._stored_generated_component`).
`_is_position_component` / `_is_eve_component` recognise a component by its SHAPE
("Nth day of …", "Eve of …"), which is exactly what a rename may change; when it did, the
overlay could not see the stored component and appended the regenerated one beside it.

#### The build asks for the declaration; only the serving path infers

`generated_observance_id(d, kind)` returns the **declared** id and nothing else. That is the
whole of what the build may use, and the split matters:

| | asks | why |
|---|---|---|
| build (`dev/build_observance_catalog.py`) | `generated_observance_id` — declared only | the inferences read `_OBSERVANCE_ID_BY_READINGS`, which **is the previous build's own output**; a build resolving through it derives the new catalog from the old one |
| serving (`_apply_position_label` / `_apply_eve_label`) | `_resolve_generated_id` — declared → readings → coordinate | there the index is per-occurrence evidence produced independently of the rule, worth having on top of the declaration |

Both `declared_label_ids` (which `registration()` uses) and `build_readings_index`'s
`declared_ids` ask for both kinds. Asking for eves only is what shipped broken: 52 of the 216
labels are **pinned** — the engine literal equals neither `approved_en` nor `source_en` — so a
rename left them with no text route, and a pinned *position* label then silently lost its
index entry on rebuild while the build still reported success (registration was reading the
previous index). The next rebuild failed on what that one wrote. Pinned by
`tests/test_build_registration.py`, which drives the real build over a renamed ground truth —
`tests/test_rename_reaches_the_served_name.py` substitutes a catalog in-process and re-runs
the *serving* path, so it structurally cannot see a build defect.

Do **not** route the serving path through `generated_observance_id`: `_apply_position_label`
withholds `declared` *and* `coordinate` under the coordinate guard, and collapsing the two
calls would delete that guard.

### The catalog is held, not swapped underneath

`engine._OBSERVANCE_CATALOG` is an `ObservanceCatalog`, not a dict. The reverse indexes
(text → id, text → `{en, hy}`) are built in its constructor from the entries it holds, so
**they cannot disagree with it**. That deletes, rather than relocates, the four globals and
two accessors that used to keep them in step — `_TEXT_TO_OBSERVANCE_NAMES`,
`_TEXT_TO_OBSERVANCE_ID`, `_OBSERVANCE_INDEX_FOR`, `_observance_indexes`,
`_observance_names`, `_observance_ids` — and the identity check they ran on every lookup.

Working rules:

- **Substituting a catalog is constructing one**: `engine._OBSERVANCE_CATALOG =
  ObservanceCatalog({...})`, or `.replacing(sid, en=...)` for the common case of renaming
  one observance to see whether it propagates. There is no second thing to patch.
- **`own_day_cache` lives on the instance.** `_canons_with_own_day` memoizes a liturgical
  year's laydown *resolved through the catalog*, so a different catalog must not answer
  from the previous one's scan. It is a plain dict on the catalog rather than an
  `lru_cache` on the function, which is why nothing has to call `cache_clear()` any more.
  Pinned by `tests/test_observance_catalog.py`.
- **Reads are dict-like on purpose** (`catalog[sid]`, `.get`, `.items()`, `in`,
  truthiness): dev tooling and tests legitimately read entries by id. Writes are not — an
  instance is built complete or not at all.
- `_catalog_text(sid, default, lang)` stays a module function over `text_of`, because its
  eight callers want whatever `_OBSERVANCE_CATALOG` is bound to *now*.

Two kinds of name component are **not** stored in the table, because a table key is a
liturgical coordinate shared by civil years that disagree about them. `build_table.
unanimous_feast` drops any calendar-derived component the years sharing a key do not state
identically, and the engine regenerates it per date as an overlay in
`compute_armenian_lectionary`:

| Component | Regenerated by | Position | Verify with |
|---|---|---|---|
| calendar position — "Fourth Sunday after Nativity", "Sixth day of the Fast of Nativity", "Third day of the Fast of St. Gregory the Illuminator", "Second day of the Fast of Prophet Elijah", "First day of the Fast of St. James the bishop of Nisibis", "Wednesday Fast"/"Friday Fast", "Fast day" | `engine._position_label` | head | `dev/verify_position_labels.py` |
| eve note — "Eve of Fast of Advent", "Eve of Great Lent" | `engine._eve_label` | tail | `dev/verify_eve_labels.py` |

### A rename is a TSV edit, not an `engine.py` edit

For Armenian, a position/eve label never comes from `engine.py` directly: `engine.
_resolve_observance_names` looks the served English text up in `observance_catalog.json`
and substitutes that id's `hy`, so correcting `approved_hy` and rebuilding is enough —
`engine.py` never mentions the Armenian words at all. English used to be the exception:
`_position_label`/`_eve_label`'s literal template text was *always* what got served, so
correcting an English position/eve label meant editing the template in `engine.py`, not
just `dev/observance_name_review.tsv`'s `approved_en`.

`engine._apply_position_label`/`_apply_eve_label` close that gap the same way, for the
subset of labels it is safe to: those genuinely determined by their offset alone (a
dedicated fast weekday, an eve), never a label sharing its table key with a rotating
saint. The key that makes it safe is not the display text (which is exactly what a rename
changes) but the day's own **readings** — canonical, never corrected, so a hash of them
(`engine._observance_id_from_readings`) is a stable lookup key forever, with nothing to
freeze or snapshot.

`dev/build_observance_catalog.py`'s `build_readings_index` writes
`observance_readings_index.json`, a `readings-hash -> id` index, checked in both
directions per label: the same text must always carry the same readings, AND those
readings must never recur under a different text. Both checks run **within each label's
own dominant `Source` tier**, not across all of its occurrences pooled together — that
distinction is what lets the index cover every day of the Fast of St. James the bishop of
Nisibis despite Dec 9 (the Conception of the Holy Virgin, a fixed civil date) falling
inside that fast's window in 12 of 27 supported years: on those years Dec 9 outranks the
fast day and replaces its readings wholesale (`Source` flips `validated-table` ->
`validated-composite`), so those years are simply excluded from the label's readings
signature rather than treated as instability — the label is still fully, uniquely
identified by its readings on its other, undisplaced occurrences. The
Sunday-after-Nativity/Transfiguration/Assumption families are a different problem this
does NOT rescue: their instability is *within* one tier (`validated-table` every time —
the reading a lectio-continua slot carries stays put, but the Sunday-count the source
prints for it can drift across years of different length, per `_position_label`'s own
docstring), so they still fail the one-to-one readings check. Most of them are picked up
by the coordinate pass below instead; the Sunday-after-Nativity six and "Second Sunday
after Pentecost" are not, because a drifting count is not a stable coordinate either, and
they fall back to their literal template text.

Three more collisions, each real and each handled:

- **A position label and an eve note can share a day's readings by construction.**
  Pentecost+21 is a Sunday every year (21 is a multiple of 7), so "Third Sunday after
  Pentecost" and "Eve of Fast of St. Gregory the Illuminator" carry identical readings on
  *every* occurrence of either, forever. `_observance_id_from_readings` folds a `kind`
  ("position"/"eve") into the hash, so the two are keyed in separate namespaces and
  resolve independently despite the shared readings.
- **A day's readings are not always its own to be keyed by.** Some days have no readings
  at all: the ferial track of the Fast of the Catechumens (Առաջավորաց պահք) carries no
  scripture — a validated, intentional aliturgical day, not missing data. Far more often,
  a fixed civil feast outranks the day and takes its readings, leaving the label served
  but its signature unrecognizable. Both are handled by a second key, the calendar
  **coordinate** (`engine._position_coordinate` / `engine._eve_coordinate`: the family's
  own anchor key and day-offset, refactored out of `_position_label`/`_eve_label` so text
  and coordinate share one matching loop), hashed by
  `engine._observance_id_from_coordinate` in a namespace that cannot collide with a
  readings-based hash. `build_readings_index` gives an entry to every label with one
  stable coordinate no other label shares, and `_resolve_generated_text` tries it whenever
  the readings lookup finds nothing — for empty readings *and* after a miss.
  `kind` is folded into the coordinate hash for the same reason it is folded into the
  readings hash, and here the collision is not hypothetical: Pentecost+21 is the
  coordinate of both "Third Sunday after Pentecost" and "Eve of Fast of St. Gregory the
  Illuminator".

  The two keys are **not equally strong**, and the code does not pretend otherwise. A
  readings hit is per-occurrence evidence — readings come from the validated table,
  produced independently of the rule that emitted the label. A coordinate hit only
  restates that the rule fired here; its backing is rule-level
  (`dev/verify_position_labels.py`, 6,294 matched / 0 MISMATCH / 0 EXTRA, and
  `dev/verify_eve_labels.py`, 338/338) — and that backing is **asserted**, by
  `tests/test_label_rules.py`, rather than read off a script's output. Three things keep
  the weaker key honest, each covering a moment the others do not:

  | Guard | Where | Fires when |
  |---|---|---|
  | `_assert_routes_agree` | `build_readings_index` | a rebuild would write an index whose two routes name different observances — the build fails and writes nothing |
  | `tests/test_coordinate_index.py` | CI | a change parts the table from the rule, or leaves a covered label-day unresolvable, anywhere in `MIN_YEAR`–`MAX_YEAR` |
  | the coordinate guard | `_apply_position_label` / `_apply_eve_label` | at request time, a stored position/eve component disagrees with the rule — the stored value wins and no rename is applied |

  The third exists because the first two are bounded by the supported range and the range
  is **env-overridable by design**: the deploy runbook below widens it with a one-line
  `gcloud run services update`, and the engine's own `ValueError` tells a library consumer
  to do the same. Neither a build assertion nor a CI sweep is in the path then. In range
  the guard never fires — the table and the rule agree on all 6,312 days that have both.
- **A dominant `Source` tier is not always enough.** "Eve of Great Lent" disagrees on 2
  of 27 years (2010, 2021) — the Presentation of the Lord, a *fixed civil date* (Feb 14),
  happens to land on Great Lent's own eve and outranks it — but `Source` stays
  `validated-table` both ways, so tier-filtering alone can't see it (unlike Nisibis/Dec 9,
  where `Source` flips to `validated-composite`). `build_readings_index` attributes a
  disagreeing occurrence to the competing observance only when that's independently
  *provable*: the date's pre-overlay commemoration
  (`_compute_lectionary(d)["Liturgical Day"]`, before any eve/position text is added) must
  have exactly one reading set across *every* one of its own occurrences globally, **and**
  occur on at least one date that does not also carry this label — the second condition
  rules out a self-referential trap where a civil-year-unanimous table entry already bakes
  this very label's own text into its stored `"feast"` field. A label's remaining,
  unexplained occurrences must still agree *exactly*. Collision detection runs across
  every tier a label was *ever* served under, not just its dominant one, since a
  minority-tier occurrence (a best-guess continuum filling in for an unvalidated date) can
  still reuse another label's reading pool.

`engine._resolve_generated_text` does the lookup at request time;
`_apply_position_label`/`_apply_eve_label` only let it override a stored, validated table
value when it actually resolves to something *different* from the literal default — that
default is otherwise trusted over a fresh recomputation, for the same reason the table
overlay exists in the first place.

Practically: to rename an English position/eve label the index covers — which is now all
but the 8 listed under *Index coverage*, `illuminator_fast_day_*` and `james_nisibis_day_*`
among them — edit
`approved_en` in `dev/observance_name_review.tsv` and rebuild (`build_ground_truth.py`
then `build_observance_catalog.py`) — `engine.py` does not change. `dev/
source_corrections.named_fast_label` calls `engine._position_label` directly rather
than keeping its own copy of the window and template, for the same duplication reason;
`dev/observance_names._SEASONS` derives the Illuminator, Nisibis, and Prophet Elijah
fasts' bare names from the live catalog rather than a hardcoded literal, so none of them
goes stale the day a rename ships.

Introducing a genuinely NEW label this mechanism does not yet cover -- as opposed to
renaming one it does -- is a different operation: it still needs the `_POSITION_FAMILIES`
edit (and, if the source's bare text is ambiguous on those days, a
`source_corrections.named_fast_label`/`named_fast_label_hy` fold), same as before the
readings index existed. Only after that rebuild does the new label join the index and
become rename-by-TSV like the others. Naming the Fast of St. James the bishop of Nisibis
and the Fast of Prophet Elijah (docs/observance-name-corrections.md section 6b) is the
worked example: Nisibis needed both halves (no label existed at all); Elijah needed only
the `_POSITION_FAMILIES` template edit, since its position label was already served, just
under a less specific name.

#### Coverage is per-label; resolution is per-occurrence

Coverage is a property of a **label**; whether a rename actually reaches a given day is a
property of that **occurrence**. The two came apart under the readings-only index: an
indexed label resolved on the occurrences whose readings were its own, but on an
occurrence where something else supplied the day's readings the hash missed and
`_resolve_generated_text` returned the literal template text — so a TSV rename reached
every other day of the same label and not that one. Serving was unaffected (the literal
text is the correct text, which is what `verify_position_labels.py`'s 0 MISMATCH means);
only renameability was.

That was **93 of ~4,300** served position/eve label-days, over **31 labels** and **11
civil dates** — `Source` split 44 `validated-composite`, 13 `generative-composite`, 36
`validated-table`; concentrated on Sep 8 (24 days), Dec 9 (20), Feb 14 (12), Nov 20 (8),
Apr 7 (7), Feb 13 (5). The dominant cause was displacement by a fixed civil feast, seen
from the occurrence side rather than the label side.

The coordinate pass closes all 93: every covered label-day in range now resolves, pinned
by `tests/test_coordinate_index.py`. The Dec-9/Nisibis case that motivated it is now
ordinary — Dec 9 falls inside that fast's window in 12 of 27 years, and a rename reaches
those days like any other.

**This no longer constrains test-year choice**, which it used to. `tests/test_language.py`'s
`TestNisibisAndElijahRenamesResolveThroughTheCatalog` still uses 2017, where Dec 9 (a
Saturday, Heesnak+20) falls outside the window, so all five days are `validated-table` —
but that is now belt-and-braces rather than a requirement, and a composite year would pass
too.

#### Index coverage

"Index coverage" is a **separate axis from accuracy**, not a measure of it:
`tests/test_observance_name_raw.py`/`test_observance_name_hy_raw.py` already guarantee served text
matches sacredtradition.am on every day, covered label or not (0 contradictions, hard
requirement). Coverage instead measures how many of the position/eve labels the engine
can currently produce would pick up a *future* TSV rename with no `engine.py` edit.
Currently **202 of 210** (run `python3 -c "import json; print(len(json.load(open(
'armenian_lectionary/data/observance_readings_index.json'))))"` for the live entry count,
which is larger — a label can hold both a readings entry and a coordinate entry).

The remaining **8** have neither a stable reading nor a stable coordinate to key on. The
day-count families the readings index used to miss (Great Lent, the Nativity, Catechumens
and Assumption fasts, Eastertide) are all covered now: their ordinal is arithmetic in the
offset, so one label sits on exactly one coordinate. What is left is the labels where that
is not true either:

- `"Fast day"` — not one observance to begin with; it labels ~1,513 unrelated days, and so
  sits on as many coordinates.
- `First`–`Sixth Sunday after Nativity` and `Second Sunday after Pentecost` —
  `_position_label`'s own docstring flags their counting rule as "not exact on every
  occurrence": the season's length depends on the movable Easter date, so the same ordinal
  falls at different offsets in different years. Neither the same ordinal mapping to the
  same reading, nor one ordinal to one coordinate.

These are not rescuable by refining either key: the text is not a stable function of the
readings *or* of the calendar coordinate, so there is no signal left to hash. **They no
longer need to be.** `engine._POSITION_IDS` and the eve families' declared ids are exactly
the hand-maintained table this note used to scope, and a declared id outranks both
inferences (`_resolve_generated_id`), so every position and eve label is renameable through
the TSV whether or not the index covers it. Ten position labels — these seven plus the two
weekly fasts and the bare marker — were never in the index at all and are now reached.

Index coverage still matters for what it measures: the index is per-*occurrence* evidence
produced independently of the rule, which is why it is consulted first for anything a
declared id does not name.

A third overlay is not a table problem but a **translation gap**: `engine._FIXED_DATE_OBSERVANCES`
adds an observance on a fixed civil date that the source's *English* names on no day at all —
currently Jan 1's `Blessing of the Pomegranates`. There is no printed English to correct, so
it cannot go through `apply_ground_truth`; it is declared in the engine, listed in
`dev/observance_ids._ADDED_OBSERVANCES`, and pinned by `OBSERVANCE_ADDITION_DAYS` as an
**equality**, because an addition is excluded from the contradiction count by construction
and nothing else would notice it firing on the wrong days. Each entry carries the **first
year it applies** (2015 for the Pomegranates, the year the rite was instituted) — the one
place the engine is a function of history rather than of the calendar, because the
institution of a feast is a datable event and serving a rite before it existed is a claim
about a year, not a rounding error.

Its mirror is `dev/observance_ids._DECLINED_SOURCE_HY`: source text the engine deliberately
does **not** serve (the civil New Year, which sacredtradition.am prints and the 1915
Tōnats'oyts does not carry at all). Same reasoning — omitting what the source states needs
declaring, or the omission ratchet stops meaning "unexplained" — and the same equality
pinning, `HY_DECLINED_DAYS`. Adding to either set requires a write-up in docs §9.

Storing them asserted the modal year's count for every year — the defect that shipped
41 wrong names. If you add a family to either, run its verifier: MISMATCH and EXTRA must
stay 0, and so must the END-TO-END LOST count, which is the number that actually matters
downstream (a fasting calendar is built from exactly these components). All three are
asserted by `tests/test_label_rules.py`, so a regression fails the suite rather than
waiting for someone to read the report — but run the script anyway when you add a family:
it groups the residue by family, which the test does not.

## Configuration (env vars)

| Var | Default | Effect |
|-----|---------|--------|
| `LECTIONARY_MIN_YEAR` / `LECTIONARY_MAX_YEAR` | `2001` / `2027` | Supported date range, read by the engine (`ValueError` outside it) and imported by `app.py`, which turns it into HTTP 400. `calculate_liturgical_mode` is exempt — pure arithmetic. |
| `LECTIONARY_RATE_LIMITS` | `60 per minute;600 per hour` | Per-client-IP limits (semicolon-separated). |
| `LECTIONARY_RATELIMIT_STORAGE_URI` | `memory://` | Rate-limit counter store. Set to a shared backend (e.g. `redis://…`) for exact global limits across instances. |
| `PORT` | `8080` (container) | Bind port; set by Cloud Run. |

## Deploy / redeploy to Cloud Run

Hosted on **Google Cloud Run**. Deployment facts:

- **Project:** `armenian-lectionary` · **Region:** `us-central1` · **Service:** `lectionary`
- **URLs:** https://lectionary.andylitalo.com/readings (custom domain) and the
  `*.run.app` URL. Public (`allUsers` invoker).

A redeploy is a single command from the repo root — domain mapping, TLS, IAM, and
env config all persist across revisions:

```bash
gcloud config set project armenian-lectionary        # once per shell
gcloud run deploy lectionary \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --min-instances 0 --max-instances 3
```

To change an env var without a code change (creates a new revision):
```bash
gcloud run services update lectionary --region us-central1 \
  --update-env-vars LECTIONARY_MAX_YEAR=2028
```

Verify after deploy:
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://lectionary.andylitalo.com/readings   # 200
curl -s "https://lectionary.andylitalo.com/readings?date=2030-01-01"                  # 400 + range note
```

### One-time setup (already done; for reference / disaster recovery)

These were needed once on the fresh project and persist:
- Enable APIs: `run.googleapis.com`, `cloudbuild.googleapis.com`, `artifactregistry.googleapis.com`.
- Grant the build service account read access to source:
  `roles/cloudbuild.builds.builder` on `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`.
- Public access under a Workspace org required relaxing Domain Restricted Sharing:
  org policy `iam.allowedPolicyMemberDomains` set to `allowAll: true` **scoped to
  this project**, then `allUsers` granted `roles/run.invoker` on the service.
- Custom domain: `gcloud beta run domain-mappings create --service=lectionary
  --domain=lectionary.andylitalo.com --region=us-central1`, then add the returned
  A/AAAA records at the DNS host (Squarespace). Google issues managed TLS once DNS resolves.

## Packaging & release (PyPI)

The engine ships as the `armenian-lectionary` wheel (stdlib-only, all JSON data
bundled under `armenian_lectionary/data/`). Build and check locally:

```bash
pip install build twine
python -m build                       # -> dist/*.whl, dist/*.tar.gz
python -m zipfile -l dist/*.whl       # confirm all eight data/*.json are bundled
twine check dist/*
```

Releases are automated: pushing a `v*` tag runs `.github/workflows/release.yml`,
which builds and publishes via **PyPI Trusted Publishing (OIDC)** — no stored
tokens. `__version__` in `armenian_lectionary/__init__.py` is the single source of
truth for the version; bump it and tag to match (e.g. `v1.0.0`). One-time setup:
register this repo as a Trusted Publisher on PyPI for the `armenian-lectionary`
project.

## Conventions

- Keep the runtime offline — never add a network call to the request path.
- `app.json.ensure_ascii = False` keeps Armenian script native in responses; preserve it.
- Engine changes must keep the test suite's **0-wrong** contract (validated tiers never
  return a wrong reading); see `tests/test_full_dataset.py`.
