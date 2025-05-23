# Dockerfile

# ─── base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# make sure Python output is unbuffered, and default PORT to 8080
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# ─── 1) Install system deps (including git for pip‐git installs) ───────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git \
      build-essential \
      libffi-dev \
      libpq-dev \
      libjpeg-dev \
      libcairo2 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-0 \
      shared-mime-info \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ─── 2) Copy & install Python deps ──────────────────────────────────────────────
WORKDIR /srv
COPY backend/requirements.txt ./

# bump pip, install everything, then verify SIWE is present
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip show siwe

# ─── 3) Copy your app ───────────────────────────────────────────────────────────
COPY backend/ ./backend

# ─── 4) Make sure Uvicorn can import your package ──────────────────────────────
ENV PYTHONPATH=/srv/backend

# ─── 5) Expose port & start server ─────────────────────────────────────────────
EXPOSE $PORT
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT --proxy-headers"]
