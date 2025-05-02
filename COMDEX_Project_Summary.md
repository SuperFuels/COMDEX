COMDEX Project Summary (Updated — 2025-04-30)
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

Supplier Onboarding (KYC placeholder)

JWT-based Authentication (register/login)

Buyer/Supplier/Admin Role-based Dashboards

Product Listing: title, price, origin, image, description

Image Upload (stored locally in /uploaded_images)

Manual Deal Logging + Status Flow (negotiation → confirmed → completed)

Deal PDF Preview + Download (WeasyPrint + StreamingResponse)

Admin Panel: manage all users/products/deals

Route Protection (role-based auth: admin/supplier/buyer)

PostgreSQL + FastAPI Backend

Next.js + Tailwind CSS Frontend

Stripe Placeholder (future crypto swap integration)

MetaMask Wallet Connection + Binding

🧪 Demo Logins

Role	Email	Password
Admin	admin@example.com	admin123

🔐 Auth

JWT stored in LocalStorage

Role-based Redirect (admin → /admin/dashboard, supplier → /supplier, etc.)

🧱 Database Schema (2025-04-30)
📦 users

id, name, email, password_hash

role (admin/supplier/buyer)

wallet_address (optional)

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

🔁 COMDEX V2+ Roadmap — Next Steps
✅ Phase 1: Wallet Connection

MetaMask wallet integration via window.ethereum

Wallet address shown and bound in the backend

✅ Phase 2: Wallet Identity Binding

PATCH /users/me/wallet

Allows smart contract actions per user

🔧 Phase 3: Buyer/Seller Onboarding UI Cleanup

Distinct flows and role UI elements

🧾 Phase 4: Product Passport Schema

Includes: batch_number, trace_id, certificate_url, blockchain_tx_hash

Future: QR + NFT explorer for product authenticity

🤖 Phase 5: AI Matching Engine (Planned)

POST /match with criteria → returns ranked suppliers

🔄 Phase 6: Swap Engine UI

Simulated swap USD/EUR/BTC/ETH → CMDX

⚡ Bonus Features (Coming V2/V3)
Feature	Why It Matters
Wallet-Based Login	Authenticate with MetaMask
On-Chain Profile NFTs	Verify suppliers/buyers
Marketplace Messaging	In-platform buyer/supplier communications
Smart Contract Escrow	Trustless settlement
Gas Fee Estimator	Cost transparency for transactions

💸 COMDEX Coin Model (V2/V3)

COMDEX Stablecoin: For escrow payments (Fiat-pegged)

FX Swap Engine: Convert USD/EUR/ETH/BTC to CMDX

CDXT Investor Token: ("Shitcoin") Utility + governance + speculation

CVAL Store-of-Value Coin: Deflationary reserve

🔗 Blockchain Strategy

Fork Polygon (EVM-compatible)

Build COMDEX Chain

Smart contract escrow (Polygon Amoy now)

On-chain NFT certificates

Gas tracking

QR-linked transactions

✅ Escrow Contract Setup

Deployed on: Polygon Amoy Testnet

Contract address: 0xC4e695966B04fB8ee57d09Fa39A81a8b9582279b

Buyer wallet: 0x89F44431d03C175cd8758f69Aa1F9A5F89064Db4

Seller wallet: 0xC8F9CbF2712fbA4e123D1855A4665544B6b535A9

🤖 AI Agents (V2/V3)
Autonomous supplier matching

Agent-to-agent trade negotiation

GPT + LLM integration

✅ Dev Command Reference
✅ Backend

bash
Copy
source venv/bin/activate  
cd backend  
uvicorn main:app --reload
✅ Frontend

bash
Copy
cd frontend  
npm install  
npm run dev
✅ Database

bash
Copy
cd backend  
alembic upgrade head  # or python create_tables.py
🧠 Progress Snapshot (as of 2025-04-30)
✅ Image upload fixed (local + display)

✅ MetaMask wallet connected

✅ Role-based dashboard routing

✅ Product CRUD complete

✅ Deal system (status toggle + PDF)

✅ Admin dashboard live

✅ Public marketplace search

✅ Wallet-to-user binding

✅ Smart contract deployed on Polygon

✅ Escrow call from frontend (MetaMask)

✅ Landing page + role split (next)

📂 GitHub Repo
🔗 https://github.com/SuperFuels/COMDEX

COMDEX Updated Build Plan (STICKEY)
Branding and Naming:

Brand Name: "STICKEY"

Stable Coin: "$GLU"

Display "$GLU" prominently across the platform.

Frontend/UI Design Changes:
Landing Page (Main Entry Point):

STICKEY Branding: Replace existing branding with “STICKEY” and display "$GLU" prominently.

Currency Swap: Centralized currency swap for GBP to $GLU and other relevant currencies with real-time exchange rates visible.

Product Search: Dropdown to select products like Whey Protein, Cocoa, etc., with filters.

Scrolling Exchange Rates: Real-time ticker at the bottom showing prices in $GLU, USD, and local currencies.

Product Search Results Page:

Product List: Displays supplier name, product origin, price per KG, specifications, and ratings. Includes pagination and sorting options.

Product Detail Page:

Product Details: Supplier information, product specifications, certifications, quantity, and lead time.

