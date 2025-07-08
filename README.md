# 1. Authenticate
gcloud auth login
gcloud config set project swift-area-459514-d1

# 2. Build & push your backend image
gcloud builds submit . --tag gcr.io/swift-area-459514-d1/comdex:latest

# 3. Deploy to Cloud Run
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

git add .
git commit -m "Full update to fix everything in AION"
git push origin main


gcloud builds submit --config cloudbuild.yaml .

# 1. Double-check you’re on main
git checkout main

# 2. See what’s changed
git status

# 3. Stage absolutely everything (new, modified, deleted)
git add -A

# 4. Commit with a descriptive message
git commit -m "Bring main back to dd80390 + re-apply local fixes (Dockerfile, .dockerignore, siwe, firebase.json, etc.)"

# 5. Push up to GitHub
git push origin main --force


rm -rf node_modules package-lock.json yarn.lock
npm cache clean --force

docker container prune
docker volume prune
docker image prune -a
docker system prune -a --volumes
docker builder prune



python backend/scripts/create_agent.py nova 

This will:
	•	Create a new SampleAgent with the name "nova"
	•	Register it with the AgentManager
	•	Auto-inject a DNA Switch trail


