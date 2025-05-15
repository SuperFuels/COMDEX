# Use official Python slim image
FROM python:3.11-slim

# Ensure Python output is sent straight to the terminal (no buffering)
ENV PYTHONUNBUFFERED=1

# Install system dependencies for Web3, Postgres, WeasyPrint, etc.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libpq-dev \
    libjpeg-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /srv

# Copy and install Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy your FastAPI app sources
COPY backend/ .

# Prepare uploads folder
RUN mkdir -p uploaded_images

# Expose the port Cloud Run will use (informational)
EXPOSE 8080

# Launch Uvicorn so we bind to $PORT (defaults to 8080)
ENTRYPOINT ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

