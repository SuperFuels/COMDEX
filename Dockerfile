FROM python:3.11-slim AS base

# --- Environment Configuration ---
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/srv/backend

# --- Set Working Directory to /srv ---
WORKDIR /srv

# --- Install System Dependencies ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git build-essential libffi-dev libpq-dev libjpeg-dev \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 shared-mime-info ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# --- Install Python Dependencies ---
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# --- Copy Backend Codebase ---
COPY backend/ backend/

# --- Ensure Static and Upload Folders Exist ---
RUN mkdir -p /srv/backend/static /srv/uploaded_images

# --- Copy Frontend Static Build ---
COPY frontend/out/ backend/static/

# --- Expose App Port ---
EXPOSE 8080

# --- Launch App ---
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]