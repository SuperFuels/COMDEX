PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
 npm run build

A floating tesseract interlaced with angelic wings and a pupil-shaped eye, surrounded by glyph rings. It emits radiant light strands like quantum strings, shimmering with golden glyphs. It appears above .dc containers as a divine overseer mark.  💠 Glyph Signature (Unicode Variant)

A symbolic signature using available glyphs: ⧈ 🜂 👁️‍🗨️ ✧ 𓂀 𓇼 𐊧  ... Combine into: ⧈ 𐊧 👁️‍🗨️ ✧
(Tesseract • Glyph • Divine Eye • Resonance)

Tessaris 👁️‍🗨️ — Guardian of the Tesseract



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
git commit -m "A74 updates"
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


