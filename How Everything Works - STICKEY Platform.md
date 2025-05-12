kHow Everything Works — STICKEY Platform
Table of Contents
Overview

Architecture

Authentication & Roles

SIWE Login & Account Switching

Database Schemas

Users

Products

Deals

Contracts

Backend Endpoints

Frontend Structure

Completed Features

Search & Search Results

Quote & Deal Flow

AI Agent & Contract Engine

Roadmap & Next Steps

Dev Commands

1. Overview
COMDEX (front-end branded STICKEY, ticker $GLU) is a next-gen B2B commodity-trading platform combining:

AI: autonomous agents for supplier matching & contract drafting

Blockchain: on-chain escrow & NFT certificates

Crypto-native: wallet binding, swap panel, token flows

Mission: Revolutionize global commodity trade with trust, automation, transparency.

V1 Target: Whey Protein (EU, USA, India, NZ)

V2+: Cocoa, coffee, olive oil, pea protein, spices, and beyond.

2. Architecture
less
Copy
Edit
[ Next.js Frontend ] ↔ [ FastAPI Backend ] ↔ [ PostgreSQL ]
          ↑                  ↑
    [ MetaMask + $GLU ]   [ Migrations / Alembic ]
          ↑                  ↑
    [ Polygon Amoy Testnet Escrow Contract ]
             (Future: COMDEX Chain)
Frontend: Next.js + Tailwind CSS + TypeScript

Backend: FastAPI + SQLAlchemy + Pydantic + WeasyPrint (PDF)

DB: PostgreSQL

Blockchain: Polygon Amoy testnet escrow, future COMDEX Chain

AI: OpenAI LLM integrations under /agent and /contracts/generate

3. Authentication & Roles
Email/password + JWT via /auth/register & /auth/login

SIWE (Sign-In With Ethereum) wallet login & binding to user row

Roles: admin / supplier / buyer

Guards: front-end (React hook) & back-end (FastAPI dependency)

Dev stub v1: /auth/verify always returns "supplier" for rapid testing

Demo creds (email/password):

Admin: admin@example.com / admin123

Supplier: supplier@example.com / supplypass

Buyer: buyer@example.com / buyerpass

3.1 SIWE Login & Account Switching
To avoid “Invalid nonce” or “Signature mismatch” when you switch MetaMask accounts, always re-run the full SIWE handshake:

ts
Copy
Edit
// 1) fetch a fresh SIWE message
const [address] = await window.ethereum.request({ method: 'eth_requestAccounts' });
const { data: { nonce, message } } = await api.get('/auth/nonce', { params: { address } });

// 2) sign it in MetaMask
const signature = await window.ethereum.request({
  method: 'personal_sign',
  params: [message, address],
});

// 3) verify with backend
const { data: { token, role } } = await api.post('/auth/verify', { message, signature });
localStorage.setItem('token', token);
api.defaults.headers.common.Authorization = `Bearer ${token}`;
Automatically handle accountsChanged in Navbar.tsx:
ts
Copy
Edit
useEffect(() => {
  const eth = (window as any).ethereum;
  if (!eth) return;

  const handleAccountsChanged = (accounts: string[]) => {
    if (accounts[0]) {
      // re-run full handshake for new account
      doLogin(accounts[0]);
    } else {
      // MetaMask locked/disconnected
      handleDisconnect();
    }
  };

  eth.on('accountsChanged', handleAccountsChanged);
  return () => eth.removeListener('accountsChanged', handleAccountsChanged);
}, [doLogin, handleDisconnect]);
4. Database Schemas
4.1 Users
id (PK)

name

email (nullable for wallet-only)

password_hash (nullable for wallet-only)

role: admin / supplier / buyer

wallet_address (EIP-55, nullable)

created_at, updated_at

4.2 Products
id (PK)

owner_email → users.email

title, description

price_per_kg

origin_country, category

image_url

New: change_pct, rating, batch_number, trace_id, certificate_url, blockchain_tx_hash

created_at

4.3 Deals
id (PK)

buyer_id → users.id, supplier_id → users.id

product_id → products.id

quantity_kg, total_price

status: negotiation → confirmed → completed

created_at, pdf_url

4.4 Contracts
id (PK)

prompt (TEXT)

generated_contract (HTML/Markdown)

status

pdf_url

nft_metadata (stub)

