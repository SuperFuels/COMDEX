# ─────────────────────────────────────────────────────────────────────────────
#  Dockerfile (at repo root)
# ─────────────────────────────────────────────────────────────────────────────

# ─── 0) Use a Python runtime as our base ─────────────────────────────
FROM python:3.11-slim AS base

# Ensure Python output is unbuffered and set default PORT to 8080
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /srv

# ─── 1) Install system dependencies ──────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git build-essential libffi-dev libpq-dev libjpeg-dev \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-0 shared-mime-info ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# ─── 2) Copy & install Python dependencies ───────────────────────────
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── 3) Copy backend application code ────────────────────────────────
COPY backend/ ./backend

# ─── 4) Ensure required runtime folders exist ────────────────────────
RUN mkdir -p /srv/backend/static /srv/uploaded_images

# ─── 5) Adjust PYTHONPATH so Uvicorn can find the backend ────────────
ENV PYTHONPATH=/srv/backend

# ─── 6) Expose port and start the server ─────────────────────────────
EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]