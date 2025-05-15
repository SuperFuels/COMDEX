# -----------------------------------------------------------------------------
# Dockerfile
# -----------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Install system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libffi-dev libpq-dev libjpeg-dev \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
      shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# Set working dir to /srv/backend so main.py & routes/ are in CWD
WORKDIR /srv/backend

# Copy all backend files (including main.py, routes/, etc.) into cwd
COPY backend/ ./

# Copy root requirements.txt (which includes python-dotenv) into cwd
COPY requirements.txt ./

# Install your Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Create uploads dir
RUN mkdir -p uploaded_images

EXPOSE 8080

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]

