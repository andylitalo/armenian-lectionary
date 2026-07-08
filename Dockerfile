# Armenian Lectionary API — container image for Cloud Run.
FROM python:3.12-slim

WORKDIR /app

# Install web-layer dependencies first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the lectionary engine as a package. This brings in the engine plus all
# five bundled data files (validated table + Second Volume saint laydown +
# Fast-of-Assumption continua) that feed the second-volume-cycle and
# generative-continua tiers. The engine has no third-party deps.
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY armenian_lectionary/ ./armenian_lectionary/
RUN pip install --no-cache-dir .

# The web app is the only loose source file at runtime.
COPY app.py ./

# Cloud Run provides $PORT (default 8080); default it for local `docker run`.
ENV PORT=8080

# Bind 0.0.0.0 so Cloud Run can route to the container. 2 workers x 4 threads
# is ample for < 1000 req/day; each worker reloads the ~1.1 MB table (trivial).
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 app:app
