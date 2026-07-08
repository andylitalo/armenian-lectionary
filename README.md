# Armenian Lectionary API

A self-contained, **offline** web service with one endpoint that returns the
Armenian Church (Տօնացոյց / Ճաշոց) scripture readings for any day.

No network is used at runtime. The readings are produced by a calendar
**algorithm** combined with an embedded, cross-year-validated **data table**.

## How it works

The Armenian lectionary is one of the oldest in Christendom, and most of its
sanctoral is **movable** — commemorations are anchored to feasts, not civil
dates (e.g. Sts. Hripsime always falls on Easter + 57, so it drifts year to
year). The engine therefore works in two steps:

1. **Calendar framework** (`lectionary.py`) computes each date's *liturgical
   coordinates* from the feast chain:
   - **Easter** (Meeus/Jones/Butcher, Gregorian as the Armenian Church uses
     since 1923) anchors Pre-Lent → Lent → Holy Week → Eastertide → Pentecost →
     post-Pentecost → Transfiguration (Easter + 98).
   - **Solar feasts** — Assumption (Sun closest to Aug 15), Exaltation of the
     Cross (Sun closest to Sep 14), Heesnak/Advent (Sun closest to Nov 18).
   - **Fixed feasts** — Theophany/Nativity (Jan 6), Presentation (Feb 14),
     Annunciation (Apr 7), etc.
2. **Embedded table** (`lectionary_data.json`) maps each coordinate to the
   actual readings. It was distilled and **cross-year validated** from 13 years
   (2014–2026) of the authoritative Tonatsooyts: an entry is kept only if every
   year that hit that coordinate agreed on the readings.

### Accuracy

Validated against all ~4,700 historical days:

| Metric | Result |
|--------|--------|
| Exact reading match | **76%** of all days |
| Wrong (table hit but mismatched) | **0** |
| Accuracy *where the table has data* | **100%** |
| Flagged estimate (no data yet) | 24% |

Every covered day is exactly correct; days without a validated entry are
clearly flagged (`"Source": "algorithmic-estimate"`) rather than guessed. The
uncovered days are chiefly the **winter "hinge"** (Advent → Theophany →
pre-Lent), whose ferial saint/fast tracks are governed by an ordered
slot-consumption rule that is still being modeled (see `dev/`).

## Setup & run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py        # serves http://127.0.0.1:5001
```

## Endpoint

### `GET /readings?date=YYYY-MM-DD`

`date` is optional (defaults to today). Supported range is **2001–2027**
(env-overridable via `LECTIONARY_MIN_YEAR` / `LECTIONARY_MAX_YEAR`); a date
outside it returns HTTP 400 with a message explaining the current range. Example:

```bash
curl "http://127.0.0.1:5001/readings?date=2026-06-01"
```

```json
{
  "Date": "2026-06-01",
  "Liturgical Day": "Saints Hripsime and her companions",
  "Season": "After Pentecost",
  "Readings": {
    "Old Testament": ["Proverbs 31.29-31", "Isaiah 61.10-62.3"],
    "Epistle": ["St. Paul's Epistle to the Romans 15.30-16.2"],
    "Gospel": ["Matthew 10.26-33"]
  },
  "ReadingsList": ["Proverbs 31.29-31", "Isaiah 61.10-62.3",
                   "St. Paul's Epistle to the Romans 15.30-16.2",
                   "Matthew 10.26-33"],
  "Source": "validated-table"
}
```

An unparseable date returns HTTP 400. `GET /` returns usage JSON, and
`GET /health` returns `{"status": "ok"}` for liveness checks.

## Deploy (Google Cloud Run)

The app is containerized (`Dockerfile`) and runs under gunicorn. Deploy from
source (Cloud Build builds the image):

```bash
gcloud run deploy lectionary --source . --region us-central1 \
  --allow-unauthenticated --memory 512Mi --min-instances 0 --max-instances 3
```

Scales to zero (~$0/month at < 1000 req/day). A custom domain is attached via
`gcloud run domain-mappings create`.

## Project layout

| Path | Purpose |
|------|---------|
| `app.py` | Flask app (one endpoint) |
| `lectionary.py` | Offline engine: calendar coordinates + table lookup |
| `lectionary_data.json` | Embedded, validated readings table (shipped) |
| `dev/` | **Dev-only** tooling: ground-truth fetcher, analysis, table builder, comparison harness. Not used at runtime. |

### Rebuilding / extending the table (dev)

```bash
python dev/bulk_fetch.py 2014-01-01 2027-12-31   # cache ground truth (network)
python dev/build_table.py                        # rebuild & validate -> lectionary_data.json
python dev/compare_app.py                        # runtime accuracy report
```

`sacredtradition.am` is used **only** as the development ground-truth source;
the shipped app never contacts it.

## Data provenance & attribution

The readings in `lectionary_data.json` are **distilled and cross-year validated**
from the authoritative Tōnatsooyts (Տօնացոյց) and Ճաշոց of the Armenian Church.
[sacredtradition.am](https://www.sacredtradition.am/) was used **only during
development** as the ground-truth source for building and validating the table; it
is never contacted at runtime, and its raw cache (`dev/reference_data/`) is not
distributed with this repository. The distilled table is provided for reference and
study — for liturgical use, verify against authoritative published sources.

## License

Code and configuration in this repository are licensed under the
**Apache License 2.0** — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). The
underlying liturgical calendar and scripture readings are traditional works of the
Armenian Church and are not claimed as original authorship here; see *Data
provenance & attribution* above.
