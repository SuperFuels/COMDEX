# -----------------------------------------------------------------------------
# Dockerfile
# -----------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential libffi-dev libpq-dev libjpeg-dev \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
      shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

# 1) Install Python deps
WORKDIR /srv/backend
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy application code
COPY backend/ ./

# 3) Create uploads dir
RUN mkdir -p uploaded_images

# 4) Expose port and launch Uvicorn (JSON form, hard-coded 8080)
EXPOSE 8080
ENTRYPOINT ["uvicorn","main:app","--host","0.0.0.0","--port","8080"]

