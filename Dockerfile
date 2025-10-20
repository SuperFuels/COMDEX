# ───────────────────────────────────────────────
# 🧩 Stage 1 – Builder (has apt, npm, pip, etc.)
# ───────────────────────────────────────────────
FROM gcr.io/google.com/cloudsdktool/cloud-sdk:slim AS builder

# --- Environment Configuration ---
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/srv/backend

# --- Working Directory ---
WORKDIR /srv

# --- Install System Dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    git build-essential libffi-dev libpq-dev libjpeg-dev \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    shared-mime-info ca-certificates nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# --- Create & Activate Virtual Environment ---
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# --- Install Python Dependencies ---
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Copy Backend Codebase ---
COPY backend/ backend/

# --- Build Frontend ---
WORKDIR /srv/frontend
COPY frontend/ ./
RUN npm install && npm run build

# --- Copy Next.js Build Output into Backend Static ---
WORKDIR /srv
RUN mkdir -p backend/static backend/static/.next backend/static/public && \
    cp -r frontend/.next backend/static/.next && \
    cp -r frontend/public backend/static/public && \
    cp frontend/package.json backend/static/

# ───────────────────────────────────────────────
# 🧩 Stage 2 – Runtime (Distroless = Tiny + Secure)
# ───────────────────────────────────────────────
FROM gcr.io/distroless/python3-debian12

# --- Environment Configuration ---
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONPATH=/srv/backend \
    PATH="/opt/venv/bin:$PATH"

# --- Working Directory ---
WORKDIR /srv

# --- Copy Application from Builder ---
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /srv/backend /srv/backend

# --- Ensure Static Dirs Exist ---
RUN mkdir -p /srv/backend/static /srv/uploaded_images

# --- Expose App Port ---
EXPOSE 8080

# --- Launch App ---
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]