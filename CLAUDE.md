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
python -m unittest tests.test_calendar tests.test_parser   # self-contained, no cache
```
The full-dataset regression tests (`test_regression`, `test_full_dataset`,
`test_table_build`) need the git-ignored `dev/reference_data/` ground-truth cache;
without it they fail their coverage floors. Rebuild the cache with
`python dev/bulk_fetch.py` (see README).

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
python -m zipfile -l dist/*.whl       # confirm all five data/*.json are bundled
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
