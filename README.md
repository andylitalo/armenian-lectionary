# Armenian Lectionary

A self-contained, **offline** engine that returns the Armenian Church
(Տօնացոյց / Ճաշոց) scripture readings for any day. Use it two ways:

- **`pip install armenian-lectionary`** — import the engine into any Python app
  and generate readings offline (see [Use the engine offline](#use-the-engine-offline-python-package)).
- **Hosted API** — one HTTP endpoint on Google Cloud Run for network-tolerant or
  non-Python callers.

No network is used at runtime. The readings are produced by a calendar
**algorithm** combined with an embedded, cross-year-validated **data table**.

**Live:** the service is hosted on Google Cloud Run at
**https://lectionary.andylitalo.com** — try it:

```bash
curl "https://lectionary.andylitalo.com/readings"                 # today
curl "https://lectionary.andylitalo.com/readings?date=2026-04-05" # any date, 2001–2027
```

## How it works

The Armenian lectionary is one of the oldest in Christendom, and most of its
sanctoral is **movable** — commemorations are anchored to feasts, not civil
dates (e.g. Sts. Hripsime always falls on Easter + 57, so it drifts year to
year). The engine therefore works in two steps:

1. **Calendar framework** (`armenian_lectionary/engine.py`) computes each date's
   *liturgical coordinates* from the feast chain:
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

Validated against every day of **2001–2026** (9,495 days) from the authoritative
Tōnatsooyts. 2027 is also served and was validated separately as a held-out
forward year.

| Metric | Result |
|--------|--------|
| Coverage (any readings shipped) | **100.00%** (9,495 / 9,495) |
| Exact reading match | **99.21%** (9,420 / 9,495) |
| Wrong (validated tier hit but mismatched) | **0** |
| Validated-tier days (`validated-*`) | **9,273** (all exact) |
| Blank (no readings available) | **0 days** |

The hard invariant holds: a **validated** entry (`Source` `validated-table` /
`validated-composite`) is never wrong — 0 mismatches across all 9,495 days.
**Coverage is now complete**: every day 2001–2026 ships readings, and there are no
blank (`algorithmic-estimate`) days — the former summer gaps and winter "hinge"
(Advent → Theophany → pre-Lent) gap are resolved. The remaining ~0.8% that aren't
byte-exact all fall on the **labeled best-guess / source-derived tiers** (e.g.
`first-volume-cohort`, `generative-composite`), where the engine's reading differs
from the sacredtradition.am **test-oracle** — typically a versification /
verse-boundary convention on the same pericope, not a missing reading. Gate on
`Source` to include or exclude these. Regenerate these figures with
`python dev/compare_app.py`.

### Feast-name accuracy

Every result also carries the **feast/fast name of the day** in the `"Liturgical Day"`
field. As of **1.1.0** this name is locked against the same authoritative ground truth:
the engine's commemoration matches the source on **all 9,495 days of 2001–2026 (100%)**,
with no exceptions and no allowlist (`tests/test_feast.py`). The engine always serves a
concrete, source-matched name — never a placeholder.

The match is checked on the **commemoration component** — the saint/feast identity. The
source string also prepends a *year-varying* calendar-position label ("Nth day of
&lt;Season&gt;", "Nth Sunday after &lt;Anchor&gt;") that a static engine cannot
byte-reproduce, so that positional prefix is normalized out on **both** sides before
comparison (`dev/feast_names.py`); a small set of reviewed companion-enumeration and
transliteration variants are reconciled symmetrically (`dev/source_corrections.canonical_commem`).
Naming nuances may still be refined as experts review. Audit with `python dev/feast_audit.py`.

### Source fidelity & known typos

The engine treats the printed Տօնացոյց (Tōnatsooyts) as the **primary source** and
sacredtradition.am as a **test oracle** (see `dev/source_corrections.py`). Systematic
versification-convention differences are corrected on the source-derived tiers; confirmed
**typographical errors** in the printed source are catalogued in the digitization repo,
next to the source, at
[`grabar-ocr` `corpus/TYPOS.md`](https://github.com/andylitalo/grabar-ocr/blob/main/corpus/TYPOS.md),
and where a source typo would yield a wrong reading the engine ships the corrected value.

For example, the **eve of the Presentation of the Lord (Feb 13)** Proverbs reading is
printed in the Tōnatsooyts (First Volume p. 462) as `Առակ. Ը. 22 … վ. 24`
("Proverbs 8:22-24"), but its quoted endpoint «որ զճանապարհս իմ պահիցէ» is verbatim the
close of **Proverbs 8:34** (the singular «պահիցէ» distinguishes it from the near-identical
8:32) — a transposed digit, `24` for `34`. The engine ships the corrected
`Proverbs 8.22-34`, which sacredtradition renders unanimously (23/23 Feb-13 eve years,
26/26 Feb-14 feast years). See
[`grabar-ocr` `corpus/TYPOS.md`](https://github.com/andylitalo/grabar-ocr/blob/main/corpus/TYPOS.md)
for the full analysis.

### Roadmap

A complete engine covering the **entire 532-year Great Paschal Cycle** — the full
period after which the Armenian movable calendar repeats — is forthcoming. It
awaits validation against the Տօնացոյց (Tōnatsooyts), currently being transcribed
and translated in the [grabar-ocr](https://github.com/andylitalo/grabar-ocr)
repository (a pipeline for digitizing Grabar / Classical Armenian texts). Until
that validation lands, the served range stays within the tested **2001–2027**
window.

## Setup & run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt   # web layer (Flask, gunicorn)
pip install -e .                  # the lectionary engine package
python app.py                     # serves http://127.0.0.1:5001
```

## Endpoint

### `GET /readings?date=YYYY-MM-DD`

`date` is optional (defaults to today). Supported range is **2001–2027**
(env-overridable via `LECTIONARY_MIN_YEAR` / `LECTIONARY_MAX_YEAR`); a date
outside it returns HTTP 400 with a message explaining the current range. Example:

```bash
curl "https://lectionary.andylitalo.com/readings?date=2026-06-01"
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

Requests are rate-limited per client IP (default **60/min, 600/hour**);
exceeding a limit returns HTTP 429. Limits are configurable via
`LECTIONARY_RATE_LIMITS`.

## Use the engine offline (Python package)

Don't want to depend on the hosted API — e.g. for a fully offline app? Install
the engine as a package. It has **no third-party dependencies** (Python 3.9+
standard library only), and all the readings data (the validated table plus the
source-derived saint & continua data) ships **inside the wheel**, so nothing is
fetched at runtime:

```bash
pip install armenian-lectionary
```

```python
import datetime
import armenian_lectionary

reading = armenian_lectionary.compute_armenian_lectionary(datetime.date(2026, 4, 5))
print(reading["Liturgical Day"])   # RESURRECTION OF OUR LORD JESUS CHRIST (Easter Sunday)
print(reading["ReadingsList"])     # ['John 20.1-18', 'Acts of the Apostles 1.1-8', ...]
```

The distribution name is **`armenian-lectionary`**; the import name is
**`armenian_lectionary`**. The public API is intentionally small —
`compute_armenian_lectionary(date)` and `calculate_gregorian_easter(year)`.
(Internal calendar helpers and constants remain importable from
`armenian_lectionary.engine` if you need them.)

### Command line

The package installs an `armenian-lectionary` console script that prints the
readings as JSON in native Armenian script:

```bash
armenian-lectionary                # today
armenian-lectionary 2026-04-05     # any date
python -m armenian_lectionary.cli 2026-04-05   # equivalent
```

### Gating on `Source` / `Confidence`

`compute_armenian_lectionary(date)` always returns a `dict` and never raises or
makes a network call. It will compute **any** date — the 2001–2027 range check is
a property of the API layer (`app.py`), not the engine. Because the output blends
tiers of differing certainty, **gate on the `Source` field** (and `Confidence`
where present) rather than assuming every result is authoritative:

- `validated-*` — cross-year-validated against the authoritative Tōnatsooyts;
  never wrong across all 9,495 tested days.
- `second-volume-cycle` / `generative-continua` / other generative tiers —
  best-guess readings derived from the source laydown, flagged as such.
- `algorithmic-estimate` — no readings confidently derivable; `"ReadingsList"`
  is empty. Gate on an empty list rather than expecting an error.

See the `Source` values under [Accuracy](#accuracy) for the full picture.

### License & data provenance

The package ships `LICENSE` (Apache-2.0) and `NOTICE` in its distribution
metadata. The bundled readings are traditional works of the Armenian Church and
are not claimed as original authorship — see
[Data provenance & attribution](#data-provenance--attribution) below.

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
| `pyproject.toml` | Package metadata + build config (hatchling); defines the `armenian-lectionary` distribution and console script. |
| `armenian_lectionary/` | The installable Python package. |
| `armenian_lectionary/engine.py` | Offline engine: calendar coordinates + table lookup. Public entry: `compute_armenian_lectionary`. |
| `armenian_lectionary/cli.py` | `armenian-lectionary` console entry point. |
| `armenian_lectionary/data/lectionary_data.json` | Embedded, validated readings table (shipped in the wheel). |
| `armenian_lectionary/data/{second_volume_cycles,saint_readings,saint_schedule,continua_sequence}.json` | Shipped source-derived saint & continua data (Tōnats'oyts Second Volume laydown + Fast-of-Assumption continua) feeding the `second-volume-cycle` and `generative-continua` tiers. |
| `app.py` | Flask app (one endpoint); imports the package. |
| `Dockerfile` | Container image for Cloud Run (`pip install .` + gunicorn). |
| `dev/` | **Dev-only** tooling: ground-truth fetcher, analysis, table builder, comparison harness. Not used at runtime; not shipped in the package. |

### Rebuilding / extending the table (dev)

```bash
python dev/bulk_fetch.py 2014-01-01 2027-12-31   # cache ground truth (network)
python dev/build_table.py                        # rebuild & validate -> armenian_lectionary/data/lectionary_data.json
python dev/compare_app.py                        # runtime accuracy report
```

`sacredtradition.am` is used **only** as the development ground-truth source;
the shipped app never contacts it.

## Data provenance & attribution

The readings in `lectionary_data.json` are **distilled and cross-year validated**
against the authoritative Տօնացոյց (Tōnatsooyts) and Ճաշոց of the Armenian Church.

**Sources:**

- **Primary — the Տօնացոյց itself:** the *4th edition*, printed at the **St. James
  Press (Tparan Srbots Hakobeants), Jerusalem, 1915**. This is the canonical rubric
  the readings must be derivable from.
- **Development test-oracle — [sacredtradition.am](https://www.sacredtradition.am/):**
  used **only during development** to build and validate the table. It is never
  contacted at runtime, and its raw cache (`dev/reference_data/`) is not distributed
  with this repository.

**Discrepancy policy.** A few slight discrepancies have been found between
sacredtradition.am and the printed Տօնացոյց (mostly versification / verse-boundary
conventions on the same pericope). Where a discrepancy is confirmed, the engine
**defaults to the Տօնացոյց** as the authoritative source and treats the scrape as a
test oracle only. These corrections are recorded, with per-reading rationale, in
[`dev/source_corrections.py`](dev/source_corrections.py) (see also the working
record in [`reports/lectionary_disagreements.md`](reports/lectionary_disagreements.md)).
**Further investigation of these discrepancies is in progress.**

The distilled table is provided for reference and study — for liturgical use, verify
against authoritative published sources.

## License

Code and configuration in this repository are licensed under the
**Apache License 2.0** — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). The
underlying liturgical calendar and scripture readings are traditional works of the
Armenian Church and are not claimed as original authorship here; see *Data
provenance & attribution* above.
