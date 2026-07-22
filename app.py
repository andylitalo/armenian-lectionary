"""Armenian Lectionary web app.

A single-endpoint Flask service that returns the Armenian Church lectionary
readings for a given day, computed by
``armenian_lectionary.compute_armenian_lectionary``.
"""

import datetime
import os

from flask import Flask, jsonify, request
from flask_limiter import Limiter

from armenian_lectionary import compute_armenian_lectionary, SUPPORTED_LANGUAGES

# Supported date range. Readings are validated for 2001-2027 so far; the range
# is env-overridable so it can widen later without a code change.
MIN_YEAR = int(os.environ.get("LECTIONARY_MIN_YEAR", "2001"))
MAX_YEAR = int(os.environ.get("LECTIONARY_MAX_YEAR", "2027"))

# Per-client rate limits (abuse protection). Semicolon-separated, env-overridable.
RATE_LIMITS = [
    part.strip()
    for part in os.environ.get(
        "LECTIONARY_RATE_LIMITS", "60 per minute;600 per hour"
    ).split(";")
    if part.strip()
]
# Storage for the limiter's counters. Defaults to per-process memory, which keeps
# hosting cost at ~$0. Counters are NOT shared across gunicorn workers or Cloud Run
# instances, so effective limits scale with (workers x instances) -- acceptable for
# basic abuse protection at low volume. For exact global limits, set this to a shared
# backend, e.g. LECTIONARY_RATELIMIT_STORAGE_URI=redis://<memorystore-host>:6379.
RATE_LIMIT_STORAGE_URI = os.environ.get("LECTIONARY_RATELIMIT_STORAGE_URI", "memory://")

app = Flask(__name__)
# Emit Armenian script natively instead of \uXXXX escapes.
app.json.ensure_ascii = False


def _client_ip():
    """Real client IP. Cloud Run / proxies put it first in X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


limiter = Limiter(
    key_func=_client_ip,
    default_limits=RATE_LIMITS,
    storage_uri=RATE_LIMIT_STORAGE_URI,
    app=app,
)


@app.errorhandler(429)
def ratelimit_exceeded(exc):
    """Return the rate-limit rejection as JSON, consistent with other errors."""
    return jsonify({
        "error": "Rate limit exceeded.",
        "detail": str(getattr(exc, "description", exc)),
    }), 429


@app.route("/")
def index():
    """Self-documenting root describing how to use the API."""
    return jsonify({
        "service": "Armenian Lectionary API",
        "endpoint": "/readings",
        "query_params": {
            "date": "YYYY-MM-DD (optional; defaults to today)",
            "language": "en (default) or hy for Armenian (optional; alias: lang)",
        },
        "supported_range": {"min_year": MIN_YEAR, "max_year": MAX_YEAR},
        "example": "/readings?date=2026-04-05&language=hy"
    })


@app.route("/health")
@limiter.exempt
def health():
    """Liveness/readiness check."""
    return jsonify({"status": "ok"})


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

    if not (MIN_YEAR <= target_date.year <= MAX_YEAR):
        return jsonify({
            "error": f"Date {target_date.isoformat()} is outside the supported range.",
            "supported_range": {"min_year": MIN_YEAR, "max_year": MAX_YEAR},
            "note": (f"Readings are currently validated for {MIN_YEAR}-{MAX_YEAR}; "
                     "the range is planned to expand in the future.")
        }), 400

    language = request.args.get("language", request.args.get("lang", "en"))
    if language not in SUPPORTED_LANGUAGES:
        return jsonify({
            "error": f"Unsupported language {language!r}.",
            "supported_languages": list(SUPPORTED_LANGUAGES),
        }), 400

    return jsonify(compute_armenian_lectionary(target_date, language=language))


if __name__ == "__main__":
    # Port 5001 avoids macOS AirPlay Receiver, which listens on :5000.
    app.run(host="127.0.0.1", port=5001, debug=True)
