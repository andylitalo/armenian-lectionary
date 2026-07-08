# CLAUDE.md

Guidance for working in this repo. The app is a self-contained, **offline** Flask
API that returns Armenian Church (Տօնացոյց / Ճաշոց) scripture readings for a date.
No network is used at runtime — readings come from a calendar algorithm
(`lectionary.py`) plus an embedded validated table (`lectionary_data.json`).

## Layout

| Path | Purpose |
|------|---------|
| `app.py` | Flask web app: `/readings`, `/health`, `/` doc. Range guard + rate limiting live here. |
| `lectionary.py` | Offline engine. Public entry: `compute_armenian_lectionary(datetime.date) -> dict`. |
| `lectionary_data.json` | Embedded, cross-year-validated readings table (shipped; loaded once at import). |
| `Dockerfile` / `.dockerignore` | Container image for Cloud Run (gunicorn on `0.0.0.0:$PORT`). |
| `dev/` | **Dev-only** tooling (ground-truth fetch, table build, analysis). Not used at runtime; excluded from the image. |
| `tests/` | `unittest` suite. |

## Local development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
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

## Conventions

- Keep the runtime offline — never add a network call to the request path.
- `app.json.ensure_ascii = False` keeps Armenian script native in responses; preserve it.
- Engine changes must keep the test suite's **0-wrong** contract (validated tiers never
  return a wrong reading); see `tests/test_full_dataset.py`.
