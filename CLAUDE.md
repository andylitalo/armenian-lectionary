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
| `armenian_lectionary/data/lectionary_data.json` | Embedded, cross-year-validated readings table (shipped; loaded once at import). |
| `armenian_lectionary/data/{second_volume_cycles,saint_readings,saint_schedule,continua_sequence}.json` | Shipped source-derived saint & continua data feeding the `second-volume-cycle` and `generative-continua` tiers (Tōnats'oyts Second Volume laydown + Fast-of-Assumption continua). Loaded at import; each degrades to `{}` if absent. |
| `armenian_lectionary/data/observance_catalog.json` | Shipped `id -> {en, hy}` catalog for every liturgical-observance display-text component (commemoration/position/eve). The runtime resolution point for `language="hy"` feast/fast text (`engine._resolve_observance_names`). A **projection** of the `id` column of `dev/observance_name_review.tsv` — see "Observance ids are stated, not derived" below. Loaded at import; degrades to `{}` if absent (→ English fallback). |
| `armenian_lectionary/data/observance_readings_index.json` | Shipped `readings-hash -> id` index, for the subset of the catalog whose observance is fully determined by its offset from a movable anchor (a dedicated fast weekday, an eve — never a day sharing its table key with a rotating saint). Lets English position/eve text resolve through the catalog too, the same way Armenian already does — see "A rename is a TSV edit, not an `engine.py` edit" below. Built by `dev/build_observance_catalog.py`; loaded at import, degrades to `{}` if absent (→ literal template text). |
| `armenian_lectionary/data/book_names_hy.json` | Shipped English→Armenian map for Bible book heads, for `language="hy"` readings. Scraped once from sacredtradition.am by `dev/fetch_translations.py`; loaded at import, degrades to `{}` if absent (→ English fallback). |
| `armenian_lectionary/data/feast_names_hy.json` | No longer read at runtime (superseded by `observance_catalog.json`). Kept as the source of the `source_hy` column in `dev/observance_name_review.tsv` and exercised by `tests/test_language.py`'s orthography guards; still rebuilt by `dev/fetch_translations.py`. |
| `app.py` | Flask web app: `/readings`, `/health`, `/` doc. Imports the package. Range guard + rate limiting live here. |
| `Dockerfile` / `.dockerignore` | Container image for Cloud Run (`pip install .` + gunicorn on `0.0.0.0:$PORT`). |
| `dev/` | **Dev-only** tooling (ground-truth fetch, table build, analysis). Not used at runtime; excluded from the image and package. Writes the shipped JSON via the engine's PATH constants. |
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
                   tests.test_observance_contract
python -m unittest discover -s tests -t .                  # everything
```
The full-dataset regression tests (`test_regression`, `test_full_dataset`,
`test_table_build`, `test_observance`, `test_observance_name_raw`) need the git-ignored
`dev/reference_data/` ground-truth cache; they SKIP without it (`@requires_reference_cache`).
Rebuild the cache with `python dev/bulk_fetch.py` (see README).

The feast/fast NAME (`"Liturgical Day"`) — the value bahk persists into `Feast.name` — is
locked by **three** tests at different strengths. Keep all three; each covers what the
others structurally cannot:

| Test | Compares | Needs cache? |
|------|----------|--------------|
| `test_observance_name_raw` | the **raw string**, component-wise on ` — `. Contradictions (engine emits a component the source lacks) must be **0**; omissions and exact matches are ratchets, both now at their limits (0 omissions, 9,496/9,496 exact). | yes (2001–2026) |
| `test_observance_contract` | source-**independent** invariants — no placeholder, no empty name, `hy` differs from `en`, no repeated or runaway component, clean characters. Deliberately asserts **no storage limit**: how to store a name is the consumer's problem. | **no** (2001–2027) |
| `test_observance` | only the *commemoration component*. Narrowest: it strips the position/eve components from both sides, so >50% of days compare `"" == ""`. | yes (2001–2026) |
| `test_source_text` | the **source's own** text quality, not the engine's fidelity to it — see below. | yes (2001–2026) |
| `test_observance_name_review` | the engine against **our own** approved names (`dev/observance_name_review.tsv`) — the only one that can fail because a name is *wrong*. | mostly **no** |

That last stripping is why `test_observance` alone was not enough — the engine shipped a name
the source contradicted on 41 days, and six more as bare placeholders, entirely invisible
to it. `test_observance_contract` needs no ground truth, so it is the only cover for **2027**:
sacredtradition.am publishes nothing for that year, so the cache's 365 days for it are
empty and no oracle test can assert anything about them.

The governing rule for any new difference from the source: it must be either counted by a
ratchet or registered in `dev/source_corrections`. Nothing passes silently.

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
  - `dev/observance_ids._PACKED_POOLS` enumerates the two pools **by id**. It is what lets
    the discrepancy reports call a day where the engine serves more canons than the source
    printed an `EXPANSION` rather than a contradiction — the book's own instruction, kept
    visible and ratcheted.
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
python dev/observance_audit.py                # residual commemoration mismatches
```

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

Two kinds of name component are **not** stored in the table, because a table key is a
liturgical coordinate shared by civil years that disagree about them. `build_table.
unanimous_feast` drops any calendar-derived component the years sharing a key do not state
identically, and the engine regenerates it per date as an overlay in
`compute_armenian_lectionary`:

| Component | Regenerated by | Position | Verify with |
|---|---|---|---|
| calendar position — "Fourth Sunday after Nativity", "Sixth day of the Fast of Nativity", "Third day of the Fast of St. Gregory the Illuminator", "Fast day" | `engine._position_label` | head | `dev/verify_position_labels.py` |
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
docstring), so they still fail the one-to-one check and stay excluded, falling back to
their literal template text.

