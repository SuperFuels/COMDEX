# ─────────────────────────────────────────────────────────────
#  Dockerfile (at repo root)
# ─────────────────────────────────────────────────────────────

# 0. Use official slim Python image
FROM python:3.11-slim AS base

# 1. Environment setup
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /srv

# 2. Install system-level dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git build-essential libffi-dev libpq-dev libjpeg-dev \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-0 shared-mime-info ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 3. Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copy backend code
COPY backend/ ./backend

# 5. Copy static files (exported Next.js app)
COPY frontend/out/ ./backend/static/

# 6. Ensure required folders exist (images, static)
RUN mkdir -p /srv/backend/static /srv/uploaded_images

# 7. Set Python path
ENV PYTHONPATH=/srv/backend

# 8. Expose port for Cloud Run
EXPOSE 8080

# 9. Start server on Cloud Run’s expected port
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]