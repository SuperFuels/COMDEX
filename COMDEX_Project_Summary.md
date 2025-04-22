🧾 COMDEX Project Summary (Updated — 2025-04-22)
🌍 Overview
COMDEX is a next-gen global commodity trading platform built for trust, automation, and transparency — combining AI, blockchain, and crypto-native features to reshape how global B2B trade happens.

🔹 Business Plan
🎯 Mission
Revolutionize global commodity trade with on-chain transparency, autonomous trade agents, and AI-powered deal intelligence.

❗ Problems Solved
Manual, fragmented global commodity trade

Trust and quality verification issues

Global payment friction and reconciliation delays

Supply chain traceability challenges

No unified B2B trade network with crypto-native design

🎯 Target Market
V1: Whey protein (EU, USA, India, NZ)

V2+: Cocoa, coffee, olive oil, pea protein, spices

💰 Revenue Model
2–3% transaction fee on deals

Premium supplier subscriptions

Supply chain passport licensing

FX/Crypto swap fee margins

Smart contract escrow fees

NFT verification certificate minting

✅ Version 1 — MVP (Shipped)
✅ Core Features
Supplier onboarding (KYC placeholder)

JWT-based authentication (register/login)

Buyer/supplier role-based dashboards

Product listing (title, price, origin, image, description)

Image upload (stored locally and served via /uploaded_images)

Manual deal logging + status flow

Deal PDF preview + download (via ReportLab)

Admin panel with visibility over all users/products/deals

Route protection by role (admin/supplier/buyer)

PostgreSQL + FastAPI backend

Next.js + Tailwind frontend

Stripe placeholder integration (ready for future crypto swap)

🧪 Demo Logins

Role	Email	Password
Admin	admin@example.com	admin123
🔐 Auth
JWT stored in localStorage

Role-based redirect on login (admin → /admin/dashboard, supplier → /supplier, etc.)

🧱 Database Schema (as of 2025-04-22)
📦 users
id, name, email, password_hash

role (admin/supplier/buyer)

wallet_address (nullable)

created_at, updated_at

📦 products
id, owner_email (FK)

title, description, price_per_kg

origin_country, category, image_url

batch_number, trace_id, certificate_url, blockchain_tx_hash

created_at

📦 deals
id, buyer_id, supplier_id, product_id

quantity_kg, agreed_price, currency

status: negotiation → confirmed → completed

created_at, pdf_url

🔁 COMDEX V2+ Roadmap — Next Steps (Priority Ordered)
✅ Phase 1: Wallet Connection (Done)
MetaMask wallet integration via window.ethereum

Wallet address shown on homepage

🔧 Phase 2: Wallet Identity Binding (Now)
Goal: Wallet = persistent login identity + dashboard access

Backend:

Add wallet_address to User model

Add PATCH /users/me/wallet endpoint (JWT required)

Frontend:

After MetaMask connect, call backend to bind wallet

Prepares for wallet login, smart contracts, NFTs

🧭 Phase 3: Buyer/Seller Onboarding UI Cleanup
Clean radio/dropdown selection for roles

Icons and role explanation

Visually distinct dashboards

🧾 Phase 4: Product Passport Schema
New fields on Product:

batch_number, trace_id, certificate_url, blockchain_tx_hash

Future /products/:id/passport API

QR code explorer / NFT integration

🤖 Phase 5: AI Matching Engine (Planning)
Endpoint: POST /match

Input: criteria (volume, location, category, price)

Output: Ranked supplier list

UI: Match cards

🔄 Phase 6: Swap Engine UI
Simulated FX/crypto swap

Choose: USD/EUR/ETH/BTC → CMDX

Placeholder only (no chain interaction yet)

⚡ Bonus Features (Coming in V2/V3)

Feature	Why It Matters
Wallet-Based Login	Sign & login directly with MetaMask
On-Chain Profile NFTs	Verify identity via tokenized user profiles
Marketplace Messaging	Direct buyer ↔ supplier communication
Smart Contract Escrow	Trustless deals using stablecoin
Gas Fee Estimator	Transparency before sending transactions
💸 COMDEX Coin Model (V2/V3)
🪙 1. COMDEX Stablecoin
Used for escrow & payment

Fiat-pegged, deal-specific

🔁 2. FX Swap Engine
USD/EUR/INR/ETH/BTC to CMDX

Uniswap-style

🚀 3. CDXT Investor Token ("Shitcoin")
Utility + speculation + DAO

🏦 4. CVAL Store-of-Value Coin
BTC-like deflationary reserve asset

🔗 Blockchain Strategy
Fork Polygon (EVM compatible)

Build COMDEX Chain:

Smart contract escrow

NFT COAs

QR traceability

Gas tracking + on-chain explorer

🤖 AI Agents (V2/V3)
Auto-matching suppliers

Agent-to-agent negotiation

AI alerts, price trend forecasts

Plug into GPT or custom LLM

✅ Dev Command Reference
✅ Backend
bash
Copy
Edit
source venv/bin/activate
cd backend
uvicorn main:app --reload
✅ Frontend
bash
Copy
Edit
cd frontend
npm install
npm run dev
✅ Database (if needed)
bash
Copy
Edit
cd backend
python create_tables.py
🧠 Progress Snapshot (as of 2025-04-22)
✅ Image path fix (uploaded_images serving)
✅ MetaMask wallet connected
✅ Role-based routing
✅ Product CRUD complete
✅ Deal system (PDF + status toggle)
✅ Admin dashboard live
✅ Navbar implemented
✅ Public marketplace + search
✅ Landing page + role split (next)

📂 GitHub Repo
🔗 https://github.com/SuperFuels/COMDEX
