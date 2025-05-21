STICKEY / COMDEX Platform — Living Documentation
Table of Contents
Overview

Architecture

Authentication & Roles

Email/Password + JWT

SIWE Login & Account Switching

Database Schemas

Users

Products

Deals

Contracts

Backend Endpoints

Frontend Structure

Pages

Key Components

Completed Features

Search & Results

Quote & Deal Flow

AI Agent & Contract Engine

Roadmap & Next Steps

Dev Commands

Git & Deploy Shortcuts

Backend (FastAPI + Cloud Run)

Frontend (Next.js + Firebase Hosting)

Recent Changes & Notes

Handover Summary

1. Overview
COMDEX (branded STICKEY, ticker $GLU) is a next-gen B2B commodity-trading platform combining:

AI: autonomous agents for supplier matching & contract drafting

Blockchain: on-chain escrow & NFT certificates

Crypto-native: wallet binding, swap panel, token flows

Mission: Revolutionize global commodity trade with trust, automation, transparency.
V1 Target: Whey Protein (EU, USA, India, NZ)
V2+: Cocoa, coffee, olive oil, pea protein, spices, beyond.

2. Architecture
css
Copy
Edit
[ Next.js Frontend (Firebase Hosting, static ∪ rewrites) ]
                    ↕
   [ FastAPI Backend (Cloud Run, Docker) ]
                    ↕
         [ PostgreSQL (Cloud SQL) ]
Frontend: Next.js + Tailwind CSS + TypeScript, output: "export" → static build to frontend/out → Firebase Hosting

Backend: FastAPI + SQLAlchemy + Pydantic + WeasyPrint; Dockerized → Cloud Run

DB: PostgreSQL (Cloud SQL)

Blockchain: Polygon Amoy testnet escrow → future COMDEX Chain

AI: OpenAI LLM integrations under /agent & /contracts/generate

3. Authentication & Roles
3.1 Email/Password + JWT
POST /auth/register → create user with bcrypt-hashed password & role

POST /auth/login → validate credentials → issue JWT

Guards on backend via Depends(get_current_user) + role checks; frontend hook useAuthRedirect(role)

3.2 SIWE Login & Account Switching
GET /auth/nonce?address=… → returns SIWE message

personal_sign in MetaMask

POST /auth/verify { message, signature } → validate → JWT + role

Frontend stores localStorage.token, sets Authorization header

Navbar.tsx:

tracks manuallyDisconnected to prevent unwanted auto-login

listens on accountsChanged, but no longer auto-calls doLogin on switch

forces user to click “Connect Wallet” after manual switch

4. Database Schemas
4.1 Users
Column	Type	Notes
id	integer (PK)	
name	text	
email	text (unique)	nullable if wallet-only
password_hash	text	nullable if wallet-only
role	enum	admin / supplier / buyer
wallet_address	text	EIP-55, nullable
created_at	timestamp	
updated_at	timestamp	

4.2 Products
Column	Type	Notes
id	integer (PK)	
owner_email	text (FK→users.email)	
title	text	
description	text	
price_per_kg	numeric	
origin_country	text	
category	text	
image_url	text	
change_pct	numeric	price change %
rating	numeric	user rating
batch_number	text	optional
trace_id	text	optional
certificate_url	text	NFT cert viewer
blockchain_tx_hash	text	escrow Tx hash
created_at	timestamp	

4.3 Deals
Column	Type	Notes
id	integer (PK)	
buyer_id	integer (FK→users.id)	
supplier_id	integer (FK→users.id)	
product_id	integer (FK→products.id)	
quantity_kg	numeric	
total_price	numeric	
status	enum	negotiation→confirmed→completed
created_at	timestamp	
pdf_url	text	generated PDF

4.4 Contracts
Column	Type	Notes
id	integer	PK
prompt	text	LLM prompt
generated_contract	text	HTML/Markdown
status	text	draft/final
pdf_url	text	PDF export
nft_metadata	JSONB	stub
created_at	timestamp	

5. Backend Endpoints
<details><summary>Auth</summary>
Method	Path	Description	Auth
POST	/auth/register	email/password + role → create user	—
POST	/auth/login	email/password → JWT	—
GET	/auth/nonce	SIWE nonce + EIP-4361 message	—
POST	/auth/verify	SIWE verify → JWT + role	—
GET	/auth/role	validate JWT → { role }	Bearer JWT

</details> <details><summary>Products</summary>
Method	Path	Description	Auth
GET	/products	list all products	Public
GET	/products/search	search by title or category	Public
GET	/products/{id}	product details	Public
GET	/products/me	my products	Bearer supplier JWT
POST	/products	create product	Bearer supplier JWT
PUT	/products/{id}	update product	Bearer supplier JWT
DELETE	/products/{id}	delete product	Bearer supplier JWT

</details> <details><summary>Deals</summary>
Method	Path	Description	Auth
GET	/deals	list deals for current user	Bearer JWT
POST	/deals	create deal (calculates total_price)	Bearer JWT
GET	/deals/{id}	single deal	Bearer JWT + ownership
GET	/deals/{id}/pdf	download deal PDF	Bearer JWT
PUT	/deals/{id}/status	update deal status	Bearer admin/parties
POST	/deals/{id}/release	release funds on-chain	Bearer buyer/supplier

</details> <details><summary>Contracts</summary>
Method	Path	Description	Auth
POST	/contracts/generate	LLM draft contract	Bearer JWT
GET	/contracts/{id}	contract details	Bearer JWT
GET	/contracts/{id}/pdf	download contract PDF	Bearer JWT
POST	/contracts/{id}/mint	mint NFT (future)	Bearer JWT

