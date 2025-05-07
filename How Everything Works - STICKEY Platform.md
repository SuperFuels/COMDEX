STICKEY Unified Handover & Reference
Table of Contents
Overview

Architecture

Authentication & Roles

Database Schemas

Users

Products

Deals

Contracts

Backend Endpoints

Auth (/auth)

Products (/products)

Deals (/deals)

Contracts (/contracts)

Admin (/admin)

Users (/users)

Frontend Structure

Pages

Components

Completed Features

Search & Search Results

Quote & Deal Flow

AI Agent & Contract Engine

Roadmap & Next Steps

Dev Commands

1. Overview
COMDEX (front‑end branded STICKEY, ticker $GLU) is a next‑gen B2B commodity‑trading platform combining:

AI: autonomous agents for supplier matching & contract drafting

Blockchain: on‑chain escrow & NFT certificates

Crypto‑native: wallet binding, swap panel, token flows

Mission: Revolutionize global commodity trade with trust, automation, transparency.
V1 Target: Whey Protein (EU, USA, India, NZ)
V2+: Cocoa, coffee, olive oil, pea protein, spices, and beyond.

2. Architecture
less
Copy
Edit
[ Next.js Frontend ] ←→ [ FastAPI Backend ] ←→ [ PostgreSQL ]
           ↑                    ↑
  [ MetaMask + $GLU Wallet ]   [ Alembic Migrations ]
           ↑                    ↑
 [ Polygon Amoy Testnet Escrow Contract ] 
 (Future: COMDEX Chain)
Frontend: Next.js + Tailwind CSS + TypeScript

Backend: FastAPI + SQLAlchemy + Pydantic + WeasyPrint (PDF)

DB: PostgreSQL

Blockchain: Polygon Amoy (escrow contract), future COMDEX Chain

AI: OpenAI LLM integrations under /agent and /contracts/generate

3. Authentication & Roles
JWT auth via /auth/register & /auth/login

Roles: admin / supplier / buyer

MetaMask wallet connect + backend binding (PATCH /users/me/wallet)

Route guards on both front-end & back-end

Demo credentials:

Admin: admin@example.com / admin123

Supplier: supplier@example.com / supplypass

Buyer: buyer@example.com / buyerpass

4. Database Schemas
4.1 Users
id, name, email, password_hash

role: admin/supplier/buyer

wallet_address

created_at, updated_at

4.2 Products
id, owner_email (FK → users.email)

title, description, price_per_kg

origin_country, category, image_url

New: change_pct (FLOAT), rating (FLOAT)

New: batch_number, trace_id, certificate_url, blockchain_tx_hash

created_at

4.3 Deals
id, buyer_id (FK → users.id), supplier_id

product_id (FK → products.id)

quantity_kg, total_price

status: negotiation → confirmed → completed

created_at, pdf_url

4.4 Contracts
id, prompt (TEXT), generated_contract (HTML/Markdown)

status, pdf_url, nft_metadata (stub)

5. Backend Endpoints
5.1 Auth (/auth)
POST /register → user + JWT

POST /login → { access_token, token_type }

GET /role (Bearer) → { role }

5.2 Products (/products)
Public

GET /products → all products (includes change_pct, rating)

GET /products/search?query=…

GET /products/{id}

Authenticated (supplier)

GET /products/me → own products

POST /products → create

POST /products/create → multipart file upload

PUT /products/{id}, DELETE /products/{id}

5.3 Deals (/deals)
GET /deals → list for current user

POST /deals → create (calculates total_price)

GET /deals/{id} → single deal (role‑guarded)

GET /deals/{id}/pdf → PDF summary

5.4 Contracts (/contracts)
POST /contracts/generate → draft via LLM

GET /contracts/{id} → details

GET /contracts/{id}/pdf → PDF stream

POST /contracts/{id}/mint → mint NFT (future)

5.5 Admin (/admin)
CRUD all users, products, deals, contracts

5.6 Users (/users)
PATCH /users/me/wallet → bind MetaMask wallet

(future) profile updates

