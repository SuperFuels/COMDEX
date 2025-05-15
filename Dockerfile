# Dockerfile

# 1) Base image
FROM python:3.11-slim

# 2) No buffering
ENV PYTHONUNBUFFERED=1

# 3) System deps
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

# 4) Work dir
WORKDIR /srv

# 5) Copy & install Python deps from the root requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6) Copy all your code (including the backend/ folder)
COPY . .

# 7) Prepare uploads
RUN mkdir -p backend/uploaded_images

# 8) Expose for Cloud Run
EXPOSE 8080

# 9) Entrypoint: run the app in backend/main.py
ENTRYPOINT ["sh","-c","exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

