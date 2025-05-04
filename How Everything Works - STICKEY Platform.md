STICKEY Unified Handover & Reference
Table of Contents
Overview

Architecture

Authentication & Roles

Database Schemas
4.1 Users
4.2 Products
4.3 Deals
4.4 Contracts

Backend Endpoints
5.1 Auth (/auth)
5.2 Products (/products)
5.3 Deals (/deals)
5.4 Contracts (/contracts)
5.5 Admin (/admin)
5.6 Users (/users)

Frontend Structure
6.1 Pages
6.2 Components

Completed Features

Search & Search Results

Quote & Deal Flow

AI Agent & Contract Engine

Roadmap & Next Steps

Dev Commands

Overview
COMDEX (front‑end branded STICKEY, ticker $GLU) is a next‑gen B2B commodity‑trading platform combining:

AI: autonomous agents for supplier matching & contract drafting

Blockchain: on‑chain escrow & NFT certificates

Crypto‑native: wallet binding, swap panel, token flows

Mission: Revolutionize global commodity trade with trust, automation, transparency.
V1 Target: Whey Protein (EU, USA, India, NZ)
V2+: Cocoa, coffee, olive oil, pea protein, spices, and beyond.

Architecture
text
Copy
Edit
[Next.js Frontend] ←→ [FastAPI Backend] ←→ [PostgreSQL]
       │                                │
 [MetaMask + $GLU Wallet]        [Alembic Migrations]
       │                                │
 [Polygon Amoy Testnet Escrow Contract]
       │
    (Future: COMDEX Chain)
Frontend: Next.js + Tailwind CSS + TypeScript

Backend: FastAPI + SQLAlchemy + Pydantic + WeasyPrint (PDF)

DB: PostgreSQL

Blockchain: Polygon Amoy (escrow contract), future COMDEX Chain

AI: OpenAI LLM integrations under /agent and /contracts/generate

Authentication & Roles
JWT auth via /auth/register and /auth/login (tokens in localStorage)

Roles: admin / supplier / buyer

MetaMask wallet connect + backend binding (PATCH /users/me/wallet)

Route guards on both front-end & back-end

Demo credentials:

Role	Email	Password
admin	admin@example.com	admin123
supplier	supplier@example.com	supplypass
buyer	buyer@example.com	buyerpass

Database Schemas
Users
id, name, email, password_hash

role: admin/supplier/buyer

wallet_address

created_at, updated_at

Products
id

owner_email (FK → users.email)

title, description, price_per_kg

origin_country, category, image_url

New fields (added via Alembic revision fa7a1f804df6):

change_pct (FLOAT NOT NULL)

rating (FLOAT NOT NULL)

batch_number, trace_id, certificate_url, blockchain_tx_hash

created_at

Deals
id

buyer_id (FK → users.id), supplier_id (FK → users.id)

product_id (FK → products.id)

quantity_kg, total_price

status: negotiation → confirmed → completed

created_at, pdf_url

Contracts
id

prompt (TEXT)

generated_contract (HTML/Markdown)

status

pdf_url, nft_metadata (stub for future NFT)

Backend Endpoints
5.1 Auth (/auth)
POST /register (name, email, password) → user + JWT

POST /login (email, password) → { access_token, token_type }

GET /role (Bearer) → { role }

5.2 Products (/products)
Public
GET /products/ → all products (now includes change_pct, rating)

GET /products/search?query=… → filter by title/category

GET /products/{id} → single product

Authenticated (supplier)
GET /products/me → supplier’s products

POST /products/ (JSON) → create (Pydantic schema updated with change_pct & rating)

POST /products/create (multipart) → file upload → saved to /uploaded_images/

PUT /products/{id} → update own product

DELETE /products/{id} → delete own product

Pydantic Schemas (backend/schemas/product.py)
python
Copy
Edit
class ProductBase(BaseModel):
    title: str
    origin_country: str
    category: str
    description: str
    image_url: str
    price_per_kg: float

class ProductCreate(ProductBase): pass

class ProductOut(ProductBase):
    id: int
    owner_email: EmailStr
    change_pct: float    # ← added
    rating: float        # ← added

    class Config:
        orm_mode = True
Alembic Migration
Generated revision fa7a1f804df6_add_change_pct_rating_to_products.py

Applied via:

bash
Copy
Edit
alembic stamp aa5d58481454
alembic upgrade head
5.3 Deals (/deals)
GET /deals/ → list deals for current user (buyer or supplier)

POST /deals/ → create deal (calculates total_price, fills emails & IDs)

GET /deals/{id} → single deal (role‑guarded)

GET /deals/{id}/pdf → stream PDF summary (WeasyPrint)

Route (backend/routes/deal.py)
python
Copy
Edit
@router.post("/", response_model=DealOut)    # DealCreate → DealOut
def create_deal(...):
    # fetch product, supplier, build payload, persist, return

@router.get("/", response_model=List[DealOut])
def get_user_deals(...):
    # fetch where buyer_email==current_user or supplier_email==current_user

@router.get("/{deal_id}", response_model=DealOut)
def get_deal_by_id(...):
    # 404 if not found, 403 if not authorized

@router.get("/{deal_id}/pdf")
def generate_deal_pdf(...):
    # HTML → PDF bytes → StreamingResponse
5.4 Contracts (/contracts)
Stub endpoints:

POST /contracts/generate → draft contract via LLM

GET /contracts/{id} → details (future)

GET /contracts/{id}/pdf → PDF stream