Three more collisions, each real and each handled:

- **A position label and an eve note can share a day's readings by construction.**
  Pentecost+21 is a Sunday every year (21 is a multiple of 7), so "Third Sunday after
  Pentecost" and "Eve of Fast of St. Gregory the Illuminator" carry identical readings on
  *every* occurrence of either, forever. `_observance_id_from_readings` folds a `kind`
  ("position"/"eve") into the hash, so the two are keyed in separate namespaces and
  resolve independently despite the shared readings.
- **Some position labels have no readings to hash.** A few days in the ferial track of
  the Fast of the Catechumens (Aṙաջավորաց պահք) carry no scripture — a validated,
  intentional aliturgical day, not missing data. Those are indexed instead by calendar
  **coordinate** (`engine._position_coordinate`: the position family's own anchor key and
  day-offset, refactored out of `_position_label` so both share one matching loop), hashed
  by `engine._observance_id_from_coordinate` in a namespace that cannot collide with a
  readings-based hash. The coordinate is a pure function of the calendar, so it's exactly
  as stable as readings are elsewhere; `_resolve_generated_text` only falls back to it
  when `readings` is empty, never after a real readings lookup misses.
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

Practically: to rename an English position/eve label already covered by the readings
index (`illuminator_fast_day_*`, `nisibis_fast_day_*` once PR #28 lands, and similar),
edit `approved_en` in `dev/observance_name_review.tsv` and rebuild (`build_ground_truth.py`
then `build_observance_catalog.py`) — `engine.py` does not change. `dev/
source_corrections.illuminator_fast_label` calls `engine._position_label` directly rather
than keeping its own copy of the window and template, for the same duplication reason;
`dev/observance_names._SEASONS` derives the Illuminator fast's bare name from the live catalog
rather than a hardcoded literal, so it does not go stale the day a rename ships.

#### Index coverage

"Index coverage" is a **separate axis from accuracy**, not a measure of it:
`tests/test_observance_name_raw.py`/`test_observance_name_hy_raw.py` already guarantee served text
matches sacredtradition.am on every day, covered label or not (0 contradictions, hard
requirement). Coverage instead measures how many of the position/eve labels the engine
can currently produce would pick up a *future* TSV rename with no `engine.py` edit.
Currently **161 of 205** (run `python3 -c "import json; print(len(json.load(open(
'armenian_lectionary/data/observance_readings_index.json'))))"` for the live count).

The remaining 44 have no independently verifiable stable reading at all, even after the
commemoration-attribution check above — genuine variance in the source's own counting,
not a gap in the mechanism:

- `"Fast day"` itself — not one observance to begin with; it labels ~1,575 unrelated days.
- The Sunday-after-Nativity/Transfiguration/Assumption/Pentecost families and the Advent
  Sunday count — `_position_label`'s own docstring already flags their counting rule as
  "not exact on every occurrence": the season's length depends on the movable Easter
  date, so the lectio-continua sequence compresses or skips in a short year, and neither
  the same ordinal maps to the same reading nor different ordinals map to different
  readings, reliably.
- The Great Lent, Nativity-fast, Catechumens-fast, and Assumption day-counts, and a few
  Easter/Eastertide day-counts — the same shape of drift, one level down.

None of this is rescuable by refining the readings-index mechanism further: the
text↔reading relationship for these families genuinely isn't stable in the data, so
there is no signal — readings, coordinate, or otherwise — left to key on. Making these
renameable via the TSV alone would need a structurally different mechanism (a literal,
hand-maintained `(family, offset) -> id` table embedded in `engine.py`, decoupled from
both text and readings) — a larger, separate undertaking, out of scope here.

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
downstream (a fasting calendar is built from exactly these components).

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
python -m zipfile -l dist/*.whl       # confirm all seven data/*.json are bundled
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