6. Frontend Structure
6.1 Pages
bash
Copy
Edit
/                    Home (Marketplace + chart + table)
/search              Search results table
/products/[id]       Product detail (+ Lock‑in, Sample, Zoom buttons)
/products/[id]/sample  Sample Request form
/products/[id]/zoom    Zoom Request form
/products/create     Create Product
/deals               (moved into “Deal Flow” tab)
/deals/[id]          Deal detail + PDF link
/contracts           Contracts list (stub)
/contracts/[id]      Contract detail (stub)
/login               Login form
/register/supplier   Supplier sign‑up
/register/buyer     Buyer sign‑up
/dashboard           Role‑based dashboard (supplier & buyer)
/admin/dashboard     Admin panel
6.2 Components
Navbar: logo, search, auth links, wallet connect (sticky)

SwapBar: inline amount/token swap UI (sticky below Navbar)

Chart: Recharts line chart component

ProductCard: card with image, price, change%, rating, tags, Chart link

QuoteModal: quantity input → create deal

Sidebar: filters & selected commodity

DashboardTabs: buyer “Deal Flow” etc.

7. Completed Features
🌐 Public marketplace: listing + filters

🖼️ Image upload for products

🔐 JWT auth + role‑based guards

🦊 MetaMask wallet binding

📝 Product CRUD (supplier)

📋 Deals CRUD + status flow

📄 PDF generation (WeasyPrint)

⚖️ Admin panel

🔄 SwapPanel (dummy) + sticky layout

🚀 Escrow contract on Polygon Amoy testnet

📊 Live charts (stub data)

📑 Sample Request page

📹 Zoom Request page

8. Search & Search Results
/search table with columns: Image | Product | Origin | Cost/kg | Supplier | Change % | Rating /10 | Details

9. Quote & Deal Flow
Product details → “Lock in GLU Quote” button → open QuoteModal

New “Deal Flow” tab on Buyer Dashboard replaces /deals page

Buyers view and manage all deals under tabbed interface

10. AI Agent & Contract Engine
Stub: AgentBar → POST /contracts/generate → save draft

Contract pages (/contracts/[id]) to review & download PDF

11. Roadmap & Next Steps
Phase 2: Polish & Core Flows
Registration UIs: /register/supplier, /register/buyer

Role dashboards refinement

Search filters: rating, tags, regions

SwapPanel “Swap” → create deal

Multi-image uploads & NFT certificate explorer

New Feature Proposal: Blockchain-Based Trust System
“TrustlessTrust” – tokenized real‑world assets held in smart‑contract trusts with programmable beneficiaries and revenue streams.

Asset Tokenization: NFTs for deeds, IP, artwork

Smart Trust: Solidity contracts enforce distribution rules

Streaming Income: e.g. Superfluid, DeFi yields

Legal Wrapper: Wyoming DAO law, Swiss trusts

Phase 3: On‑chain & Integrations
Real swap engine (Web3 + escrow)

Live commodity price feeds → real change_pct

Product passports & NFT certificates

Shipping API & QR tracking

Stripe + WalletConnect payments

Phase 4: AI & Automation
Autonomous trade agents & negotiation

Messaging & dispute workflows

Rich contract templates & styling

Phase 5: Governance & Expansion
COMDEX Chain (Polygon fork)

Governance token (CDXT), staking

CDN & mobile apps

New commodity verticals & digital goods

12. Dev Commands
Backend
bash
Copy
Edit
cd ~/Desktop/Comdex/backend
source venv/bin/activate
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
npm install       # or yarn
npm run dev       # or yarn dev

# Tailwind config & next.config.js updated for custom colors, fonts, remotePatterns
# Env vars required:
#   NEXT_PUBLIC_API_URL
#   NEXT_PUBLIC_GLU_TOKEN_ADDRESS
#   NEXT_PUBLIC_ESCROW_ADDRESS
Creating & Opening Files
bash
Copy
Edit
# Dashboard, pages, components
nano pages/dashboard.tsx
nano pages/products/[id].tsx
nano components/SwapBar.tsx
nano components/Chart.tsx
