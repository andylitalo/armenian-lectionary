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
| `armenian_lectionary/data/observance_catalog.json` | Shipped `id -> {en, hy}` catalog for every liturgical-observance display-text component (commemoration/position/eve). The runtime resolution point for `language="hy"` feast/fast text (`engine._resolve_observance_names`) — see `dev/build_observance_catalog.py`. Loaded at import; degrades to `{}` if absent (→ English fallback). |
| `armenian_lectionary/data/book_names_hy.json` | Shipped English→Armenian map for Bible book heads, for `language="hy"` readings. Scraped once from sacredtradition.am by `dev/fetch_translations.py`; loaded at import, degrades to `{}` if absent (→ English fallback). |
| `armenian_lectionary/data/feast_names_hy.json` | No longer read at runtime (superseded by `observance_catalog.json`). Kept as a **dev-time input** to `dev/build_observance_catalog.py` and exercised by `tests/test_language.py`'s orthography guards; still rebuilt by `dev/fetch_translations.py`. |
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
                   tests.test_feast_contract
python -m unittest discover -s tests -t .                  # everything
```
The full-dataset regression tests (`test_regression`, `test_full_dataset`,
`test_table_build`, `test_feast`, `test_feast_name_raw`) need the git-ignored
`dev/reference_data/` ground-truth cache; they SKIP without it (`@requires_reference_cache`).
Rebuild the cache with `python dev/bulk_fetch.py` (see README).

The feast/fast NAME (`"Liturgical Day"`) — the value bahk persists into `Feast.name` — is
locked by **three** tests at different strengths. Keep all three; each covers what the
others structurally cannot:

| Test | Compares | Needs cache? |
|------|----------|--------------|
| `test_feast_name_raw` | the **raw string**, component-wise on ` — `. Contradictions (engine emits a component the source lacks) must be **0**; omissions and exact matches are ratchets, both now at their limits (0 omissions, 9,496/9,496 exact). | yes (2001–2026) |
| `test_feast_contract` | source-**independent** invariants — no placeholder, no empty name, `hy` differs from `en`, no repeated or runaway component, clean characters. Deliberately asserts **no storage limit**: how to store a name is the consumer's problem. | **no** (2001–2027) |
| `test_feast` | only the *commemoration component*. Narrowest: it strips the position/eve components from both sides, so >50% of days compare `"" == ""`. | yes (2001–2026) |
| `test_source_text` | the **source's own** text quality, not the engine's fidelity to it — see below. | yes (2001–2026) |
| `test_feast_name_review` | the engine against **our own** approved names (`dev/feast_name_review.tsv`) — the only one that can fail because a name is *wrong*. | mostly **no** |

That last stripping is why `test_feast` alone was not enough — the engine shipped a name
the source contradicted on 41 days, and six more as bare placeholders, entirely invisible
to it. `test_feast_contract` needs no ground truth, so it is the only cover for **2027**:
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

Registered repairs live in `dev/source_corrections._FEAST_TEXT_FIXES`, each justified by
the source contradicting itself rather than by editorial preference. When one lands, the
shipped artifacts must be rebuilt with it — including `saint_schedule.json`, whose feast
labels are served directly (`dev/refresh_artifact_names.py`). Every correction is written
up, with its evidence, in [`docs/feast-name-corrections.md`](docs/feast-name-corrections.md).

### Our own ground truth: `dev/feast_name_review.tsv`

`dev/reference_data/` is *sacredtradition.am's* ground truth. **`dev/feast_name_review.tsv`
is ours** — one row per distinct name component with the English a human approved, the
source's own Armenian beside it, and the questions still open. It is the only name test
that can fail because a name is *wrong* rather than because it differs from the source.

The review loop, and why it is safe to hand to a non-programmer:

1. open the TSV (a spreadsheet, or GitHub, which renders it as a table);
2. edit the `approved` column where the English should read differently, and say why in
   `note`. Leave `source` alone — it is the record of what was published;
3. `tests/test_feast_name_review.py` now fails, naming the row;
4. register the fold in `dev/source_corrections._FEAST_TEXT_FIXES`, rebuild (order below),
   and it passes.

`python dev/feast_name_review.py` refreshes the file and **never discards human edits**;
`--check` reports rows whose approved name the engine does not yet serve.

Dev tooling:
```bash
python dev/audit_source_anomalies.py     # errors in the SOURCE's own feast text
python dev/feast_name_review.py          # refresh dev/feast_name_review.tsv (our own GT)
python dev/refresh_artifact_names.py     # push registered fixes into saint_schedule.json
python dev/feast_discrepancy_report.py   # engine vs. source, classified (now: 0 findings)
python dev/verify_position_labels.py     # engine._position_label vs. every cached label
python dev/verify_eve_labels.py          # engine._eve_label vs. every cached eve note
python dev/feast_audit.py                # residual commemoration mismatches
```

**After any change to `dev/source_corrections`**, rebuild in this order and re-run the
suite — the table and the `hy` map are keyed on the corrected English, so a partial
rebuild leaves days with no Armenian name:
```bash
python dev/build_ground_truth.py               # freeze feast_name_review.tsv edits
python dev/refresh_artifact_names.py --write   # saint_schedule labels
python dev/build_table.py                      # lectionary_data.json
python dev/fetch_translations.py               # feast/book *_names_hy.json (offline
                                               #   from dev/reference_data_hy/)
python dev/build_observance_catalog.py         # observance_catalog.json
```
The catalog is **last** because it reads the outputs of the two steps above it. It was
missing from this list entirely, which is how a stale entry could survive a rebuild.
`dev/saint_schedule.py` and `dev/build_second_volume_cycles.py` are deliberately NOT in
that list: they do not currently reproduce their checked-in artifacts from the present
cache, and regenerating them moves readings provenance (2016-07-30 drops from
`second-volume-cycle` to `generative-saint`). That drift predates this work and needs its
own reviewed change.

Two kinds of name component are **not** stored in the table, because a table key is a
liturgical coordinate shared by civil years that disagree about them. `build_table.
unanimous_feast` drops any calendar-derived component the years sharing a key do not state
identically, and the engine regenerates it per date as an overlay in
`compute_armenian_lectionary`:

| Component | Regenerated by | Position | Verify with |
|---|---|---|---|
| calendar position — "Fourth Sunday after Nativity", "Sixth day of the Fast of Nativity", "Fast day" | `engine._position_label` | head | `dev/verify_position_labels.py` |
| eve note — "Eve of Fast of Advent", "Eve of Great Lent" | `engine._eve_label` | tail | `dev/verify_eve_labels.py` |

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
