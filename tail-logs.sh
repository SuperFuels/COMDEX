set -e
gcloud beta run services logs tail comdex-api \
  --project=swift-area-459514-d1 \
  --region=us-central1
