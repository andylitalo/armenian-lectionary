"""Armenian Lectionary web app.

A single-endpoint Flask service that returns the Armenian Church lectionary
readings for a given day, computed by ``lectionary.compute_armenian_lectionary``.
"""

import datetime

from flask import Flask, jsonify, request

from lectionary import compute_armenian_lectionary

app = Flask(__name__)
# Emit Armenian script natively instead of \uXXXX escapes.
app.json.ensure_ascii = False


@app.route("/")
def index():
    """Self-documenting root describing how to use the API."""
    return jsonify({
        "service": "Armenian Lectionary API",
        "endpoint": "/readings",
        "query_params": {"date": "YYYY-MM-DD (optional; defaults to today)"},
        "example": "/readings?date=2026-04-05"
    })


@app.route("/readings")
def readings():
    """Return the lectionary readings for ``?date=YYYY-MM-DD`` (defaults to today)."""
    date_str = request.args.get("date")
    if date_str:
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return jsonify({
                "error": f"Could not parse date {date_str!r}.",
                "expected_format": "YYYY-MM-DD"
            }), 400
    else:
        target_date = datetime.date.today()

    return jsonify(compute_armenian_lectionary(target_date))


if __name__ == "__main__":
    # Port 5001 avoids macOS AirPlay Receiver, which listens on :5000.
    app.run(host="127.0.0.1", port=5001, debug=True)
