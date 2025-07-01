FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /srv/backend

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      git build-essential libffi-dev libpq-dev libjpeg-dev \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      libgdk-pixbuf2.0-0 shared-mime-info ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Create upload folder and static folder (static will be filled by next line)
RUN mkdir -p /srv/backend/static /srv/uploaded_images

# Copy the frontend static build into /srv/backend/static (must match FastAPI mount path)
COPY frontend/out/ ./static/

ENV PYTHONPATH=/srv/backend

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]