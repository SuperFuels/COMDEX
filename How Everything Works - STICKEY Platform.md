How Everything Works — STICKEY Platform
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

Completed Features

Search & Search Results

Quote & Deal Flow

AI Agent & Contract Engine

Roadmap & Next Steps

Dev Commands

1. Overview
COMDEX (front-end branded STICKEY, ticker $GLU) is a next-gen B2B commodity-trading platform combining:

AI: autonomous agents for supplier matching & contract drafting

Blockchain: on-chain escrow & NFT certificates

Crypto-native: wallet binding, swap panel, token flows

Mission: Revolutionize global commodity trade with trust, automation, transparency.
V1 Target: Whey Protein (EU, USA, India, NZ)
V2+: Cocoa, coffee, olive oil, pea protein, spices, and beyond

2. Architecture
less
Copy
Edit
[ Next.js Frontend (Firebase Hosting, static ∪ rewrites) ]
            ↕
[ FastAPI Backend (Cloud Run, Docker) ]
            ↕
        [ PostgreSQL (Cloud SQL) ]

     ↑                           ↑
[ MetaMask + $GLU ]       [ Migrations / Alembic ]

     ↑
[ Polygon Amoy Testnet Escrow Contract ]
      (Future: COMDEX Chain)
Frontend: Next.js + Tailwind CSS + TypeScript, statically exported → frontend/out → served by Firebase Hosting

Backend: FastAPI + SQLAlchemy + Pydantic + WeasyPrint (Docker → Cloud Run)

DB: PostgreSQL (Cloud SQL)

Blockchain: Polygon Amoy testnet escrow; future COMDEX Chain

AI: OpenAI LLM integrations under /agent and /contracts/generate

3. Authentication & Roles
3.1 Email/Password + JWT
/auth/register → store hashed password + role

/auth/login → issue JWT

Guards on backend (Depends(get_current_user) + role check) and frontend (React hook useAuthRedirect(role))

3.2 SIWE Login & Account Switching
Fetch nonce & SIWE message

ts
Copy
Edit
const { data: { message } } = await api.get('/auth/nonce', { params: { address } });
Sign in MetaMask

ts
Copy
Edit
const signature = await ethereum.request({ method: 'personal_sign', params: [message, address] });
Verify & receive JWT

ts
Copy
Edit
const { data: { token, role } } = await api.post('/auth/verify',{ message, signature });
localStorage.setItem('token', token);
api.defaults.headers.common.Authorization = `Bearer ${token}`;
Handle account changes in Navbar.tsx: re-run handshake on accountsChanged.

4. Database Schemas
4.1 Users
Column	Type	Notes
id	PK	
name	TEXT	
email	TEXT	nullable if wallet-only
password_hash	TEXT	nullable if wallet-only
role	ENUM	admin | supplier | buyer
wallet_address	TEXT	EIP-55, nullable
created_at	TIMESTAMP	
updated_at	TIMESTAMP	

4.2 Products
Column	Type	Notes
id	PK	
owner_email	FK	→ users.email
title	TEXT	
description	TEXT	
price_per_kg	NUMERIC	
origin_country	TEXT	
category	TEXT	
image_url	TEXT	
New Fields		
change_pct	NUMERIC	price change %
rating	NUMERIC	user rating
batch_number	TEXT	
trace_id	TEXT	
certificate_url	TEXT	NFT cert viewer
blockchain_tx_hash	TEXT	escrow Tx hash
created_at	TIMESTAMP	

4.3 Deals
Column	Type	Notes
id	PK	
buyer_id	FK	→ users.id
supplier_id	FK	→ users.id
product_id	FK	→ products.id
quantity_kg	NUMERIC	
total_price	NUMERIC	
status	ENUM	negotiation→confirmed→completed
created_at	TIMESTAMP	
pdf_url	TEXT	generated PDF

4.4 Contracts
Column	Type	Notes
id	PK	
prompt	TEXT	LLM prompt
generated_contract	TEXT	HTML/Markdown
status	TEXT	draft/final
pdf_url	TEXT	PDF export
nft_metadata	JSONB	stub

5. Backend Endpoints
<details> <summary>Auth</summary>
Method	Path	Description	Auth
POST	/auth/register	email/password + role → create user	—
POST	/auth/login	email/password → JWT	—
GET	/auth/nonce	SIWE nonce + EIP-4361 message	—
POST	/auth/verify	SIWE verify → JWT + role	—
GET	/auth/role	validate JWT → { role }	Bearer JWT

</details> <details> <summary>Products</summary>
Method	Path	Description	Auth
GET	/products	list all products	Public
GET	/products/search	search products	Public
GET	/products/{id}	product details	Public
GET	/products/me	supplier’s own products	Bearer supplier JWT
POST	/products	create product	Bearer supplier JWT
PUT	/products/{id}	update product	Bearer supplier JWT
DELETE	/products/{id}	delete product	Bearer supplier JWT

