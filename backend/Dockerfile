# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /srv

# install OS packages for psycopg2, WeasyPrint & CFFI
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

# copy & install your backend Python deps
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# copy only the backend code into /srv
COPY backend/ .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]
