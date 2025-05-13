# Use the slim Python base
FROM python:3.11-slim

# 1️⃣ Work from /srv (so we keep the same structure)
WORKDIR /srv

# 2️⃣ System deps for psycopg2, WeasyPrint, etc.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential libpq-dev libcairo2 libpango-1.0-0 \
      libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 \
      libffi-dev shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# 3️⃣ Copy & install Python deps from backend/requirements.txt
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4️⃣ Copy the backend code
COPY backend/ backend/

# 5️⃣ Ensure uploads folder exists for StaticFiles
RUN mkdir -p backend/uploaded_images

# 6️⃣ Expose & launch
WORKDIR /srv/backend
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]