</details> <details> <summary>Deals</summary>
Method	Path	Description	Auth
GET	/deals	list deals for current user	Bearer JWT
POST	/deals	create deal (calculates total_price)	Bearer JWT
GET	/deals/{id}	single deal	Bearer JWT + ownership guard
GET	/deals/{id}/pdf	download deal PDF	Bearer JWT
PUT	/deals/{id}/status	update deal status	Bearer admin/parties
POST	/deals/{id}/release	release funds on-chain	Bearer buyer/supplier

</details> <details> <summary>Contracts</summary>
Method	Path	Description	Auth
POST	/contracts/generate	LLM draft contract	Bearer JWT
GET	/contracts/{id}	contract details	Bearer JWT
GET	/contracts/{id}/pdf	download contract PDF	Bearer JWT
POST	/contracts/{id}/mint	mint NFT (future)	Bearer JWT

</details> <details> <summary>Admin</summary>
All CRUD under /admin/* for users, products, deals, contracts

Auth: Bearer admin JWT

</details> <details> <summary>Users</summary>
Method	Path	Description	Auth
PATCH	/users/me/wallet	bind MetaMask wallet to user profile	Bearer JWT

</details>
6. Frontend Structure
6.1 Pages
bash
Copy
Edit
/                 → Home / Marketplace
/search           → Search results
/products/[id]    → Product detail
/products/[id]/sample → Sample request
/products/[id]/zoom   → Zoom request
/products/create      → Create product
/products/edit/[id]   → Edit product
/buyer/dashboard      → Buyer Dashboard
/dashboard            → Supplier Dashboard
/admin/dashboard      → Admin panel
/login                → Email/password login
/register/supplier    → Supplier signup
/register/buyer       → Buyer signup
6.2 Key Components
Navbar: logo, search bar, auth links, wallet-connect, SIWE & account-switch

SwapPanel: inline token swap UI (stub)

Chart: Recharts line chart

ProductCard: image, price, change %, rating, details link

QuoteModal: input quantity → create deal

Sidebar: filters & selected commodity

DashboardTabs: tabs for deals / contracts

7. Completed Features
🌐 Public marketplace with listings & filters

🖼️ Image upload & display

🔐 Email/password JWT auth & role-guards

🦊 MetaMask wallet connect & full SIWE handshake with account-switch

📝 Product CRUD (supplier)

📋 Deal creation & status workflow

📄 PDF generation (WeasyPrint)

⚖️ Admin panel full CRUD

🔄 Sticky SwapPanel (stub)

🚀 On-chain escrow integration (Polygon Amoy testnet)

📊 Live charts (stub)

📑 Sample & Zoom request UIs

8. Search & Search Results
/search shows table with:
Image | Title | Origin | Price/kg | Supplier | Change % | Rating | Details

9. Quote & Deal Flow
On /products/[id], click “Lock in GLU Quote” → opens QuoteModal

Buyer enters quantity → POST /deals → redirect to /buyer/dashboard

10. AI Agent & Contract Engine
AgentBar stub on /contracts

POST /contracts/generate → save draft → review & PDF download

11. Roadmap & Next Steps
Phase 2: Core Flows & Polish

Harden real-world SIWE (remove dev stub)

Add full registration UIs

Enhanced search filters (rating, tags, regions)

SwapPanel → real on-chain swaps & deals

Multi-image uploads & NFT certificate viewer

Phase 3+: On-chain & Integrations

AI agents

Governance

COMDEX Chain

Mobile & global expansion

12. Dev Commands
12.1 Backend (FastAPI + Docker + Cloud Run)
bash
Copy
Edit
# Local
cd backend
source .venv/bin/activate
uvicorn main:app --reload

# DB Migrations
alembic revision --autogenerate -m "…"
alembic upgrade head

# Docker build & push (for Cloud Run):
docker build -t gcr.io/$PROJECT/comdex-api:latest .
docker push gcr.io/$PROJECT/comdex-api:latest

# Deploy to Cloud Run
gcloud run deploy comdex-api \
  --image=gcr.io/$PROJECT/comdex-api:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --add-cloudsql-instances="$CLOUDSQL_INSTANCE" \
  --vpc-connector=comdex-connector \
  --vpc-egress=private-ranges-only \
  --env-vars-file=env.yaml

# Tail logs
gcloud beta run services logs tail comdex-api \
  --region=us-central1 --platform=managed
12.2 Frontend (Next.js + Firebase Hosting)
bash
Copy
Edit
cd frontend

# Local dev
npm install
npm run dev

# Static export
npm run build      # → runs `next build`
# no longer need `next export` here: `output: "export"` in next.config.js
npm run export     # → writes to `out/`

# Deploy to Firebase Hosting
firebase deploy --only hosting
firebase.json (public-only mode + Cloud Run rewrite):

jsonc
Copy
Edit
{
  "hosting": {
    "public": "frontend/out",
    "ignore": [ "firebase.json", "**/.*", "**/node_modules/**" ],
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
<br>
End of document.








