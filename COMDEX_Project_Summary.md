# 🧾 COMDEX Project Summary (Updated — 2025-04-30)

## 🌍 Overview
COMDEX is a next-gen global commodity trading platform built for trust, automation, and transparency — combining AI, blockchain, and crypto-native features to reshape how global B2B trade happens.

---

## 🔹 Business Plan

### 🎯 Mission
Revolutionize global commodity trade with on-chain transparency, autonomous trade agents, and AI-powered deal intelligence.

### ❗ Problems Solved
- Manual, fragmented global commodity trade
- Trust and quality verification issues
- Global payment friction and reconciliation delays
- Supply chain traceability challenges
- No unified B2B trade network with crypto-native design

### 🎯 Target Market
- **V1**: Whey protein (EU, USA, India, NZ)
- **V2+**: Cocoa, coffee, olive oil, pea protein, spices

### 💰 Revenue Model
- 2–3% transaction fee on deals
- Premium supplier subscriptions
- Supply chain passport licensing
- FX/Crypto swap fee margins
- Smart contract escrow fees
- NFT verification certificate minting

---

## ✅ Version 1 — MVP (Shipped)

### ✅ Core Features
- Supplier onboarding (KYC placeholder)
- JWT-based authentication (register/login)
- Buyer/supplier/admin role-based dashboards
- Product listing: title, price, origin, image, description
- Image upload (stored locally in `/uploaded_images`)
- Manual deal logging + status flow (negotiation → confirmed → completed)
- Deal PDF preview + download (WeasyPrint + StreamingResponse)
- Admin panel: manage all users/products/deals
- Route protection (role-based auth: admin/supplier/buyer)
- PostgreSQL + FastAPI backend
- Next.js + Tailwind CSS frontend
- Stripe placeholder (future crypto swap integration)
- MetaMask wallet connection + binding

---

## 🧪 Demo Logins

| Role    | Email               | Password   |
|---------|---------------------|------------|
| Admin   | admin@example.com   | admin123   |

---

## 🔐 Auth
- JWT stored in localStorage
- Role-based redirect (admin → `/admin/dashboard`, supplier → `/supplier`, etc.)

---

## 🧱 Database Schema (2025-04-30)

### 📦 users
- `id`, `name`, `email`, `password_hash`
- `role` (admin/supplier/buyer)
- `wallet_address` (optional)
- `created_at`, `updated_at`

### 📦 products
- `id`, `owner_email` (FK)
- `title`, `description`, `price_per_kg`
- `origin_country`, `category`, `image_url`
- `batch_number`, `trace_id`, `certificate_url`, `blockchain_tx_hash`
- `created_at`

### 📦 deals
- `id`, `buyer_id`, `supplier_id`, `product_id`
- `quantity_kg`, `agreed_price`, `currency`
- `status`: `negotiation` → `confirmed` → `completed`
- `created_at`, `pdf_url`

---

## 🔁 COMDEX V2+ Roadmap — Next Steps

### ✅ Phase 1: Wallet Connection
- ✅ MetaMask wallet integration via `window.ethereum`
- ✅ Wallet address shown and bound in backend

### ✅ Phase 2: Wallet Identity Binding
- PATCH `/users/me/wallet`
- Allows smart contract actions per user

### 🔧 Phase 3: Buyer/Seller Onboarding UI Cleanup
- Distinct flows and role UI elements

### 🧾 Phase 4: Product Passport Schema
- Includes: `batch_number`, `trace_id`, `certificate_url`, `blockchain_tx_hash`
- Future: QR + NFT explorer for product authenticity

### 🤖 Phase 5: AI Matching Engine (Planned)
- POST `/match` with criteria → returns ranked suppliers

### 🔄 Phase 6: Swap Engine UI
- Simulated swap USD/EUR/BTC/ETH → CMDX

---

## ⚡ Bonus Features (Coming V2/V3)

| Feature                  | Why It Matters                        |
|--------------------------|----------------------------------------|
| Wallet-Based Login       | Authenticate with MetaMask            |
| On-Chain Profile NFTs    | Verify suppliers/buyers                |
| Marketplace Messaging    | In-platform buyer/supplier comms       |
| Smart Contract Escrow    | Trustless settlement                   |
| Gas Fee Estimator        | Cost transparency for transactions     |

---

## 💸 COMDEX Coin Model (V2/V3)

### 🪙 1. COMDEX Stablecoin
- For escrow payments
- Fiat-pegged

### 🔁 2. FX Swap Engine
- Convert USD/EUR/ETH/BTC to CMDX

### 🚀 3. CDXT Investor Token ("Shitcoin")
- Utility + governance + speculation

### 🏦 4. CVAL Store-of-Value Coin
- Deflationary reserve

---

## 🔗 Blockchain Strategy

- Fork Polygon (EVM-compatible)
- Build **COMDEX Chain**
  - Smart contract escrow (Polygon Amoy now)
  - On-chain NFT certificates
  - Gas tracking
  - QR-linked transactions

### ✅ Escrow Contract Setup

- ✅ Deployed on: **Polygon Amoy Testnet**
- ✅ Contract address: `0xC4e695966B04fB8ee57d09Fa39A81a8b9582279b`
- ✅ Buyer wallet: `0x89F44431d03C175cd8758f69Aa1F9A5F89064Db4`
- ✅ Seller wallet: `0xC8F9CbF2712fbA4e123D1855A4665544B6b535A9`

---

## 🤖 AI Agents (V2/V3)
- Autonomous supplier matching
- Agent-to-agent trade negotiation
- GPT + LLM integration

---

## ✅ Dev Command Reference

### ✅ Backend
```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload
```

### ✅ Frontend
```bash
cd frontend
npm install
npm run dev
```

### ✅ Database
```bash
cd backend
alembic upgrade head  # or python create_tables.py
```

---

## 🧠 Progress Snapshot (as of 2025-04-30)

✅ Image upload fixed (local + display)✅ MetaMask wallet connected✅ Role-based dashboard routing✅ Product CRUD complete✅ Deal system (status toggle + PDF)✅ Admin dashboard live✅ Public marketplace search✅ Wallet-to-user binding✅ Smart contract deployed on Polygon✅ Escrow call from frontend (MetaMask)✅ Landing page + role split (next)

---

## 📂 GitHub Repo

🔗 https://github.com/SuperFuels/COMDEX

