STICKEY Unified Handover & Reference
Table of Contents
Overview

Architecture

Authentication & Roles

Database Schemas

Backend Endpoints

5.1 Auth (/auth)

5.2 Products (/products)

5.3 Deals (/deals)

5.4 Contracts (/contracts) Stub

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

1. Overview
COMDEX (rebranded front-end STICKEY, coin ticker $GLU) is a next-gen global commodity-trading platform combining:

AI: autonomous agents for supplier matching & contract drafting

Blockchain: on-chain escrow & NFT certificates

Crypto-native features: wallet binding, swap panel, token flows

Mission: Revolutionize B2B commodity trade with trust, automation, and transparency.

V1 Target: Whey Protein (EU, USA, India, NZ)
V2+: Cocoa, coffee, olive oil, pea protein, spices, and beyond.

2. Architecture
scss
Copy
Edit
[Next.js Frontend] ←→ [FastAPI Backend] ←→ [PostgreSQL]
       │                    │
    MetaMask            Smart Contracts
       │                    │
    $GLU Wallet         Polygon Amoy Testnet
Frontend: Next.js + Tailwind CSS + TypeScript

Backend: FastAPI + SQLAlchemy + Pydantic + WeasyPrint (PDF)

DB: PostgreSQL

Blockchain: Polygon Amoy (escrow contract), future COMDEX Chain

AI: OpenAI LLM integrations under /agent and /contracts/generate

3. Authentication & Roles
JWT auth via /auth/register and /auth/login (tokens stored in localStorage).

Roles: admin / supplier / buyer.

MetaMask wallet connect + backend binding (PATCH /users/me/wallet).

Route Guards on front-end & back-end (role-based dependencies).

Demo credentials:

Role	Email	Password
admin	admin@example.com	admin123
supplier	supplier@example.com	supplypass
buyer	buyer@example.com	buyerpass

4. Database Schemas
users
id, name, email, password_hash

role (admin/supplier/buyer)

wallet_address

created_at, updated_at

products
id, owner_email (FK → users.email)

title, description, price_per_kg

origin_country, category, image_url

batch_number, trace_id, certificate_url, blockchain_tx_hash

created_at

deals
id, buyer_id (FK), supplier_id (FK), product_id (FK)

quantity_kg, agreed_price, currency

status: negotiation → confirmed → completed

created_at, pdf_url

(Stub) contracts
id, prompt (free-form)

generated_contract (Markdown/HTML)

status, pdf_url, nft_metadata

5. Backend Endpoints
5.1 Auth (/auth)
POST /register (name, email, password) → user + JWT

POST /login (email, password) → access_token

GET /role (Bearer token) → { role }

5.2 Products (/products)
Public

GET /products/ → list all products

GET /products/search?query=… → filtered by title/category

GET /products/{id} → single product

Authenticated

GET /products/me → supplier’s products

POST /products/ (JSON) → create (owner_email from JWT)

POST /products/create (multipart) → with file upload → saved in /uploaded_images

PUT /products/{id} → update own product

DELETE /products/{id} → delete own product

5.3 Deals (/deals)
GET /deals/ → list deals for current user (buyer or supplier)

POST /deals/ → create deal (buyer_email, supplier_email, product_title, quantity_kg, total_price)

GET /deals/{id} → fetch single deal

GET /deals/{id}/pdf → stream PDF contract

5.4 Contracts (/contracts) Stub
POST /contracts/generate → { prompt: str } → { id, generated_contract, status, pdf_url }

(future) GET /contracts/{id} → contract details

(future) POST /contracts/{id}/mint → mint NFT receipt

5.5 Admin (/admin)
CRUD on all users, products, deals

5.6 Users (/users)
PATCH /users/me/wallet → bind MetaMask wallet

(future) profile updates

6. Frontend Structure
6.1 Pages
bash
Copy
Edit
/                    Home (product listing + search form)
/search              Search results table
/products/[id]       Product detail + “Generate Quote” button
/products/create     Supplier: new product + image upload form
/deals               Listing page for deals
/deals/[id]          Deal detail + PDF link
/contracts/[id]      (Stub) Contract detail page
/login               Login form
/register/seller     Seller onboarding
/register/buyer      Buyer onboarding
/dashboard           Role-based dashboard skeleton
/admin/dashboard     Admin panel
6.2 Components
Navbar: logo, search bar (→ /search?query=), auth links, wallet connect

