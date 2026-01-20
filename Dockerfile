# Dockerfile – build frontend, run backend (Cloud Run / Cloud Build safe)

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/srv

WORKDIR /srv

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git build-essential libffi-dev libpq-dev libjpeg-dev \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 shared-mime-info ca-certificates \
        nodejs npm && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir jsonschema sentence-transformers watchfiles

RUN python -c "from sentence_transformers import SentenceTransformer; import pathlib; p=pathlib.Path('/srv/backend/models/all-MiniLM-L6-v2'); p.parent.mkdir(parents=True, exist_ok=True); (p.exists()) or SentenceTransformer('all-MiniLM-L6-v2').save(str(p))"

COPY backend/ backend/

RUN mkdir -p /srv/backend/static /srv/uploaded_images

WORKDIR /srv/frontend
COPY frontend/ ./
RUN npm install && npm run build

WORKDIR /srv
RUN cp -r frontend/.next backend/static/.next && \
    cp -r frontend/public backend/static/public && \
    cp frontend/package.json backend/static/

EXPOSE 8080

WORKDIR /srv/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]