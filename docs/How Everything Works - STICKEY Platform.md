# STICKEY / COMDEX Platform — Living Documentation  
**Last updated: June 2025**

---

## Overview  
COMDEX (branded STICKEY, ticker $GLU) is a next-gen B2B commodity-trading platform combining:  
- **AI**: autonomous agents for supplier matching & contract drafting  
- **Blockchain**: on-chain escrow & NFT certificates  
- **Crypto-native**: wallet binding, built-in swap functionality, token flows  

**Mission**: Revolutionize global commodity trade with trust, automation, and transparency.  
**V1 Target**: Whey Protein (EU, USA, India, NZ)

---

## Architecture  

[ Next.js Frontend (Firebase Hosting) ] ↕ [ FastAPI Backend (Cloud Run) ] ↕ [ PostgreSQL (Cloud SQL) ]

- **Frontend**:  
  - Next.js + Tailwind + TypeScript  
  - `next build` → `next export` → `frontend/out` → deployed to Firebase Hosting  
  - Rewrites: any `/api/**` request is forwarded to Cloud Run (FastAPI)
- **Backend**:  
  - FastAPI + SQLAlchemy + Pydantic → Docker → Cloud Run  
  - Connects to Cloud SQL (Postgres)
- **Blockchain**:  
  - Polygon Amoy testnet for escrow  
  - COMDEX chain planned in later phases
- **AI**:  
  - OpenAI LLM integrations under `/agent` & `/contracts/generate`

---

## Authentication & Roles  
### 3.1 Email/Password + JWT  
1. **POST** `/auth/register` → create new user (bcrypt-hash password), assign role (`supplier`/`buyer`/`admin`).  
2. **POST** `/auth/login` → validate credentials → issue JWT.  
3. Protected API routes use `Depends(get_current_user)` + role checks.  
4. Frontend hook `useAuthRedirect(requiredRole?)` enforces login & redirects based on role.

