#!/usr/bin/env bash
set -e

# 1) Commit & push
git add .
git commit -m "chore: deploy 🚀"
git push origin main

# 2) Build & push backend image
gcloud builds submit . \
  --tag gcr.io/swift-area-459514-d1/comdex:latest

# 3) Deploy backend to Cloud Run
gcloud run deploy comdex-api \
  --project=swift-area-459514-d1 \
  --region=us-central1 \
  --platform=managed \
  --image=gcr.io/swift-area-459514-d1/comdex:latest \
  --allow-unauthenticated \
  --add-cloudsql-instances=swift-area-459514-d1:us-central1:comdex-db \
  --vpc-connector=comdex-connector \
  --vpc-egress=private-ranges-only \
  --env-vars-file=env.yaml \
  --timeout=300s

# 4) Build & deploy frontend
cd frontend
npm ci
npm run build
firebase deploy --only hosting
cd ..
