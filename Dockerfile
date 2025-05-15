# ────────── Dockerfile ──────────
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libffi-dev libpq-dev libjpeg-dev \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
      shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# 1) copy & install your requirements
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2) smoke-test that dotenv really is installed
RUN python - <<'EOF'
import dotenv
print("✅ python-dotenv:", dotenv.__version__)
EOF

# 3) copy the rest of your code
COPY backend/ backend/
COPY main.py .

RUN mkdir -p uploaded_images
EXPOSE 8080

# point uvicorn at your app in backend/main.py
ENTRYPOINT ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