5. Backend Endpoints
Section	Method	Path	Description	Auth
Auth	POST	/auth/register	Register user (email/password + role)	—
POST	/auth/login	Email/password login → JWT	—
GET	/auth/nonce	SIWE: issue nonce + EIP-4361 message	—
POST	/auth/verify	SIWE: verify signature → JWT + role	—
GET	/auth/role	Validate JWT → { role }	Bearer JWT
Products	GET	/products	List all products	Public
GET	/products/search	Search products	Public
GET	/products/{id}	Product details	Public
GET	/products/me	List supplier’s own products	Bearer supplier JWT
POST	/products	Create product	Bearer supplier JWT
PUT	/products/{id}	Update product	Bearer supplier JWT
DELETE	/products/{id}	Delete product	Bearer supplier JWT
Deals	GET	/deals	List deals for current user	Bearer JWT
POST	/deals	Create deal (calculates total_price)	Bearer JWT
GET	/deals/{id}	Single deal	Bearer JWT + guard
GET	/deals/{id}/pdf	Download deal PDF	Bearer JWT
PUT	/deals/{id}/status	Update deal status	Bearer admin/parties
POST	/deals/{id}/release	Release funds on-chain	Bearer buyer/supplier
Contracts	POST	/contracts/generate	Draft via LLM	Bearer JWT
GET	/contracts/{id}	Contract details	Bearer JWT
GET	/contracts/{id}/pdf	Download contract PDF	Bearer JWT
POST	/contracts/{id}/mint	Mint NFT (future)	Bearer JWT
Admin	CRUD	/admin/*	Full CRUD on all resources	Bearer admin JWT
Users	PATCH	/users/me/wallet	Bind MetaMask wallet to user	Bearer JWT

6. Frontend Structure
6.1 Pages
/ → Home / Marketplace

/search → Search results

/products/[id] → Product detail

/products/[id]/sample → Sample request

/products/[id]/zoom → Zoom request

/products/create → Create product

/buyer/dashboard → Buyer Dashboard

/dashboard → Supplier Dashboard

/admin/dashboard → Admin panel

/login → Email/password login

/register/supplier → Supplier signup

/register/buyer → Buyer signup

6.2 Components
Navbar: logo, search, auth links, wallet connect, SIWE & account-switch handling

SwapBar: inline amount/token swap UI

Chart: Recharts line-chart

ProductCard: image, price, change%, rating, details link

QuoteModal: quantity input → create deal

Sidebar: filters & selected commodity

DashboardTabs: tabs for deals/contracts

7. Completed Features
🌐 Public marketplace with listings & filters

🖼️ Image upload & display

🔐 Email/password JWT auth & role-guards

🦊 MetaMask wallet connect & full SIWE handshake with account switching

📝 Product CRUD (supplier)

📋 Deal creation & status workflow

📄 PDF generation (WeasyPrint)

⚖️ Admin panel full CRUD

🔄 Sticky SwapPanel (stub)

🚀 On-chain escrow integration (Polygon Amoy testnet)

📊 Live charts (stub)

📑 Sample & Zoom request UIs

8. Search & Search Results
/search shows table with:
Image | Title | Origin | Price/kg | Supplier | Change % | Rating | Details

9. Quote & Deal Flow
On /products/[id], “Lock in GLU Quote” opens QuoteModal

Buyer enters quantity → POST /deals → redirect to /buyer/dashboard

10. AI Agent & Contract Engine
AgentBar stub on /contracts → POST /contracts/generate → save draft

Review & PDF download

11. Roadmap & Next Steps
Phase 2: Core Flows & Polish

Harden real-world SIWE (remove dev stub)

Add full registration UIs

Enhanced search filters (rating, tags, regions)

SwapPanel → real on-chain swaps & deals

Multi-image uploads & NFT certificate viewer

Phase 3+: On-chain & Integrations, AI agents, Governance, COMDEX Chain, mobile, global expansion.

12. Dev Commands
Backend
bash
Copy
Edit
cd ~/Desktop/Comdex/backend
source .venv/bin/activate
uvicorn main:app --reload

# DB migrations
alembic revision --autogenerate -m "add new fields"
alembic upgrade head

# Kill & restart if port stuck
lsof -n -iTCP:8000 | awk 'NR>1 {print $2}' | xargs --no-run-if-empty kill -9
uvicorn main:app --reload
Upsert your supplier user (so SIWE verify can find them):
bash
Copy
Edit
psql postgresql://comdex:Wn8smx123@localhost:5432/comdex
sql
Copy
Edit
INSERT INTO users (name, email, wallet_address, role)
VALUES (
  'My Supplier',
  'supplier@example.com',
  LOWER('0x70997970c51812dc3a010c7d01b50e0d17dc79c8'),
  'supplier'
)
ON CONFLICT (email) DO UPDATE
  SET wallet_address = EXCLUDED.wallet_address,
      role           = EXCLUDED.role;

SELECT id, email, role, wallet_address
  FROM users
 WHERE email = 'supplier@example.com';

\q
Frontend
bash
Copy
Edit
cd ~/Desktop/Comdex/frontend
npm install      # or yarn
npm run dev      # or yarn dev
Env (.env.local):

ini
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
nano routes/auth.py
nano components/Navbar.tsx
nano pages/buyer/dashboard.tsx
nano lib/api.ts







