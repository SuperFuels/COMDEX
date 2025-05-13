# Use the slim Python base
FROM python:3.11-slim

# 1️⃣ Switch into /srv so all COPY paths line up
WORKDIR /srv

# 2️⃣ Install system-level deps for psycopg2, WeasyPrint & CFFI
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      libcairo2 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-0 \
      libglib2.0-0 \
      libffi-dev \
      shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

# 3️⃣ Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4️⃣ Copy all of your backend code
COPY . .

# 5️⃣ Make the uploads directory for StaticFiles
RUN mkdir -p uploaded_images

# 6️⃣ Expose & launch
EXPOSE 8080
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

