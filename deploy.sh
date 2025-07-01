set -e
git add .
git commit -m "chore: deploy 🚀"
git push origin main

gcloud builds submit . --tag gcr.io/swift-area-459514-d1/comdex:latest

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
cd frontend
npm ci
npm run build
firebase deploy --only hosting
cd ..
