# 1) Base image
FROM python:3.11-slim

# 2) No buffering on stdout/stderr
ENV PYTHONUNBUFFERED=1

# 3) Install system deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libffi-dev libpq-dev libjpeg-dev \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-0 shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# 4) Set workdir to /srv
WORKDIR /srv

# 5) Install exactly the backend requirements
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 6) Copy in your backend code
COPY backend/ backend/

# 7) Switch into the backend folder so imports like "from routes.auth" work
WORKDIR /srv/backend

# 8) Prepare upload dir
RUN mkdir -p uploaded_images

# 9) Expose port
EXPOSE 8080

# 10) Launch Uvicorn, pointing at main:app
ENTRYPOINT ["sh","-c","exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

