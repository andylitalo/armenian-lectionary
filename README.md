# Armenian Lectionary API

A tiny [Flask](https://flask.palletsprojects.com/) web service with **one endpoint**
that returns the Armenian Church (Tonatsooyts) lectionary readings for a given day.

The liturgical day and its scripture readings are computed entirely offline in
[`lectionary.py`](./lectionary.py). The cycle is anchored on Easter Sunday — calculated
with the Meeus/Jones/Butcher algorithm — plus a set of fixed immovable feasts
(Theophany, Annunciation, …) and movable landmark Sundays (Assumption, Exaltation
of the Cross).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

The server starts on <http://127.0.0.1:5001> (port 5001 avoids macOS AirPlay,
which uses 5000).

## Endpoint

### `GET /readings`

| Query param | Required | Description                                |
|-------------|----------|--------------------------------------------|
| `date`      | no       | Day to look up, `YYYY-MM-DD`. Defaults to today. |

**Examples**

```bash
curl "http://127.0.0.1:5001/readings?date=2026-04-05"   # Easter Sunday
curl "http://127.0.0.1:5001/readings?date=2026-02-16"   # First Day of Great Lent
curl "http://127.0.0.1:5001/readings?date=2026-05-01"   # Hinank (Eastertide)
curl "http://127.0.0.1:5001/readings?date=2026-01-06"   # Theophany & Nativity
curl "http://127.0.0.1:5001/readings"                    # today
```

**Sample response** (`?date=2026-04-05`)

```json
{
  "Date": "2026-04-05",
  "Liturgical Day": "Feast of the Glorious Resurrection / Easter Sunday (Սուրբ Զատիկ)",
  "Classification": "Feast of Feasts / Dominical",
  "Readings": {
    "Epistle (Liturgy)": "Acts 1:1-8",
    "Gospel (Liturgy)": "John 1:1-17",
    "Gospel (Vespers)": "Luke 24:13-35"
  }
}
```

An unparseable `date` returns HTTP `400` with a JSON error.

`GET /` returns a short JSON description of the API.

## Known limitation

The algorithm is a partial/demo rubric: major feasts, Great Lent, Holy Week, and the
Hinank (Eastertide) cycle are mapped explicitly, but **ordinary non-feast days** return
placeholder `"Notice"` text rather than the exact daily pericopes. For authoritative
readings on every day, a future version could source data from
[sacredtradition.am](https://www.sacredtradition.am/Calendar/).
