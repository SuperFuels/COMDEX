STICKEY / COMDEX Platform — Living Documentation
Last updated: May 2025

⸻

1. Overview

COMDEX (branded STICKEY, ticker $GLU) is a next-gen B2B commodity-trading platform combining:
	•	AI: autonomous agents for supplier matching & contract drafting
	•	Blockchain: on-chain escrow & NFT certificates
	•	Crypto-native: wallet binding, swap panel, token flows

Mission: Revolutionize global commodity trade with trust, automation, transparency.
V1 Target: Whey Protein (EU, USA, India, NZ)

⸻

2. Architecture

[ Next.js Frontend (Firebase Hosting) ]
            ↕
[ FastAPI Backend (Cloud Run) ]
            ↕
[ PostgreSQL (Cloud SQL) ]

	•	Frontend: Next.js + Tailwind + TypeScript → next build → next export → frontend/out → Firebase Hosting with rewrites to Cloud Run for /api/**.
	•	Backend: FastAPI + SQLAlchemy + Pydantic → Docker → Cloud Run → connects to Cloud SQL (Postgres).
	•	Blockchain: Polygon Amoy testnet for escrow; COMDEX chain planned.
	•	AI: OpenAI LLM integrations under /agent & /contracts/generate.

⸻

3. Authentication & Roles

3.1 Email/Password + JWT
	•	POST /auth/register → create user (bcrypt-hash), assign role.
	•	POST /auth/login → validate credentials → issue JWT.
	•	Protected routes use Depends(get_current_user) + role checks.
	•	Frontend: useAuthRedirect(requiredRole?) enforces login & redirects.

3.2 SIWE Login & Account Switching
	1.	GET /auth/nonce?address=… → returns full EIP-4361 message.
	2.	User signs via personal_sign (MetaMask).
	3.	POST /auth/verify → { message, signature }.
	4.	Backend uses SiweMessage.parse_message() → verifies → upserts User → returns { token, role }.
	5.	Frontend stores localStorage.setItem('token', token) and sets Axios default.
	6.	Disconnects tracked in localStorage.manualDisconnect.

⸻

4. Database Schemas

4.1 Users

Column
Type
Notes
id
integer
PK
name
varchar
email
varchar
unique; nullable if wallet-only
password_hash
varchar
nullable if wallet-only
role
varchar
enum (admin / supplier / buyer)
wallet_address
varchar
EIP-55; nullable
created_at
timestamp
default NOW()
updated_at
timestamp


4.2 Products

Column
Type
Notes
id
integer
PK
owner_email
varchar
FK → users.email
title
text
description
text
price_per_kg
numeric
origin_country
text
category
text
image_url
text
change_pct
numeric
price change %
rating
numeric
user rating
batch_number
text
optional
trace_id
text
optional
certificate_url
text
NFT cert viewer
blockchain_tx_hash
text
escrow Tx hash
created_at
timestamp


4.3 Deals

Column
Type
Notes
id
integer
PK
buyer_id
integer
FK → users.id
supplier_id
integer
FK → users.id
product_id
integer
FK → products.id
quantity_kg
numeric
total_price
numeric
status
varchar
enum (negotiation → confirmed → completed)
created_at
timestamp
pdf_url
text
generated PDF


4.4 Contracts

Column
Type
Notes
id
integer
PK
prompt
text
LLM prompt
generated_contract
text
HTML/Markdown
status
varchar
draft / final
pdf_url
text
PDF export
nft_metadata
JSONB
stub
created_at
timestamp

5. Backend Endpoints
	•	Auth (/auth): register, login, nonce, verify, profile, role
	•	Products (/products): CRUD & listing
	•	Deals (/deals): create & status
	•	Contracts (/contracts): generate & PDF
	•	Admin (/admin): full CRUD
	•	Users (/users): wallet binding

See each router’s docstrings for full path, payload, response.

⸻

6. Frontend Structure

6.1 Pages

/              → Marketplace  
/search        → Search results  
/products/[id] → Product detail  
/products/[id]/sample  
/products/[id]/zoom  
/products/create  
/products/edit/[id]  
/register      → Role selection & signup  
/login         → Email/password login  
/dashboard     → Supplier Dashboard  
/buyer/dashboard  
/admin/dashboard  

6.2 Key Components
	•	Navbar.tsx: logo, nav links, register/login or wallet-connect, role badge
	•	SwapPanel.tsx: GLU swap stub
	•	Chart.tsx: line chart via Recharts
	•	ProductTable/ProductCard: listing UI
	•	QuoteModal.tsx: lock-in quote → deal creation
	•	DashboardTabs.tsx: supplier vs buyer views

⸻

7. Completed Features
	•	🌐 Public marketplace with filters
	•	🔐 Email/password + JWT auth + role guards
	•	🦊 SIWE handshake & wallet binding
	•	📝 Product CRUD (supplier)
	•	📋 Deal creation & lifecycle (buyer ⇄ supplier)
	•	📄 PDF generation (WeasyPrint)
	•	⚖️ Admin panel full CRUD
	•	🚀 On-chain escrow (Polygon Amoy)
	•	📊 Live charts stub
	•	📑 Sample & zoom workflows

⸻

8. Search & Results

/search?query=… displays table:

| Image | Title | Origin | Price/kg | Supplier | Change % | Rating | Details |

⸻

9. Quote & Deal Flow
	1.	On /products/[id], click Lock in GLU Quote
	2.	Enter quantity → POST /deals
	3.	Redirect to /buyer/dashboard → view status, download PDF

⸻

10. AI Agent & Contract Engine
	•	POST /contracts/generate → generate draft via OpenAI
	•	Review → GET /contracts/{id}/pdf → download PDF
	•	(Future) mint NFT on-chain

⸻

11. Roadmap & Next Steps
	•	Phase 2: full registration UI, enhanced filters, real swap integration, multi-image viewer
	•	Phase 3+: on-chain governance, AI agents, COMDEX chain, mobile app

⸻

12. Dev Commands

12.1 Git & Deploy Shortcuts

git add .  
git commit -m "…"  
git push  

12.2 Backend (FastAPI + Cloud Run)

Local Dev

cd backend  
python3 -m venv .venv  
source .venv/bin/activate  
pip install -r requirements.txt  
uvicorn main:app --reload  

Alembic Migrations

cd backend  
alembic -c alembic.ini revision --autogenerate -m "…"  
alembic -c alembic.ini upgrade head  

Cloud Run Deploy

# Build & push
docker build -t gcr.io/$PROJECT/comdex-api:latest backend/  
docker push gcr.io/$PROJECT/comdex-api:latest  

# Deploy
gcloud run deploy comdex-api \
  --image=gcr.io/$PROJECT/comdex-api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=$PROJECT:us-central1:comdex-db \
  --vpc-connector=comdex-connector \
  --vpc-egress=private-ranges-only \
  --env-vars-file=cloudrun-env.yaml \
  --timeout=300s \
  --port=8080

  12.3 Frontend (Next.js + Firebase Hosting)

  cd frontend  
npm ci  
npm run dev       # local  
npm run build     # static build  
npm run export    # → frontend/out/  
firebase deploy --only hosting

firebase.json

{
  "hosting": {
    "public": "frontend/out",
    "ignore": ["firebase.json","/.*","/node_modules/"],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "comdex-api",
          "region": "us-central1"
        }
      },
      { "source": "**","destination": "/index.html" }
    ]
  }
}

13. Recent Changes & Notes
	•	Switched SIWE parsing to SiweMessage.parse_message()
	•	Unified localStorage key to "token" only
	•	Removed duplicate wallet-connect buttons in Navbar
	•	Frontend now always injects Authorization: Bearer <token>
	•	Updated cloudrun-env.yaml & deploy pipeline to include all env vars

⸻

14. Handover Summary
	•	Marketplace: listing, filtering, product CRUD, deal flow
	•	Auth: email/password + SIWE + JWT + roles
	•	Deploy: backend on Cloud Run, frontend on Firebase, Postgres on Cloud SQL
	•	Blockchain & AI: escrow & contract drafting stubs live on testnet

