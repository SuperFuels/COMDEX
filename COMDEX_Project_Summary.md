# 🧾 COMDEX Project Summary (Updated — 2025-04-20)

## 🌍 Overview

COMDEX is a modern global commodity marketplace, starting with whey protein. Verified suppliers can list products, and buyers can transact using fiat (via Stripe) or crypto (future). COMDEX emphasizes transparency, traceability, and automation. Future versions will feature smart contracts, on-chain verification, and AI-driven matching.

---

## 🔹 Business Plan

### 🎯 Mission
Revolutionize global commodity trade with transparency, traceability, and efficiency.

### ❗ Problems Solved
- Manual, fragmented global commodity trade
- Trust issues in product quality or source
- Friction in global payments and deal closure
- Lack of a centralized, verified supplier network

### 🎯 Target Market
- V1: Whey protein (EU, USA, India, NZ)
- V2+: Cocoa, coffee, olive oil, pea protein, spices

### 💰 Revenue Model
- 2–3% transaction fee on deals
- Premium seller subscriptions (badges, insights)
- COA/lab test upload + verified seller filters
- Supply chain passport licensing
- FX & crypto SWAP transaction fees

---

## ✅ Version 1 — MVP (Complete)

### ✅ Core Features
- Supplier onboarding (KYC placeholder)
- JWT auth (register/login)
- Product listing (title, price, origin, image, description)
- Image upload (stored locally)
- Manual deal logging + status flow
- Deal PDF export via ReportLab
- Buyer, Supplier, and Admin Dashboards
- Admin panel (view users/products/deals)
- Route protection via `useAuthRedirect`
- Stripe checkout placeholder (for v2 crypto prep)
- PostgreSQL + FastAPI backend
- Next.js + Tailwind frontend

---

## ✅ Version 2 — In Progress

### ✅ Completed (as of 2025-04-20)
- Role-based authentication (buyer, supplier, admin)
- Role-based dashboard redirection
- Admin dashboard view for all users/products/deals
- Supplier dashboard for managing own products
- Product creation page protected for suppliers
- Token-based `GET /auth/role` endpoint added
- Navbar dynamically updates based on login
- Cleaner layout: sidebar removed, top navbar used
- Swap component placeholder (Uniswap-style)
- Dark theme removed, using light theme (gray/white)

---

## 🧱 Database Schema (2025-04-20)

### 📦 users
- `id`, `name`, `email`, `password_hash`
- `role`: "buyer", "supplier", "admin"
- `created_at`, `updated_at`

### 📦 products
- `id`, `owner_email`
- `title`, `description`, `price_per_kg`
- `origin_country`, `category`, `image_url`
- `created_at`

### 📦 deals
- `id`, `buyer_id`, `supplier_id`, `product_id`
- `quantity_kg`, `agreed_price`, `currency`
- `status`: negotiation → confirmed → completed
- `pdf_url`, `created_at`

---

## 🧪 Demo Logins & DB Access

| Role    | Email                  | Password  |
|---------|------------------------|-----------|
| Admin   | admin@example.com      | admin123  |

**Database**  
- Username: `comdex`  
- Password: `Wn8smx123`  
- DB Name: `comdex`  

---

## 📁 Project Structure

COMDEX/ ├── backend/ │ ├── main.py │ ├── create_tables.py │ ├── models/ │ │ ├── user.py │ │ ├── product.py │ │ └── deal.py │ ├── routes/ │ │ ├── auth.py │ │ ├── product.py │ │ ├── deal.py │ │ └── admin.py │ ├── schemas/ │ │ ├── user.py │ │ ├── product.py │ │ ├── deal.py │ │ └── admin.py │ ├── utils/ │ │ └── auth.py │ └── uploaded_images/ │ ├── frontend/ │ ├── components/ │ │ └── Navbar.tsx │ ├── hooks/ │ │ └── useAuthRedirect.ts │ ├── pages/ │ │ ├── index.tsx │ │ ├── login.tsx │ │ ├── register.tsx │ │ ├── dashboard.tsx │ │ ├── products/ │ │ │ ├── new.tsx │ │ │ └── edit/[id].tsx │ │ ├── supplier/ │ │ │ └── dashboard.tsx │ │ ├── admin/ │ │ │ └── dashboard.tsx │ │ └── deals/ │ │ └── index.tsx │ │ └── public/ │ └── placeholder.jpg

---

## 🛠 Deployment Commands

### 🔧 Backend
```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload
cd frontend
npm install
npm run dev
cd backend
python create_tables.py
🚀 Next Steps (Upcoming in V2)

Task	Status
Supplier-only Product Creation Guard	✅ Done
Supplier & Admin Dashboards	✅ Done
Role-based Routing	✅ Done
Token Role Validation	✅ Done
Buyer Deal Dashboard	⏳ In Progress
PDF Deal Preview	⏳ In Progress
Swap Interface (Polygon Placeholder)	⏳ Planned
AI Matching Engine (V3)	🔜
On-Chain Smart Contracts + NFT Proof	🔜
OpenSea-style Marketplace (COMDEX NFT)	🔜
Chain Fork (e.g., Polygon / Custom L1)	🔜
