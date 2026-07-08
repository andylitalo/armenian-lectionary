# Armenian Lectionary API — container image for Cloud Run.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime files only (the engine, the web app, and the validated table).
COPY app.py lectionary.py lectionary_data.json ./

# Cloud Run provides $PORT (default 8080); default it for local `docker run`.
ENV PORT=8080

# Bind 0.0.0.0 so Cloud Run can route to the container. 2 workers x 4 threads
# is ample for < 1000 req/day; each worker reloads the ~1.1 MB table (trivial).
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 app:app
