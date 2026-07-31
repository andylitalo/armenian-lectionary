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
| `armenian_lectionary/data/{feast_names_hy,book_names_hy}.json` | Shipped English→Armenian name maps for `language="hy"` (feast strings/components and Bible book heads). Scraped once from sacredtradition.am by `dev/fetch_translations.py`; loaded at import, each degrades to `{}` if absent (→ English fallback). |
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
| `test_feast_name_raw` | the **raw string**, component-wise on ` — `. Contradictions (engine emits a component the source lacks) must be **0**; omissions and exact matches are ratchets. | yes (2001–2026) |
| `test_feast_contract` | source-**independent** invariants — no placeholder, fits `Feast.name`, `hy` differs from `en`, clean characters. | **no** (2001–2027) |
| `test_feast` | only the *commemoration component*. Narrowest: it strips the position/eve components from both sides, so >50% of days compare `"" == ""`. | yes (2001–2026) |

That last stripping is why `test_feast` alone was not enough — the engine shipped a name
the source contradicted on 41 days, and six more as bare placeholders, entirely invisible
to it. `test_feast_contract` needs no ground truth, so it is the only cover for **2027**:
sacredtradition.am publishes nothing for that year, so the cache's 365 days for it are
empty and no oracle test can assert anything about them.

The governing rule for any new difference from the source: it must be either counted by a
ratchet or registered in `dev/source_corrections`. Nothing passes silently.

Dev tooling:
```bash
python dev/feast_discrepancy_report.py   # -> reports/feast_name_discrepancies.md
python dev/verify_position_labels.py     # engine._position_label vs. every cached label
python dev/feast_audit.py                # residual commemoration mismatches
```

The calendar-position label ("Fourth Sunday after Nativity") is **not** stored in the
table — a table key is a liturgical coordinate shared by civil years whose ordinals
differ, so storing it asserted the modal year's count for every year. `build_table.
unanimous_feast` drops non-unanimous calendar-derived components and
`engine._position_label` regenerates them per date. If you add a family there, verify it
with `dev/verify_position_labels.py`: MISMATCH and EXTRA must both stay 0.

## Configuration (env vars)

| Var | Default | Effect |
|-----|---------|--------|
| `LECTIONARY_MIN_YEAR` / `LECTIONARY_MAX_YEAR` | `2001` / `2027` | Supported date range; outside → HTTP 400. |
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
