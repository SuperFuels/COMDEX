# ← place this Dockerfile at the repo root, next to backend/
FROM python:3.11-slim

# 1) Switch into /srv
WORKDIR /srv

# 2) Install system deps for psycopg2, WeasyPrint, etc.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libpq-dev libcairo2 libpango-1.0-0 \
      libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 \
      libffi-dev shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# 3) Copy & install Python deps from backend/requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy the entire backend/ folder into /srv
COPY backend/ ./

# 5) Ensure uploads dir exists
RUN mkdir -p uploaded_images

# 6) Expose & launch via shell so $PORT expands
EXPOSE 8080
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"

