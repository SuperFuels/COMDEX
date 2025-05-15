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

# Set working directory inside the container
WORKDIR /srv

# Copy and install Python dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only your FastAPI code into /srv
COPY backend/ .

# Prepare uploads folder
RUN mkdir -p uploaded_images

# Expose the port Cloud Run will use (informational)
EXPOSE 8080

# Launch Uvicorn on main:app (since main.py is now at /srv/main.py)
ENTRYPOINT ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

