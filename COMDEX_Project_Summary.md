# 🧾 COMDEX Project Summary (Updated — 2025-04-21)

## 🌍 Overview

COMDEX is a decentralized commodity marketplace where verified suppliers can list real-world goods and global buyers can transact using fiat or crypto. It enables traceable, on-chain transactions with PDF exports, smart contracts, and future AI agent functionality.

Built for trust, compliance, and automation — COMDEX is the **Google of B2B transactions**, with **OpenSea-level transparency**, **Apple-level polish**, and **Etherscan-style clarity**.

---

## 🔹 Business Plan

### 🎯 Mission
Revolutionize global trade by offering an AI-driven, blockchain-powered transaction platform that ensures transparency, traceability, and verified sourcing.

### ❗ Problems Solved
- Manual and opaque global trading
- Trust & traceability gaps in commodity supply chains
- Currency & payment friction across borders
- Lack of a real-time transaction passport

### 🎯 Target Market
- **V1**: Whey protein (US, EU, India, NZ)
- **V2+**: Cocoa, coffee, olive oil, pea protein, spices, grains

### 💰 Revenue Model
- 2–3% transaction fee
- Premium seller subscriptions (badging, analytics)
- COA + Passport NFT licensing
- On-chain SWAP and escrow fees
- Utility token reward loops

---

## ✅ Version 1 — MVP (Fully Functional)

### ✅ Core Features
- ✅ Supplier onboarding (KYC placeholder)
- ✅ JWT auth (register/login)
- ✅ Product listing: title, description, price, country, image
- ✅ Local image upload
- ✅ Deal logging + status updates
- ✅ Deal PDF generation (via ReportLab)
- ✅ Buyer/seller dashboards
- ✅ Admin panel (view all users/products/deals)
- ✅ Route guards for protected pages
- ✅ Stripe placeholder (crypto support coming)
- ✅ PostgreSQL + FastAPI backend
- ✅ Next.js + Tailwind frontend

---

## 🧠 Live Auth & DB (Demo Setup)

| Role    | Email               | Password  |
|---------|---------------------|-----------|
| Admin   | admin@example.com   | admin123  |

- DB Username: `comdex`  
- DB Password: `Wn8smx123`  
- DB Name: `comdex`  

---

## 🧱 Directory Structure

COMDEX/ ├── backend/ │ ├── main.py │ ├── models/ # user.py, product.py, deal.py │ ├── routes/ # auth.py, product.py, deal.py, admin.py │ ├── schemas/ # user.py, product.py, deal.py, admin.py │ ├── utils/ # auth.py │ ├── uploaded_images/ │ └── create_tables.py │ ├── frontend/ │ ├── pages/ │ │ ├── index.tsx # Public landing (coming in V2) │ │ ├── login.tsx, register.tsx │ │ ├── dashboard.tsx │ │ ├── products/ │ │ │ ├── new.tsx, edit/[id].tsx │ │ ├── deals/ │ │ │ ├── index.tsx, new.tsx │ │ └── admin/ │ │ └── dashboard.tsx │ ├── components/ │ │ └── ProductCard.tsx │ └── hooks/ │ └── useAuthRedirect.ts

---

## 🔜 Version 2 — Crypto + AI Expansion

### 📦 Core Modules
- [ ] **Public Landing Page**  
  - Browse products without login  
  - Search bar, featured categories  
  - Buyers & Sellers only log in for action (not viewing)

- [ ] **Buyer/Seller Onboarding Split**  
  - Role selector during signup  
  - Separate dashboard experiences  
  - Seller gets "Add Product" + Passport features

- [ ] **Wallet Integration (MetaMask / Supabase WalletKit)**  
  - Connect wallet  
  - Future: optional login via wallet only  
  - Link wallet to user identity

- [ ] **Smart Contract Escrow (Polygon fork)**  
  - Deploy COMDEX smart contract to Polygon chain  
  - Trigger escrow on deal confirmation  
  - Release on "Completed" status  
  - All physical products → linked NFT Passport

- [ ] **FX Engine + SWAP UI**  
  - Fiat-to-crypto + crypto-to-crypto converter  
  - Fee per swap  
  - Transparent rates in dashboard

- [ ] **OpenSea-style Marketplace Module**  
  - NFT-backed real-world goods  
  - QR code → smart contract tx → Etherscan link  
  - View ownership & COA/NFT status

- [ ] **Traceability + QR Linking**  
  - Every physical product deal → PDF + QR code  
  - QR links to transaction hash (Etherscan)  
  - Border/customs can scan to verify product

- [ ] **AI Matching Engine**  
  - Match buyers to top suppliers  
  - Recommend deals based on market patterns  
  - Predict best pricing windows using trend data

- [ ] **Mobile-First PWA or React Native App**

---

## 💸 COMDEX Coin Ecosystem

| Coin Type            | Symbol  | Use Case                                  |
|----------------------|---------|-------------------------------------------|
| Stablecoin           | $CMDX   | Escrow, stable trading pair               |
| Utility Token        | $CDXT   | Rewards, staking, governance              |
| Store-of-Value Coin  | $CVAL   | Bitcoin-like scarcity store               |

- Deployed on Polygon-forked chain
- All transactions on COMDEX are recorded on-chain
- Compatible with major exchanges

---

## 🤖 V3: AI Agent + Autonomous Protocol

- AI agents can negotiate on behalf of users
- Agent-to-Agent Protocol integration
- Zero-knowledge proof verification of COA
- Autonomous deal routing

---

## 🛠️ Deployment Commands

### 🐍 Backend
```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload

cd frontend
npm install
npm run dev

cd backend
python create_tables.py

