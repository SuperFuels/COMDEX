# Dockerfile – build frontend + run backend on Cloud Run

FROM python:3.11-slim

# --- Environment Configuration ---
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/srv

# --- Base working directory (matches repo root layout) ---
WORKDIR /srv

# --- System dependencies ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git build-essential libffi-dev libpq-dev libjpeg-dev \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 shared-mime-info ca-certificates \
        nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# --- Python deps ---
COPY backend/requirements.txt ./requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir jsonschema sentence-transformers

# --- Preload SentenceTransformer model ---
RUN mkdir -p /srv/backend/models && \
    python - <<'EOF'
from sentence_transformers import SentenceTransformer
import os
model_path = "/srv/backend/models/all-MiniLM-L6-v2"
if not os.path.exists(model_path):
    os.makedirs(model_path, exist_ok=True)
    print("Downloading all-MiniLM-L6-v2 model ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    model.save(model_path)
    print(f"Model saved to {model_path}")
else:
    print(f"Model already present at {model_path}")
EOF

# --- Backend code ---
COPY backend/ backend/

# --- Static / uploads ---
RUN mkdir -p /srv/backend/static /srv/uploaded_images

# --- Frontend build ---
WORKDIR /srv/frontend
COPY frontend/ ./

RUN npm install && npm run build

# --- Copy Next.js build into backend static ---
WORKDIR /srv
RUN cp -r frontend/.next backend/static/.next && \
    cp -r frontend/public backend/static/public && \
    cp frontend/package.json backend/static/

# --- Expose app port for Cloud Run ---
EXPOSE 8080

# --- Runtime working dir: repo root (/srv), like local ---
WORKDIR /srv

# --- Start FastAPI app (same as local: backend.main:app) ---
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]