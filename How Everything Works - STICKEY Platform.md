# STICKEY / COMDEX Platform — Living Documentation

## Table of Contents

1. Overview  
2. Architecture  
3. Authentication & Roles  
   - 3.1 Email/Password + JWT  
   - 3.2 SIWE Login & Account Switching  
4. Database Schemas  
   - 4.1 Users  
   - 4.2 Products  
   - 4.3 Deals  
   - 4.4 Contracts  
5. Backend Endpoints  
6. Frontend Structure  
   - 6.1 Pages  
   - 6.2 Key Components  
7. Completed Features  
8. Search & Results  
9. Quote & Deal Flow  
10. AI Agent & Contract Engine  
11. Roadmap & Next Steps  
12. Dev Commands  
   - 12.1 Git & Deploy Shortcuts  
   - 12.2 Backend (FastAPI + Cloud Run)  
     - Local dev  
     - Migrations  
     - Cloud SQL & Proxy  
     - Cloud Run  
   - 12.3 Frontend (Next.js + Firebase Hosting)  
13. Recent Changes & Notes  
14. Handover Summary  

---

## 1. Overview

COMDEX (branded STICKEY, ticker `$GLU`) is a next-gen B2B commodity-trading platform combining:  
- **AI:** autonomous agents for supplier matching & contract drafting  
- **Blockchain:** on-chain escrow & NFT certificates  
- **Crypto-native:** wallet binding, swap panel, token flows  

**Mission:** Revolutionize global commodity trade with trust, automation, transparency.  
**V1 Target:** Whey Protein (EU, USA, India, NZ)  
**V2+:** Cocoa, coffee, olive oil, pea protein, spices, beyond.

---

## 2. Architecture