</details> <details><summary>Admin</summary>
All CRUD under /admin/* for users, products, deals, contracts.
Auth: Bearer admin JWT.

</details> <details><summary>Users</summary>
Method	Path	Description	Auth
PATCH	/users/me/wallet	bind MetaMask wallet to user profile	Bearer JWT

</details>
6. Frontend Structure
6.1 Pages
bash
Copy
Edit
/                 → Marketplace (Home)
/search           → Search results
/products/[id]    → Product detail
/products/[id]/sample → Sample request
/products/[id]/zoom   → Zoom request
/products/create      → Create product
/products/edit/[id]   → Edit product
/register             → Role selection & signup
/login                → Email/password login
/dashboard            → Supplier Dashboard
/buyer/dashboard      → Buyer Dashboard
/admin/dashboard      → Admin panel
6.2 Key Components
Navbar: logo, marketplace link, register/login or wallet-connect, SIWE, account-switch, role-based dashboards

ProductCard: image, price change %, rating

QuoteModal: lock in quote → create deal

DashboardTabs: tabs for your deals, contracts

SwapPanel (stub): inline GLU swap UI

Chart: Recharts line chart on dashboard

7. Completed Features
🌐 Public marketplace with filters

🖼️ Image upload & display

🔐 Email/password JWT auth & role guards

🦊 MetaMask + SIWE handshake & account switching

📝 Product CRUD (supplier)

📋 Deal creation & lifecycle (buyer↔supplier)

📄 PDF generation (WeasyPrint)

⚖️ Admin panel full CRUD

🚀 On-chain escrow integration (Polygon Amoy testnet)

📊 Live charts (stub)

📑 Sample & zoom request flows

8. Search & Results
/search?query=… displays:

| Image | Title | Origin | Price/kg | Supplier | Change % | Rating | Details |

9. Quote & Deal Flow
On /products/[id], click Lock in GLU Quote

Enter quantity in QuoteModal → POST /deals

Redirect to buyer/dashboard → view status & PDF

10. AI Agent & Contract Engine
/contracts/generate → draft contract via OpenAI

Review, then download PDF via /contracts/{id}/pdf

(Future) mint NFT on chain

11. Roadmap & Next Steps
Phase 2: polish SIWE, full registration UI, enhanced filters, real swap integration, multi-image & certificate viewer

Phase 3+: on-chain governance, AI agents, COMDEX Chain, mobile expansion

12. Dev Commands
12.1 Git & Deploy Shortcuts
bash
Copy
Edit
# commit your debug-logs & fixes
git add .
git commit -m "debug: log SIWE verify request & response"
git push

# backend rebuild & redeploy
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

# frontend rebuild & redeploy
cd frontend
npm ci
npm run build
firebase deploy --only hosting
12.2 Backend (FastAPI + Cloud Run)
bash
Copy
Edit
# Local dev
cd backend
source .venv/bin/activate
uvicorn main:app --reload

# Migrations
alembic revision --autogenerate -m "…"
alembic upgrade head

# Cloud Run
docker build -t gcr.io/$PROJECT/comdex:latest .
docker push gcr.io/$PROJECT/comdex:latest
gcloud run deploy comdex-api \
  --image=gcr.io/$PROJECT/comdex:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances="$CLOUDSQL_INSTANCE" \
  --vpc-connector=comdex-connector \
  --vpc-egress=private-ranges-only \
  --env-vars-file=env.yaml
Tail logs (alternate if log-streaming component not available):

bash
Copy
Edit
gcloud beta run services logs tail comdex-api \
  --project=swift-area-459514-d1 \
  --region=us-central1
12.3 Frontend (Next.js + Firebase Hosting)
bash
Copy
Edit
cd frontend
npm install
npm run dev

# Build & export
npm run build      # output: static
npm run export     # writes to out/

# Deploy
firebase deploy --only hosting
firebase.json rewrite snippet:

jsonc
Copy
Edit
{
  "hosting": {
    "public": "frontend/out",
    "ignore": ["firebase.json","**/.*","**/node_modules/**"],
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
Navbar.tsx overhauled to prevent automatic SIWE on accountsChanged

Introduced manuallyDisconnected flag to persist user intent

Removed extra <a> tags from Next.js <Link> (now using the new API)

Database added change_pct, rating, certificate fields

Frontend build now uses output: "export" → static out/ directory

next export no longer necessary for static-only hosting

GitHub → Firebase CI/CD via firebase.json rewrites

14. Handover Summary
What we've been doing

Built out core marketplace: listing, search, product CRUD, deal flow

Implemented full SIWE/EIP-4361 handshake, plus email/password fallback

Deployed backend on Cloud Run, frontend on Firebase

Integrated Cloud SQL + Cloud Run VPC connector

Scaffolded AI contract agent & on-chain escrow stubs

Where we are right now

Marketplace: fully functional, public listings

Authentication: robust SIWE + JWT + role guards

Dashboards: supplier/buyer/admin pages in place (links appear based on role)

Contracts: draft generation & PDF download working

On-chain escrow: testnet integration complete for basic release

Logging & monitoring: Cloud Run logs tail accessible via gcloud beta run services logs tail

Next AI Chat Should Know

How we handle wallet connect/disconnect flags

The static-export setup via output: "export"

The new <Link> usage in Next 15

Where to find deploy shortcuts in this doc

How to repro SIWE verify flow in Network panel

That manuallyDisconnected will prevent auto-login

Feel free to refer back to any section in this live doc as the project evolves! 🚀









