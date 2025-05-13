# Use official Python slim image
FROM python:3.11-slim

# Install system dependencies
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
    libffi-dev \
    shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /srv

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir python-dotenv

# Copy application code
COPY . .

# Prepare uploads folder
RUN mkdir -p uploaded_images

# Expose the port (Cloud Run injects $PORT)
EXPOSE 8080

# Start Uvicorn via shell so ${PORT} is expanded at runtime
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