### 3.2 SIWE Login & Wallet Binding  
1. **GET** `/auth/nonce?address=…` → returns a full EIP-4361 message.  
2. User signs that message via `personal_sign` (MetaMask).  
3. **POST** `/auth/verify` → `{ message, signature }`.  
4. Backend uses `SiweMessage.parse_message()` → verifies → upserts User → returns `{ token, role }`.  
5. Frontend stores `localStorage.setItem('token', token)` and sets Axios default header:  
   ```ts
   api.defaults.headers.common.Authorization = `Bearer ${token}`

   	6.	Manual disconnects (user-clicked “Disconnect Wallet”) set localStorage.manualDisconnect = 'true'.
	•	On page load, if manualDisconnect is present → SIWE auto-login is suppressed until “Connect Wallet” is clicked again.

⸻

Database Schemas

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
enum: admin / supplier / buyer
wallet_address
varchar
EIP-55; nullable if email/password only
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
owner_id
integer
FK → users.id (owner/supplier)
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
S3/Cloud Storage link
change_pct
numeric
price change % (computed)
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
NFT cert viewer link
blockchain_tx_hash
text
escrow TX hash
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
FK → users.id (who initiated the deal)
supplier_id
integer
FK → users.id (supplier on the other side)
product_id
integer
FK → products.id
quantity_kg
numeric
total_price
numeric
status
varchar
enum: negotiation → confirmed → completed
created_at
timestamp
pdf_url
text
generated PDF for contract/receipt


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
HTML/Markdown draft
status
varchar
enum: draft / final
pdf_url
text
PDF export link
nft_metadata
JSONB
stub for NFT metadata
created_at
timestamp


Backend Endpoints
	•	Auth (/auth):
	•	POST /auth/register
	•	POST /auth/login
	•	GET  /auth/nonce?address=…
	•	POST /auth/verify
	•	GET  /auth/profile
	•	GET  /auth/role
	•	Products (/products):
	•	GET    /products
	•	GET    /products/{id}
	•	POST   /products (multipart/form-data)
	•	PUT    /products/{id}
	•	DELETE /products/{id}
	•	Deals (/deals):
	•	POST   /deals
	•	GET    /deals/{id}
	•	PATCH  /deals/{id} (update status)
	•	Contracts (/contracts):
	•	POST   /contracts/generate
	•	GET    /contracts/{id}/pdf
	•	Admin (/admin):
	•	Full CRUD on users, products, deals, etc.
	•	Users (/users):
	•	Wallet binding, profile lookup, list users, etc.

See each router’s docstrings for full path, payload, and response details.

⸻

Frontend Structure

6.1 Pages

/
/search
/products/[id]
/products/sample/[id]
/products/zoom/[id]
/dashboard        → redirects based on role:
/dashboard → SupplierDashboard
/buyer/dashboard
/admin/dashboard
/register
/login

	•	Note:
	•	Supplier dashboard now lives at /supplier/dashboard (automatically enforced by useAuthRedirect('supplier')).
	•	Create/Edit Product functionality is embedded in the “Manage Inventory” tabs inside the Supplier Dashboard.

6.2 Key Components
	•	Navbar.tsx
	•	Logo (Stickey.ai), “G” toggle (opens Sidebar), search input, inline swap controls, “Live” button (links to marketplace), wallet/connect button.
	•	Sidebar.tsx
	•	Drawer-style slide-in menu with role-based navigation (e.g. Dashboard, Profile, Settings, Logout).
	•	Chart.tsx
	•	Line chart component (using Recharts) for time-series data.
	•	CreateProductForm.tsx
	•	Standalone “Create Product” form (imported into Supplier Dashboard).
	•	ProductTable.tsx / ProductCard.tsx
	•	Listing UI for products on marketplace.
	•	QuoteModal.tsx
	•	Modal for “Lock in GLU Quote” (buyer flow).
	•	SupplierDashboard.tsx
	•	Top metrics (“Global Snapshot”), live chart + AI analysis, and “Manage Inventory” tabs (Create/Edit/Active/Messages/Compliance/Reports/Shipments).
	•	BuyerDashboard.tsx
	•	Buyer’s home screen showing open deals, status, etc.
	•	AdminDashboard.tsx
	•	Admin panel with full CRUD.

⸻

Completed Features
	•	🌐 Public marketplace with filtering & search
	•	🔐 Email/password + JWT authentication + role guards
	•	🦊 SIWE handshake & wallet binding (auto-reconnect logic)
	•	📝 Product CRUD (supplier)
	•	📋 Deal creation & lifecycle (buyer ⇄ supplier)
	•	📄 PDF generation (WeasyPrint)
	•	⚖️ Admin panel full CRUD
	•	🚀 On-chain escrow (Polygon Amoy testnet)
	•	📊 Live charts stub (24-point time series)
	•	📑 Sample & zoom workflows for product images

⸻

Search & Results

/search?query=… displays a responsive table:

Image
Title
Origin
Price/kg
Supplier
Change %
Rating
Details
···
Organic Whey Protein
USA
£12.50
Alice
↑ 3.25%
4.8/5
[View]


Quote & Deal Flow
	1.	On /products/[id], click “Lock in GLU Quote”.
	2.	Enter desired quantity → POST /deals → create new deal record.
	3.	Buyer is redirected to /buyer/dashboard → view deal status, download contract PDF, track shipments.

⸻

AI Agent & Contract Engine
	•	Draft Generation:
	•	POST /contracts/generate → OpenAI LLM returns a draft contract.
	•	Review & PDF:
	•	GET /contracts/{id}/pdf → serve PDF (WeasyPrint‐rendered).
	•	(Future):
	•	Mint NFT certificate on-chain, attach nft_metadata to contract record.

⸻

Roadmap & Next Steps
	1.	Phase 2
	•	Full registration UI (role selection, profile onboarding)
	•	Enhanced filters on marketplace (by country, category, price range)
	•	Real GLU swap integration (onchain DEX)
	•	Multi-image viewer for products
	2.	Phase 3+
	•	On-chain governance (DAO)
	•	AI-driven autonomous trading agents
	•	Launch COMDEX proprietary blockchain
	•	Mobile app (React Native or Expo)

⸻

Dev Commands

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

Containerize & Deploy to Cloud Run

# Build & push
docker build -t gcr.io/$PROJECT/comdex-api:latest backend/
docker push gcr.io/$PROJECT/comdex-api:latest

# Deploy to Cloud Run
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
npm run dev           # Local development
npm run build         # Static build
npm run export        # → frontend/out/
firebase deploy --only hosting

firebase.json
{
  "hosting": {
    "public": "frontend/out",
    "ignore": ["firebase.json", "/.*", "/node_modules/"],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "comdex-api",
          "region": "us-central1"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}

Recent Changes & Notes
	•	Swap Panel:
	•	Renamed from SwapBar.tsx → now inline in Navbar.tsx (desktop) and removed mobile-only swap bar.
	•	Navbar Adjustments:
	•	“G” toggle (opens Sidebar) is fixed to top-left (top-4 left-4) with proper centering in header.
	•	Logo link uses a .logo-link class to remove default CSS border.
	•	“Live” button is now a clickable <button> that routes to /products (marketplace).
	•	Wallet/Connect button is always pushed to far right of header.
	•	Currency inputs (USDT, $GLU) have been widened (w-20 sm:w-28) to avoid text overflow.
	•	Supplier Dashboard:
	•	Added a 16-unit tall spacer (<div className="h-16" />) at top of page to account for sticky Navbar.
	•	“Metrics” header changed to “Global Snapshot.”
	•	Chart + AI analysis areas updated: white background, black text (no green-on-black terminal styling).
	•	“Manage Inventory” is now a single container with tabs:
	•	Create Product (in-line form via CreateProductForm.tsx)
	•	Edit Product (placeholder)
	•	Active Products (placeholder)
	•	Messages (placeholder)
	•	Compliance (placeholder)
	•	Reports (placeholder)
	•	Shipments (placeholder)
	•	Form Styling:
	•	All form fields (input, textarea) use white background (bg-white) with black border (border-gray-300), no grey fill.
	•	Font family uses Inter (same as ChatGPT styling), and text is dark (text-gray-800) for labels and inputs.
	•	Create Product:
	•	Pulled out into frontend/components/CreateProductForm.tsx for reuse in the “Manage Inventory” tab.
	•	Uses standard Tailwind styling (white background, black border on inputs).
	•	Remove Deprecated Code:
	•	The old lower swap bar is fully removed from _app.tsx.
	•	SwapBar.tsx import is gone; all swap logic is now handled inside Navbar.tsx for desktop and removed for mobile.

⸻

Handover Summary
	•	Marketplace: listing, filtering, product CRUD (supplier), deal flow (buyer ⇄ supplier)
	•	Auth: email/password + SIWE + JWT + role guards (useAuthRedirect)
	•	Deploy: backend on Cloud Run, frontend on Firebase Hosting, Postgres on Cloud SQL
	•	Blockchain & AI: escrow & contract drafting stubs live on Polygon Amoy testnet
	•	UI/UX:
	•	Clean, ChatGPT-style forms (white fields, dark gray text)
	•	Sticky Navbar with proper spacing & consistent padding
	•	Supplier Dashboard with “Global Snapshot,” charts, AI insights, and Manage Inventory tabs

	End of Living Documentation

	