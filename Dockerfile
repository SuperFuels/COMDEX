# Use official Python slim image
FROM python:3.11-slim

# Don’t buffer Python stdout/stderr
ENV PYTHONUNBUFFERED=1

# Install system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libpq-dev libjpeg-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# Work from /srv/backend so routes/ and main.py are on the PYTHONPATH by default
WORKDIR /srv/backend

# Copy your backend code
COPY backend/ . 

# Copy root requirements.txt (which includes python-dotenv, etc.)
COPY requirements.txt .  

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Create your uploads dir
RUN mkdir -p uploaded_images

# Expose Cloud Run port
EXPOSE 8080

# Launch Uvicorn against your main.py
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]

