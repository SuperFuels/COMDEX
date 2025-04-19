# COMDEX Project Summary (Updated - 2025-04-19)

## Overview
COMDEX is a modern global commodity marketplace, starting with whey protein, where verified suppliers can list products and buyers can transact using fiat (Stripe) or—eventually—cryptocurrency. It focuses on transparency, traceability, and frictionless trade, with on-chain systems and AI tools coming in future phases.

---

## 🔹 Business Plan

### Mission
Revolutionize global commodity trade by offering a transparent, traceable, and efficient platform for buyers and sellers.

### Problems Solved
- Fragmented manual commodity trade
- Lack of trust in product origin or quality
- Friction in global deal closure + payments
- No central hub for verified suppliers

### Target Market
- **V1**: Whey protein (EU, USA, India, NZ)
- **Future**: Cocoa, coffee, olive oil, pea protein, spices

### Revenue Model
- 2–3% commission on trades  
- Premium seller subscriptions (badging, analytics)  
- COA/lab verification and sustainability features  
- White-labeled passport licensing  
- **SWAP fee revenue** (v2+)

---

## ✅ Version 1 — MVP (Live & Complete)

- ✅ Supplier onboarding (KYC placeholder)
- ✅ JWT auth (register/login)
- ✅ Product listing (title, price, origin, image, description)
- ✅ Contact seller form (via email)
- ✅ Manual deal logging
- ✅ Deal status flow (Negotiation → Confirmed → Completed)
- ✅ PDF deal export
- ✅ Buyer/seller dashboards
- ✅ Admin panel (user, product, deal visibility)
- ✅ Stripe checkout placeholder
- ✅ Route protection (token-based)
- ✅ PostgreSQL + FastAPI backend
- ✅ Tailwind + Next.js frontend

---

## 🔄 Version 2 — Crypto + AI Expansion (Next Phase)

### 💡 Smart Trading Features
- 🔁 **In-dashboard SWAP system** (Revolut-style, fiat/crypto converter with fees)
- 🔐 **Smart contract escrow** (Polygon-based)
- 🌐 **Wallet integration** (Linked to user accounts)
- 🧠 **AI supplier matching engine**
- 📊 **Dynamic commodity pricing chart**
- 🧾 **JSON-based API refactor**
- 📱 **Mobile-first interface (React Native or PWA)**
- 🗂️ **COA upload + KYC doc field**

### 💸 Coin Structure
- 🪙 **COMDEX Stablecoin** (Main settlement token)
- 🔁 **FX Engine** (Live exchange rates to all major/minor fiat)
- 📈 **COMDEX Utility Token** (Revenue share)
- 🏦 **Store-of-value coin** (BTC-like)

---

## 🧬 Version 3 — Fully On-Chain Autonomous System (Future Vision)

### 🧾 Traceability + NFT Certification
- 🌍 On-chain deal settlement (smart contract receipts)
- 📜 Blockchain COA & Passport generator
- 🧾 Real-World Asset NFTs (proof of authenticity)

### 🔗 B2B Marketplace & Automation
- 🛒 Buyer Portal (Amazon-style product discovery)
- 🧰 Seller Portal (Seller Central controls)
- 🧠 Matching algorithms for demand/supply
- 🔁 Swap engine integrated in dashboard
- 🔄 Revenue from every transaction (SWAP, escrow, listing)

---

## 💻 Tech Stack

| Layer      | Technology                             |
|------------|-----------------------------------------|
| Frontend   | Next.js (React), TailwindCSS, Vercel    |
| Backend    | FastAPI, Uvicorn, PostgreSQL (RDS)      |
| Auth       | JWT (localStorage)                      |
| Payments   | Stripe (placeholder)                    |
| PDF Export | ReportLab                               |
| Storage    | Supabase / AWS S3 (planned)             |

---

## 🗃️ Database Schema (2025-04-19)

### `users`
- id (PK), name, email, password_hash
- role (buyer/seller/admin)
- kyc_status, created_at, updated_at

### `products`
- id (PK), owner_email (FK)
- title, description, price_per_kg, origin_country, image_url
- created_at

### `deals`
- id (PK), buyer_id (FK), seller_id (FK), product_id (FK)
- quantity_kg, agreed_price, currency
- status (negotiation → completed)
- pdf_url, created_at

---

## 🧱 Build Phases

### ✅ Phase 0: Setup
- GitHub Repo → `SuperFuels/COMDEX`
- Backend + Frontend scaffolded
- Local DB created, schema seeded

### ✅ Phase 1: Core Platform
- Auth system
- Product creation
- User dashboards

### ✅ Phase 2: Deal Flow + Export
- Deal status system
- PDF deal generator
- Admin dashboard (user/product management)

### 🔜 Phase 3: v2 Prep
- Wallet & swap interface
- Smart contract backend
- Mobile-first UX
- AI recommendations
- JSON API refactor

---

## 📦 Deployment Commands

```bash
# Backend
source venv/bin/activate
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# DB Tables
cd backend
python create_tables.py