POST /contracts/{id}/mint → mint NFT (future)

5.5 Admin (/admin)
CRUD on all users, products, deals, contracts

5.6 Users (/users)
PATCH /users/me/wallet → bind MetaMask wallet

(future) profile updates

Frontend Structure
6.1 Pages
text
Copy
Edit
/                Home (product listing + change% & rating)
/search          Search results table
/products/[id]   Product detail + change% & rating + "Get Quote"
/products/create Create product + upload image
/deals           Deals list (import Deal from types.ts)
/deals/[id]      Deal detail + debug logging + PDF link
/contracts       (stub) list of contracts
/contracts/[id]  Contract detail + PDF link (stub)
/login           Login form
/register/seller Seller sign‑up
/register/buyer  Buyer sign‑up
/dashboard       Role‑based dashboard skeleton
/admin/dashboard Admin panel
Key TS Files & Interfaces
frontend/types.ts

ts
Copy
Edit
export interface Deal {
  id: number
  buyer_email: string
  supplier_email: string
  product_title: string
  quantity_kg: number
  total_price: number
  status: string
  created_at: string
}
frontend/pages/search.tsx

Extended interface Product with change_pct & rating

Added table columns for Change % and Rating /10

frontend/pages/products/[id].tsx

Show {(prod.change_pct*100).toFixed(2)}% and {prod.rating.toFixed(1)}/10

Debug logging to console for router query, token, response

frontend/pages/deals/index.tsx

import { Deal } from '../../types'

Removed inline interface

frontend/pages/deals/[id].tsx

import { Deal } from '../../types'

Debug logging in useEffect

Handles 403 Forbidden when unauthorized

frontend/pages/contracts/[id].tsx (stub)

tsx
Copy
Edit
interface Contract { id: number; prompt: string; generated_contract: string; status: string }
// fetch /contracts/{id}, show HTML, link to PDF
6.2 Components
Navbar: logo, search bar, auth links, wallet connect

ProductCard: shows thumbnail, title, origin, price, change%, rating, view link

QuoteModal: quantity input → POST /deals/ → redirect /deals

SwapPanel: dummy currency swap UI (GBP/USD ↔ $GLU)

Sidebar: role‑based nav links

AgentBar: (future) contract prompt → POST /contracts/generate

Completed Features
🌐 Public marketplace: product listing, search

🖼️ Image upload for products

🔐 JWT auth + role‑based route protection

🦊 MetaMask wallet connect & backend binding

📝 Product CRUD (supplier)

📋 Deals CRUD + status flow (negotiation → confirmed)

📄 PDF generation of deal contract (WeasyPrint)

⚖️ Admin panel for all entities

🏗️ Next.js front‑end with Tailwind CSS

🔄 Dummy SwapPanel + sticky header layout

🚀 Escrow contract deployed on Polygon Amoy testnet

Search & Search Results
Home → search form

/search table with columns:

mathematica
Copy
Edit
Image | Product | Origin | Cost/kg | Supplier | Change % | Rating /10 | Details
Change% & Rating are now real fields from the API.

Quote & Deal Flow
Product detail (/products/{id})

Click Get Quote → open QuoteModal

Enter quantity → POST /deals/

On success, redirect to /deals list

Deal detail (/deals/{id}) shows data + download PDF link

Supplier confirms/rejects via their dashboard

AI Agent & Contract Engine
Stub: AgentBar to input prompt → POST /contracts/generate

Saves generated_contract HTML + status + pdf_url

Contract pages (/contracts/[id]) to review & download

Future: mint NFT certificate on-chain

Roadmap & Next Steps
Phase 2: Polish & Core Flows
Registration UIs: /register/seller, /register/buyer

Role dashboards: buyer/supplier views

Search filters: rating, tags, regions

Wire SwapPanel “Swap” → create a deal

Multi-image product uploads & certificates

Phase 3: On‑chain & Integrations
Real swap engine (Web3 + escrow contract)

Live commodity price feeds → change_pct

Product passports & NFT certificate explorer

Shipping API integration & QR tracking

Stripe + WalletConnect payments

Phase 4: AI & Automation
AI matching engine → POST /match → ranked suppliers

Autonomous trade agents & in‑chat negotiation

Messaging & dispute workflows

Rich contract templates & PDF styling

Phase 5: Governance & Expansion
COMDEX Chain (fork Polygon)

Governance token (CDXT) & staking

Global CDN & mobile apps

New commodity verticals and digital goods

Dev Commands
Backend
bash
Copy
Edit
cd ~/Desktop/Comdex/backend
source venv/bin/activate
# run server
uvicorn main:app --reload

# DB migrations
alembic revision --autogenerate -m "add change_pct & rating to products"
alembic upgrade head

# Restart if stuck
lsof -n -iTCP:8000 | awk 'NR>1 {print $2}' | xargs --no-run-if-empty kill -9
uvicorn main:app --reload
Frontend
bash
Copy
Edit
cd ~/Desktop/Comdex/frontend
npm install        # or yarn
npm run dev        # or yarn dev

# To create new pages
cd pages
mkdir -p deals contracts
touch deals/index.tsx deals/[id].tsx contracts/index.tsx contracts/[id].tsx

# To open files
nano pages/search.tsx
nano pages/products/[id].tsx
This document now reflects all recent migrations, schema changes, route updates, UI enhancements, debug processes, and the full feature roadmap. Use it as your single source of truth for onboarding, development, and continued planning.
