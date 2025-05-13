# Use Python slim base
FROM python:3.11-slim

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential libpq-dev libcairo2 libpango-1.0-0 \
      libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 \
      libffi-dev shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

# Set working dir
WORKDIR /srv

# Copy only requirements and install first (cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create uploads dir (if your app needs it)
RUN mkdir -p uploaded_images

# Expose port and use JSON form to avoid shell signal issues
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

