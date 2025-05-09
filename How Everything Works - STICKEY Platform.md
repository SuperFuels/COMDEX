# How Everything Works — STICKEY Platform

## Table of Contents
1. [Overview](#overview)  
2. [Architecture](#architecture)  
3. [Authentication & Roles](#authentication--roles)  
4. [Database Schemas](#database-schemas)  
   1. [Users](#users)  
   2. [Products](#products)  
   3. [Deals](#deals)  
   4. [Contracts](#contracts)  
5. [Backend Endpoints](#backend-endpoints)  
   1. [Auth (`/auth`)](#auth-auth)  
   2. [Products (`/products`)](#products-products)  
   3. [Deals (`/deals`)](#deals-deals)  
   4. [Contracts (`/contracts`)](#contracts-contracts)  
   5. [Admin (`/admin`)](#admin-admin)  
   6. [Users (`/users`)](#users-users)  
6. [Frontend Structure](#frontend-structure)  
   1. [Pages](#pages)  
   2. [Components](#components)  
7. [Completed Features](#completed-features)  
8. [Search & Search Results](#search--search-results)  
9. [Quote & Deal Flow](#quote--deal-flow)  
10. [AI Agent & Contract Engine](#ai-agent--contract-engine)  
11. [Roadmap & Next Steps](#roadmap--next-steps)  
12. [Dev Commands](#dev-commands)  

---

## 1. Overview
COMDEX (front‑end branded **STICKEY**, ticker **$GLU**) is a next‑gen B2B commodity‑trading platform combining:
- **AI**: autonomous agents for supplier matching & contract drafting  
- **Blockchain**: on‑chain escrow & NFT certificates  
- **Crypto‑native**: wallet binding, swap panel, token flows  

**Mission**: Revolutionize global commodity trade with trust, automation, transparency.  
**V1 Target**: Whey Protein (EU, USA, India, NZ)  
**V2+**: Cocoa, coffee, olive oil, pea protein, spices, and beyond.

---

## 2. Architecture

[ Next.js Frontend ] ↔ [ FastAPI Backend ] ↔ [ PostgreSQL ]
↑
[ MetaMask + $GLU Wallet ]
[ Alembic Migrations ]
↑
[ Polygon Amoy Testnet Escrow Contract ]
(Future: COMDEX Chain)

markdown
Copy
Edit

- **Frontend**: Next.js + Tailwind CSS + TypeScript  
- **Backend**: FastAPI + SQLAlchemy + Pydantic + WeasyPrint (PDF)  
- **DB**: PostgreSQL  
- **Blockchain**: Polygon Amoy testnet (escrow contract), future COMDEX Chain  
- **AI**: OpenAI LLM integrations under `/agent` and `/contracts/generate`

---

## 3. Authentication & Roles

- **JWT auth** via `/auth/register` & `/auth/login`  
- **SIWE** (Sign‑In With Ethereum) wallet login & backend binding  
- **Roles**: `admin` / `supplier` / `buyer`  
- **Route guards** on both front‑end (React hook) & back‑end (FastAPI dependencies)  
- **Dev stub** in v1: SIWE `/verify` always returns `role: "supplier"` for rapid testing  

**Demo credentials** (email/password):
- Admin: `admin@example.com` / `admin123`  
- Supplier: `supplier@example.com` / `supplypass`  
- Buyer: `buyer@example.com` / `buyerpass`  

---

## 4. Database Schemas

### 4.1 Users
- `id` (PK)  
- `name`  
- `email` (nullable for wallet‑only users)  
- `password_hash` (nullable for wallet‑only users)  
- `role`: `admin` / `supplier` / `buyer`  
- `wallet_address` (EIP‑55 normalized, nullable)  
- `created_at`, `updated_at`

### 4.2 Products
- `id` (PK)  
- `owner_email` (FK → `users.email`)  
- `title`, `description`  
- `price_per_kg`  
- `origin_country`, `category`  
- `image_url`  
- **New**: `change_pct` (FLOAT), `rating` (FLOAT)  
- **New**: `batch_number`, `trace_id`, `certificate_url`, `blockchain_tx_hash`  
- `created_at`

### 4.3 Deals
- `id` (PK)  
- `buyer_id` (FK → `users.id`), `supplier_id` (FK → `users.id`)  
- `product_id` (FK → `products.id`)  
- `quantity_kg`, `total_price`  
- `status`: `negotiation` → `confirmed` → `completed`  
- `created_at`, `pdf_url`

### 4.4 Contracts
- `id` (PK)  
- `prompt` (TEXT)  
- `generated_contract` (HTML/Markdown)  
- `status`  
- `pdf_url`  
- `nft_metadata` (stub)  

---

## 5. Backend Endpoints

### 5.1 Auth (`/auth`)
| Method | Path         | Description                                  | Auth                 |
|--------|--------------|----------------------------------------------|----------------------|
| POST   | `/register`  | Register user (email/password + role)        | —                    |
| POST   | `/login`     | Email/password login → JWT                   | —                    |
| GET    | `/nonce`     | SIWE: issue nonce & EIP‑4361 message         | —                    |
| POST   | `/verify`    | SIWE: verify signature → JWT + role          | —                    |
| GET    | `/role`      | Validate JWT → `{ role }`                    | Bearer JWT           |

### 5.2 Products (`/products`)
| Method | Path                 | Description                              | Auth                  |
|--------|----------------------|------------------------------------------|-----------------------|
| GET    | `/`                  | List all products                        | Public                |
| GET    | `/search?query=…`    | Search products                          | Public                |
| GET    | `/{id}`              | Single product details                   | Public                |
| GET    | `/me`                | List supplier’s own products             | Bearer supplier JWT   |
| POST   | `/`                  | Create product                           | Bearer supplier JWT   |
| POST   | `/create`            | Create + file upload                     | Bearer supplier JWT   |
| PUT    | `/{id}`              | Update product                           | Bearer supplier JWT   |
| DELETE | `/{id}`              | Delete product                           | Bearer supplier JWT   |

### 5.3 Deals (`/deals`)
| Method | Path                     | Description                              | Auth                    |
|--------|--------------------------|------------------------------------------|-------------------------|
| GET    | `/`                      | List deals for current user              | Bearer JWT              |
| POST   | `/`                      | Create deal (calculates total_price)     | Bearer JWT              |
| GET    | `/{id}`                  | Get single deal                          | Bearer JWT + role‑guard |
| GET    | `/{id}/pdf`              | Download deal summary as PDF             | Bearer JWT              |
| PUT    | `/{id}/status`           | Update deal status                      | Bearer admin or parties |
| POST   | `/{id}/release`          | Release funds on‑chain                   | Bearer buyer/supplier   |

### 5.4 Contracts (`/contracts`)
| Method | Path                        | Description                              | Auth                    |
|--------|-----------------------------|------------------------------------------|-------------------------|
| POST   | `/generate`                 | Draft via LLM                            | Bearer JWT              |
| GET    | `/{id}`                     | Contract details                        | Bearer JWT              |
| GET    | `/{id}/pdf`                 | Download contract as PDF                 | Bearer JWT              |
| POST   | `/{id}/mint`                | Mint NFT (future)                       | Bearer JWT              |

### 5.5 Admin (`/admin`)
CRUD endpoints for all resources (users, products, deals, contracts).  
Accessible only to `admin` role via JWT.

### 5.6 Users (`/users`)
| Method | Path                          | Description                           | Auth       |
|--------|-------------------------------|---------------------------------------|------------|
| PATCH  | `/me/wallet`                  | Bind MetaMask wallet to user          | Bearer JWT |

---

## 6. Frontend Structure

### 6.1 Pages
/ → Home / Marketplace
/search → Search results
/products/[id] → Product detail
/products/[id]/sample → Sample request form
/products/[id]/zoom → Zoom request form
/products/create → Create product
/deals → (moved into Deal Flow tab)
/deals/[id] → Deal detail + PDF download
/contracts → Contracts list (stub)
/contracts/[id] → Contract detail (stub)
/login → Email/password login
/register/supplier → Supplier sign‑up
/register/buyer → Buyer sign‑up
/dashboard → Supplier dashboard
/buyer/dashboard → Buyer dashboard
/admin/dashboard → Admin panel

markdown
Copy
Edit

### 6.2 Components
- **Navbar**: logo, search, auth links, wallet connect (sticky)  
- **SwapBar**: inline amount/token swap UI (sticky)  
- **Chart**: Recharts line‑chart component  
- **ProductCard**: card with image, price, change%, rating, details link  
- **QuoteModal**: quantity input → create deal  
- **Sidebar**: filters & selected commodity  
- **DashboardTabs**: tabs for deals/contracts per role  

---

## 7. Completed Features
- 🌐 Public marketplace with listings & filters  
- 🖼️ Image upload & display for products  
- 🔐 Email/password JWT auth & role‑based guards  
- 🦊 MetaMask wallet connect & SIWE flow (DEV stub)  
- 📝 Product CRUD (supplier)  
- 📋 Deal creation & status workflow  
- 📄 PDF generation (WeasyPrint) for deals & contracts  
- ⚖️ Admin panel for full CRUD  
- 🔄 Sticky SwapPanel (dummy)  
- 🚀 Polygon Amoy escrow contract integration (testnet)  
- 📊 Live charts with stub data  
- 📑 Sample & Zoom request pages  

---

## 8. Search & Search Results
- `/search` page shows a table with:  
  - Image | Title | Origin | Price/kg | Supplier | Change % | Rating /10 | Details  

---

## 9. Quote & Deal Flow
- On `/products/[id]`, “Lock in GLU Quote” opens **QuoteModal**  
- Buyers confirm quantity → POST `/deals` → redirect to `/buyer/dashboard`  
- **Buyer Dashboard** tabbed interface replaces old `/deals` page  

---

## 10. AI Agent & Contract Engine
- **AgentBar** stub on `/contracts` → POST `/contracts/generate` → save draft  
- Contracts pages allow review & PDF download  

---

## 11. Roadmap & Next Steps

### Phase 2: Core Flows & Polish
1. Restrict `useAuthRedirect` to page‑level only (remove from layout)  
2. Harden SIWE real‑world flow (remove DEV stub)  
3. Add registration UIs (`/register/*`)  
4. Enhanced search filters (rating, tags, regions)  
5. SwapPanel → real on‑chain swap & deal creation  
6. Multi‑image uploads & NFT certificate viewer  

### Phase 3: On‑chain & Integrations
- Real swap engine & escrow interactions  
- Live price feeds → dynamic `change_pct`  
- Shipping API & QR tracking  
- Stripe + WalletConnect payments  

### Phase 4: AI & Automation
- Autonomous negotiation agents  
- Messaging & dispute resolution  
- Rich contract templates & styling  

### Phase 5: Governance & Expansion
- Launch COMDEX Chain (Polygon fork)  
- Governance token (CDXT), staking & DAO  
- Mobile apps & global expansion  

---

## 12. Dev Commands

### Backend
```bash
cd ~/Desktop/Comdex/backend
source .venv/bin/activate
uvicorn main:app --reload

# DB migrations
alembic revision --autogenerate -m "add new fields"
alembic upgrade head

# Kill & restart if port stuck
lsof -n -iTCP:8000 | awk 'NR>1 {print $2}' | xargs --no-run-if-empty kill -9
uvicorn main:app --reload
Frontend
bash
Copy
Edit
cd ~/Desktop/Comdex/frontend
npm install        # or yarn
npm run dev        # or yarn dev
Environment (.env.local):

env
Copy
Edit
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GLU_TOKEN_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
NEXT_PUBLIC_ESCROW_ADDRESS=0xe7f1725e7734ce288f8367e1bb143e90bb3f0512
NEXT_PUBLIC_WEB3_PROVIDER_URL=http://127.0.0.1:8545
Editing Files:

bash
Copy
Edit
nano pages/dashboard.tsx
nano pages/buyer/dashboard.tsx
nano components/Navbar.tsx
nano lib/api.ts