Generate Quote: Button to initiate the contract process.

Shipping Options: Allows users to view shipping quotes and upload supplier shipping rates.

Buyer/Supplier Dashboards:
Buyer Dashboard:

Manage saved quotes, transaction history, wallet balance in $GLU, and contract statuses.

Supplier Dashboard:

Manage incoming quotes, contracts, shipping options, and quote adjustments.

Smart Contract & Blockchain Integration:
Escrow System: Funds locked until shipping confirmation by QR code scan.

Blockchain Contract: Recorded on the blockchain with NFTs as certificates of authenticity.

Shipping Integration:
Shipping Providers: Initially, suppliers will upload shipping quotes. Future shipping provider API integration for live quotes and tracking.

Wallet Integration:
MetaMask Wallet: Users can connect via WalletConnect to manage $GLU balances and initiate contract signing.

Dispute & Cancellation Handling:
Dispute Resolution: Use rules-based arbitration, with refunds only if the product hasn’t been shipped or is misrepresented.

Cancellation: Free to cancel before escrow is locked, with penalties after escrow is locked.

Testing and Deployment:
Manual Testing:

Focus on manual testing for contract creation, escrow, and shipping.

CI/CD Automation:

Set up for automated backend and frontend testing, including contract details, payments, and wallet transactions.

Next Steps in Development:
UI/UX Design Finalization: Refine design for product search, contract creation, and dashboards.

Smart Contract Development: Finalize contract creation and integrate escrow system.

Payment & Wallet Integration: Complete WalletConnect integration for payments and escrow.

Shipping API Integration: Develop shipping provider API integration for real-time quotes.

Full Testing & QA: Comprehensive testing for contract creation, escrow release, and shipping tracking.


🎯 MVP (Version 1) — Completed
Core B2B commodity marketplace with role‑based auth, product CRUD, manual deals, PDF exports, and basic swap UI.

Authentication & Onboarding

✅ JWT­-based register & login

✅ Role assignment (admin / supplier / buyer)

✅ Placeholder KYC on registration

Product Management

✅ Supplier “My Products” CRUD (incl. image upload)

✅ Public marketplace listing & search

Deal Management

✅ Buyer creates “deal” records

✅ Supplier views & updates deal status

✅ PDF generation & download of deal contract

Admin Panel

✅ Admin CRUD on users, products, deals

Tech Stack & Infra

✅ FastAPI + PostgreSQL + SQLAlchemy

✅ Next.js + Tailwind CSS + TypeScript

✅ Local image hosting & CORS setup

✅ MetaMask wallet connect & backend binding

✅ Smart contract escrow deployed on Polygon Amoy

Basic Swap UI

✅ SwapPanel component (dummy rate)

✅ Sticky header + swap bar layout

🚀 Phase 2 — Polish & Complete Core Flows
Registration & Dashboard Flows

 🔄 Flesh out /register/seller and /register/buyer pages

 🔄 Build Supplier Dashboard

My Products & New Product form

Deals tab (accept/reject)

 🔄 Build Buyer Dashboard

My Deals list & status

Swap → Deal Integration

 🔄 Wire SwapPanel “Swap” button to POST /deals/

 🔄 Show confirmation & update buyer’s “My Deals”

Product Detail & Quote Flow

 🔄 /product/[id] page: full info + “Buy” to open SwapPanel

Route Protection & UX

 🔄 Enforce role‑based guards on all pages

 🔄 Improve error / loading states, form validation

Responsive & Accessibility

 🔄 Mobile-first layout tuning (navbar, swap bar, grid)

 🔄 Keyboard navigation & aria labels

⚙️ Phase 3 — Expand Features & Integrations
On‑chain Swap Engine

 🛠 Integrate real swap logic (Web3 + your escrow contract)

 🛠 Show live rates (via oracle or off‑chain API)

Product Passport & Traceability

 📦 Extend products schema with batch_number, trace_id, certificate_url, blockchain_tx_hash

 📦 UI for viewing & uploading certificates + NFT explorer

Shipping & Logistics

 🚚 Supplier shipping rate uploads

 🚚 Integrate a shipping‑provider API for quotes & tracking

Stripe / FIAT‑Crypto Onramp

 💳 Add real payment integration (Stripe for fiat, WalletConnect for crypto)

🤖 Phase 4 — AI & Automation (V2/V3)
AI‑Powered Matching

 🤖 Build /match endpoint: rank suppliers by price, rating, location

 🤖 UI to recommend “best” suppliers

Autonomous Trade Agents

 🤖 Chat‑bot interface for negotiating deals

In‑Platform Messaging & Arbitration

 💬 Buyer ↔ Supplier chat

 ⚖️ Dispute resolution workflows

📈 Long‑Term Vision
COMDEX Chain: Launch your own EVM‑chain for escrow & NFT certificates

Governance Token (CDXT): DAO‑style governance & staking

Global Expansion: Add new commodity verticals (coffee, cocoa, olive oil…)

Mobile Apps: iOS/Android wrappers for on‑the‑go trading

Next Immediate Steps
Lock down Registration & Dashboard skeletons (so roles have proper home pages).

Wire SwapPanel → /deals/ and finish buyer “My Deals” flow.

Build product detail / “Get Quote” → SwapPanel integration.