```text
[ Next.js Frontend (Firebase Hosting, static ∪ rewrites) ]
                          ↕
[ FastAPI Backend (Cloud Run, Docker) ]
                          ↕
[ PostgreSQL (Cloud SQL) ]
Frontend: Next.js + Tailwind CSS + TypeScript → static build to frontend/out → Firebase Hosting

Backend: FastAPI + SQLAlchemy + Pydantic + WeasyPrint; Dockerized → Cloud Run

DB: PostgreSQL (Cloud SQL)

Blockchain: Polygon Amoy testnet escrow → future COMDEX Chain

AI: OpenAI LLM integrations under /agent & /contracts/generate

3. Authentication & Roles
3.1 Email/Password + JWT
POST /auth/register → create user with bcrypt-hashed password & role

POST /auth/login → validate credentials → issue JWT

Guards on backend via Depends(get_current_user) + role checks

Frontend hook useAuthRedirect(role)

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
id	integer	PK
name	text	
email	text	unique; nullable if wallet-only
password_hash	text	nullable if wallet-only
role	enum	admin / supplier / buyer
wallet_address	text	EIP-55; nullable
created_at	timestamp	new: UTC default NOW()
updated_at	timestamp	

4.2 Products
Column	Type	Notes
id	integer	PK
owner_email	text	FK → users.email
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
created_at	timestamp	timestamp

4.3 Deals
Column	Type	Notes
id	integer	PK
buyer_id	integer	FK → users.id
supplier_id	integer	FK → users.id
product_id	integer	FK → products.id
quantity_kg	numeric	
total_price	numeric	
status	enum	negotiation → confirmed → completed
created_at	timestamp	
pdf_url	text	generated PDF

4.4 Contracts
Column	Type	Notes
id	integer	PK
prompt	text	LLM prompt
generated_contract	text	HTML/Markdown
status	text	draft / final
pdf_url	text	PDF export
nft_metadata	JSONB	stub
created_at	timestamp	

5. Backend Endpoints
Auth (/auth)

Products (/products)

Deals (/deals)

Contracts (/contracts)

Admin (/admin)

Users (/users)

See each router’s docstrings for full details.

6. Frontend Structure
6.1 Pages
text
Copy
Edit
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
Navbar: logo, marketplace link, register/login or wallet-connect, SIWE, account-switch, role-based dashboards

ProductCard: image, price change %, rating

QuoteModal: lock in quote → create deal

DashboardTabs: tabs for your deals, contracts

SwapPanel: inline GLU swap UI (stub)

Chart: line chart on dashboard via Recharts

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
/search?query=… displays a table:

| Image | Title | Origin | Price/kg | Supplier | Change % | Rating | Details |

9. Quote & Deal Flow
On /products/[id], click Lock in GLU Quote
Enter quantity in QuoteModal → POST /deals
Redirect to buyer/dashboard → view status & PDF

10. AI Agent & Contract Engine
POST /contracts/generate → draft contract via OpenAI

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
git add .
git commit -m "…"
git push
12.2 Backend (FastAPI + Cloud Run)
Local dev
Option A: venv

bash
Copy
Edit
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
Option B: nix-shell

Create shell.nix in project root:

nix
Copy
Edit
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.python310
    pkgs.python310Packages.sqlalchemy
    pkgs.python310Packages.alembic
    pkgs.python310Packages.python-dotenv
    pkgs.python310Packages.psycopg2
    pkgs.docker
    pkgs.docker-compose
  ];
  shellHook = ''
    export DOCKER_HOST=unix:///var/run/docker.sock
  '';
}
Launch:

bash
Copy
Edit
nix-shell
cd backend
uvicorn main:app --reload
Migrations
bash
Copy
Edit
cd backend

# view current head in the DB
alembic -c alembic.ini current

# if you have manually synced some migrations, stamp to last applied:
alembic -c alembic.ini stamp <revision_id>

# generate a new migration:
alembic -c alembic.ini revision --autogenerate -m "Add created_at to users"

# ⚠️ For non-nullable new columns:
#    1. Make column server_default=sa.func.now(), nullable=True
#    2. Upgrade & backfill
#    3. Alter column to nullable=False without default
# Example in versions/..._add_created_at_to_users.py:
#   op.add_column(
#     'users',
#     sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
#   )

# apply migrations
alembic -c alembic.ini upgrade head
Cloud SQL & Proxy
Create instance:

bash
Copy
Edit
gcloud sql instances create comdex-db \
  --database-version=POSTGRES_15 \
  --region=us-central1

gcloud sql users set-password comdex \
  --instance=comdex-db \
  --password=Wn8smx123
Run Cloud SQL Auth proxy v2:

bash
Copy
Edit
curl -Lo cloud-sql-proxy https://github.com/GoogleCloudPlatform/cloud-sql-proxy/releases/latest/download/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

./cloud-sql-proxy \
  --instances=PROJECT_ID:us-central1:comdex-db=tcp:5432 \
  --credentials-file=/path/to/key.json
Configure alembic.ini & backend/config.py:

ini
Copy
Edit
sqlalchemy.url = postgresql://comdex:Wn8smx123@localhost:5432/comdex
Migrate & run as above.

Cloud Run
bash
Copy
Edit
# build & push
docker build -t gcr.io/$PROJECT/comdex:latest backend/
docker push gcr.io/$PROJECT/comdex:latest

# deploy
gcloud run deploy comdex-api \
  --image=gcr.io/$PROJECT/comdex:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances=$PROJECT:us-central1:comdex-db \
  --vpc-connector=comdex-connector \
  --vpc-egress=private-ranges-only \
  --env-vars-file=env.yaml \
  --timeout=300s
12.3 Frontend (Next.js + Firebase Hosting)
bash
Copy
Edit
cd frontend
npm ci
npm run dev

# build & export
npm run build
npm run export  # output to frontend/out/

# deploy
firebase deploy --only hosting
firebase.json – rewrite API calls to Cloud Run:

jsonc
Copy
Edit
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
      { "source": "**", "destination": "/index.html" }
    ]
  }
}
13. Recent Changes & Notes
Nix shell added for reproducible local environment

Cloud SQL Proxy v2 instructions added

Alembic stamping & non-nullable column best practices documented

Added created_at to Users schema + migration patch

Ensured python-dotenv & psycopg2 in shell so Alembic/env.py loads

14. Handover Summary
What we’ve done

Core marketplace: listing, search, product CRUD, deal flow

SIWE/EIP-4361 + email/password fallback

Deployed backend on Cloud Run, frontend on Firebase

Integrated Cloud SQL + Auth proxy + VPC connector

Scaffolded AI contract agent & on-chain escrow stubs

Current state

Marketplace: fully functional, public listings

Auth: robust SIWE + JWT + role guards

Dashboards: supplier/buyer/admin in place

Contracts: draft generation & PDF download

On-chain escrow: testnet integration complete

Logging & monitoring: Cloud Run logs tail via gcloud beta run services logs tail comdex-api












