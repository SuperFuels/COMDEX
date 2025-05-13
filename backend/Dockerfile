FROM python:3.11-slim

# install OS deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential libpq-dev libcairo2 libpango-1.0-0 \
      libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 \
      libffi-dev shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# 1️⃣ Copy & install Python deps
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 2️⃣ Copy all your backend code
COPY . ./

# 3️⃣ Ensure uploads folder exists
RUN mkdir -p uploaded_images

EXPOSE 8080
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"