ProductCard: thumbnail, title, origin, price/kg, “View Product” (→ /products/{id})

QuoteModal: quantity input → POST /deals/ → redirect /deals

SwapPanel: dummy currency swap UI (GBP/USD ↔ $GLU)

Sidebar: role-based nav links

AgentBar: (future) contract prompt input → /contracts/generate

7. Completed Features
🌐 Public marketplace: product listing, search

🖼️ Image upload for products

🔐 JWT auth + role-based route protection

🦊 MetaMask wallet connect & backend binding

📝 Product CRUD (supplier)

📋 Deals CRUD + status flow (negotiation → confirmed)

📄 PDF generation of deal contract (WeasyPrint)

⚖️ Admin panel for all entities

🏗️ Next.js front-end with Tailwind CSS

🔄 Dummy SwapPanel + sticky header layout

🚀 Escrow contract deployed on Polygon Amoy testnet

8. Search & Search Results
Home page has a search form (<form action="/search">)

/search page displays results in a table with columns:

Image, Product, Origin, Cost /kg, Supplier, Change %, Rating /10, Details

Placeholder values for Change % and Rating

Future: real change_pct from commodity price feeds, actual rating and filter tags (organic, grass-fed, shipping regions).

9. Quote & Deal Flow
Product Detail: click “View Product” → /products/[id]

Generate Quote: opens QuoteModal, enter quantity → POST /deals/

Success: redirect to /deals listing; then detail /deals/[id]

Supplier confirms or rejects in their dashboard

PDF available via /deals/{id}/pdf

On-chain escrow integration planned (Phase 3).

10. AI Agent & Contract Engine
Agent Bar (future): text prompt → POST /contracts/generate

Contract Stub: returns Markdown/HTML draft + PDF URL + id

Contract page at /contracts/[id] to review & share

Mint NFT after both parties sign → on-chain certificate

Long-term: universal asset engine (cars, real-estate, NFTs, digital goods).

11. Roadmap & Next Steps
Phase 2 (Polish & Core Flows)
Registration UIs: /register/seller, /register/buyer

Dashboards:

Buyer: /dashboard → “My Deals”, wallet balance

Supplier: /dashboard → “My Products”, incoming quotes

Search filters: price, rating, tags (organic, regions)

SwapPanel → Deal: wire “Swap” button to /deals/

Product Detail: full specs, multi-image, cert uploads

Deals Listing: /deals page for both roles

Phase 3 (On-chain & Integrations)
Real swap engine (Web3 + escrow contract)

Live commodity price feeds → change_pct

Product passports & NFT certificate explorer

Shipping API integration & QR tracking

Stripe + WalletConnect for fiat/crypto payments

Phase 4 (AI & Automation)
AI Matching Engine: POST /match → ranked suppliers

Autonomous trade agents: in-chat negotiation

Messaging & dispute workflows

Contract LLM templates, PDF styling

Phase 5 (Governance & Expansion)
COMDEX Chain (fork Polygon → own EVM network)

Governance token (CDXT) & staking

Global CDN + mobile apps

New commodity verticals and digital goods.

12. Dev Commands
Backend
bash
Copy
Edit
cd ~/Desktop/Comdex/backend
source venv/bin/activate
uvicorn main:app --reload
# DB migrations
alembic upgrade head
Frontend
bash
Copy
Edit
cd ~/Desktop/Comdex/frontend
npm install    # or yarn
npm run dev    # or yarn dev
Restarting Backend
bash
Copy
Edit
lsof -n -iTCP:8000 | awk 'NR>1 {print $2}' | xargs --no-run-if-empty kill -9
cd ~/Desktop/Comdex/backend
source venv/bin/activate
uvicorn main:app --reload
This document consolidates all current setup, completed work, page/component structure, API routes, and the full feature roadmap—from MVP through AI-driven contract automation. It’s your single point of reference for onboarding new developers or AI agents and for tracking next steps at any point in time.
