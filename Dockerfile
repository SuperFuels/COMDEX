# Use official Python slim image
FROM python:3.11-slim

# Make Python output unbuffered (logs immediately)
ENV PYTHONUNBUFFERED=1

# System deps for Web3, Postgres, WeasyPrint, etc.
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

# Set workdir
WORKDIR /srv

# 1️⃣ Copy & install Python deps
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2️⃣ Copy your entire backend app
COPY backend/ backend/

# 3️⃣ Ensure uploads dir exists
RUN mkdir -p uploaded_images

# 4️⃣ Expose port (Cloud Run uses $PORT)
EXPOSE 8080

# 5️⃣ Launch Uvicorn pointing at backend/main.py
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]

