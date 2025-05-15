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

# Set working dir
WORKDIR /srv/backend

# Copy code + install deps
COPY backend/ ./
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create uploads dir
RUN mkdir -p uploaded_images

# Expose port (doc only)
EXPOSE 8080

# Force Uvicorn to bind to 8080
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

