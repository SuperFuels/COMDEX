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
    shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /srv

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir python-dotenv

# Copy the application code
COPY . .

# Prepare uploads folder
RUN mkdir -p uploaded_images

# Expose the port Cloud Run will use
EXPOSE 8080

# Start using start.py (resolves $PORT dynamically)
CMD ["python", "start.py"]

