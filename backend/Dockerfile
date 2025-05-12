# backend/Dockerfile
# CACHE-BUST: 2025-05-12

FROM python:3.11-slim

WORKDIR /srv

# 1) OS-level deps for Postgres, WeasyPrint & CFFI
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      libcairo2 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-0 \
      libglib2.0-0 \
      libffi-dev \
      shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# 2) Copy & install your Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy only your backend code
COPY backend/ .

# 4) Expose the port and start Uvicorn (shell form so $PORT works)
EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
