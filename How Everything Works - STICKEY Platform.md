STICKEY / COMDEX Platform — Living Documentation

Table of Contents
	1.	Overview
	2.	Architecture
	3.	Authentication & Roles
	1.	Email/Password + JWT
	2.	SIWE Login & Account Switching
	4.	Database Schemas
	1.	Users
	2.	Products
	3.	Deals
	4.	Contracts
	5.	Backend Endpoints
	6.	Frontend Structure
	1.	Pages
	2.	Key Components
	7.	Completed Features
	8.	Search & Results
	9.	Quote & Deal Flow
	10.	AI Agent & Contract Engine
	11.	Roadmap & Next Steps
	12.	Dev Commands
	13.	Git & Deploy Shortcuts
	14.	Backend (FastAPI + Cloud Run)
	15.	Frontend (Next.js + Firebase Hosting)
	16.	Recent Changes & Notes
	17.	Handover Summary

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
[ FastAPI Backend (Cloud Run)     ]
               ↕
[ PostgreSQL (Cloud SQL)         ]
	•	Frontend: Next.js + Tailwind + TypeScript → next build → next export → frontend/out → Firebase Hosting with rewrites to Cloud Run for /api/**.
	•	Backend: FastAPI + SQLAlchemy + Pydantic → Docker → Cloud Run → connects to Cloud SQL (Postgres).
	•	Blockchain: Polygon Amoy testnet for escrow; COMDEX chain planned.
	•	AI: OpenAI LLM integrations under /agent & /contracts/generate.

⸻

3. Authentication & Roles

3.1 Email/Password + JWT
	•	POST /auth/register → create user (bcrypt-hash), assign role.
	•	POST /auth/login → validate credentials → issue JWT.
	•	Protected routes use Depends(get_current_user) + role checks in FastAPI.
	•	Frontend: useAuthRedirect(requiredRole?) enforces login & role, redirecting to /login or appropriate dashboard.

3.2 SIWE Login & Account Switching
	1.	Frontend calls GET /auth/nonce?address=… → receives full EIP-4361 SIWE message text.
	2.	User signs with personal_sign (MetaMask).
	3.	Frontend posts { message, signature } to POST /auth/verify.
	4.	Backend now uses SiweMessage.parse_message(message) (rather than constructor) → verifies signature + nonce → looks up/creates User → returns { token, role }.
	5.	Frontend stores localStorage.setItem('token', token) (never use “jwt” key), sets axios default.
	6.	In Navbar, clicking “Connect Wallet” triggers SIWE; manual‐disconnect is tracked in localStorage.manualDisconnect to prevent unwanted auto‐login.

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
text
email
text
unique; nullable if wallet-only
password_hash
text
nullable if wallet-only
role
enum
admin / supplier / buyer
wallet_address
text
EIP-55; nullable
created_at
timestamp
UTC default NOW()
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
text
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
enum
negotiation → confirmed → completed
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
text
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

Refer to each router’s docstrings for full path, payload, response.

⸻

6. Frontend Structure

6.1 Pages
/                   → Marketplace (Home)
/search             → Search results
/products/[id]      → Product detail
/products/[id]/sample → Sample request
/products/[id]/zoom   → Zoom request
/products/create    → Create product
/products/edit/[id] → Edit product
/register           → Role selection & signup
/login              → Email/password login
/dashboard          → Supplier Dashboard
/buyer/dashboard    → Buyer Dashboard
/admin/dashboard    → Admin panel

6.2 Key Components
	•	Navbar.tsx: logo, marketplace, register/login or wallet-connect button, role badge, dashboard links, account dropdown
	•	SwapPanel.tsx: sticky GLU swap stub
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
	•	📋 Deal creation & lifecycle (buyer↔supplier)
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
	1.	On /products/[id], click Lock in GLU Quote.
	2.	Enter quantity → POST /deals.
	3.	Redirect to /buyer/dashboard → view status, download PDF.

⸻

10. AI Agent & Contract Engine
	•	POST /contracts/generate → generate draft via OpenAI.
	•	Review → GET /contracts/{id}/pdf → download PDF.
	•	(Future) mint NFT on-chain.

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

Local Dev (venv):
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

Alembic Migrations:
cd backend
alembic -c alembic.ini revision --autogenerate -m "…"
alembic -c alembic.ini upgrade head

Cloud Run:
docker build -t gcr.io/$PROJECT/comdex:latest backend/
docker push gcr.io/$PROJECT/comdex:latest
gcloud run deploy comdex-api \
  --image=gcr.io/$PROJECT/comdex:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=$PROJECT:us-central1:comdex-db \
  --vpc-connector=comdex-connector \
  --env-vars-file=env.yaml \
  --timeout=300s

  12.3 Frontend (Next.js + Firebase Hosting)
  cd frontend
npm ci
npm run dev            # local
npm run build          # Next.js static build
npm run export         # exports to frontend/out/
firebase deploy --only hosting

Your firebase.json now rewrites:
{
  "hosting": {
    "public": "frontend/out",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "comdex-api",
          "region": "us-central1"
        }
      },
      { "source": "**", "destination": "/index.html" }
    ]
  }
}

13. Recent Changes & Notes
	•	Switched SIWE parsing to SiweMessage.parse_message() to avoid BaseModel.__init__ errors.
	•	Unified localStorage key to "token" only—no more "jwt".
	•	Fixed Navbar duplicate wallet‐connect by removing page‐level buttons.
	•	Updated frontend/lib/api.ts to always inject Authorization: Bearer <token>.
	•	Ensured Firebase Hosting predeploy & rewrites point at static output + Cloud Run.

⸻

14. Handover Summary
	•	Core marketplace: listing, filtering, product CRUD, deal flow.
	•	Auth: robust email/password + SIWE + JWT + role guards.
	•	Deploy: backend on Cloud Run, frontend on Firebase, Postgres on Cloud SQL.
	•	Blockchain & AI stubs in place; PDF generation & on-chain escrow working on testnet.

— end of living documentation.






