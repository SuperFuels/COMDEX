
# COMDEX Project Summary

## 1. **Overview**
COMDEX is a modern global commodity marketplace, starting with whey protein. It enables verified suppliers to list products, and buyers to transact using fiat or crypto. The platform includes product traceability, escrow logic (future), and AI-based matching and pricing (v2).

## 2. **Business Plan**

### **Mission**:
To revolutionize global commodity trading by offering a transparent, traceable, and frictionless digital platform for buyers and sellers.

### **Core Problems Solved**:
- Fragmented, offline commodity trade
- Lack of transparency and trust in product origin
- Cross-border payment and contract friction
- No central, trusted discovery hub for verified commodities

### **Target Market**:
- **Initial**: Whey protein producers and bulk buyers in the EU, USA, India, NZ
- **Expansion**: Commodities like cocoa, coffee, pea protein, oils, spices

### **Revenue Model**:
- 2–3% commission on successful trades
- Premium seller subscriptions (badging, analytics)
- Add-ons (lab verification, COA upload, carbon offsetting)
- **Future**: White-labeling traceability passport tech

## 3. **MVP v1 Features (Confirmed)**

- Buyer and supplier dashboards
- Supplier onboarding and KYC upload
- Product listings (origin, title, price, COA)
- Contact seller (messaging or email initiation)
- Manual deal record logging
- Status flow: Negotiation → Confirmed → Completed
- Stripe fiat checkout integration
- Crypto wallet field (stored, not active)
- PDF export of deal records

## 4. **COMDEX v2 Features (Roadmap)**

- AI-based supplier matching engine
- Dynamic pricing intelligence
- Smart contract escrow system (on Polygon)
- Blockchain-based traceability passport
- Commodity pricing charts with TradingView-style UI
- Mobile-first app version

## 5. **Pitch Deck Summary**

### **Slide Structure**:
- Title Slide + Logo
- The Problem
- The Solution
- Product Flow (MVP walkthrough)
- Why Now
- Unique Selling Points
- Market Opportunity ($5.2T+ commodity market)
- Business Model
- Go-To-Market Plan
- Roadmap & Traction
- Team
- Fundraising Ask ($500k seed)
- Closing Vision

## 6. **Wireframes Overview (Desktop-First)**

### **Key Wireframe Pages**:
- **Homepage**: Search bar, browse button, create listing CTA
- **Listing Page**: Product cards with price chart, origin, certification, % price change
- **Product Detail Page**: Full details, COA link, contact supplier button
- **Deal Record Page**: Buyer/seller info, agreed volume, price, status, download PDF
- **Dashboard**: User’s active listings or deal history, crypto wallet field

**Design Style**: TradingView-inspired, focusing on clarity and professional usability.

## 7. **Tech Stack**

- **Frontend**: Next.js (React), TailwindCSS
- **Backend**: FastAPI or Django REST
- **Database**: PostgreSQL (Supabase or AWS RDS)
- **File Storage**: Supabase / AWS S3
- **Fiat Payments**: Stripe
- **Crypto** (future): Polygon + MetaMask
- **PDF Export**: ReportLab or wkhtmltopdf
- **Deployment**: Vercel (Frontend), Render or AWS (Backend)

---

## 8. **MVP v1 Database Schema**

### **1. Users Table**
- id (PK)
- name
- email
- password_hash
- role (buyer, seller, admin)
- kyc_status (pending, verified, rejected)
- created_at
- updated_at

### **2. Products Table**
- id (PK)
- seller_id (FK → Users)
- title
- description
- price_per_kg
- origin_country
- certifications
- coa_file_id (FK → Files)
- status (active, archived)
- created_at

### **3. Deals Table**
- id (PK)
- buyer_id (FK → Users)
- seller_id (FK → Users)
- product_id (FK → Products)
- quantity_kg
- agreed_price
- currency (USD, EUR, etc.)
- status (negotiation, confirmed, paid, completed)
- pdf_export_url
- stripe_payment_id (nullable)
- created_at

### **4. Files Table**
- id (PK)
- user_id (FK → Users)
- file_type (COA, KYC, Invoice)
- filename
- storage_path
- uploaded_at

### **5. Wallets Table**
- id (PK)
- user_id (FK → Users)
- crypto_address
- preferred_chain (Polygon, Ethereum)
- created_at

## 9. **Phased Build Plan**

### **Phase 0: Planning & Architecture (Week 0–2)**
- Finalize wireframes + database schema
- Set up GitHub + environments
- Define backend API endpoints and frontend routes

### **Phase 1: Core Platform Build (Week 3–4)**
- Supplier + Buyer registration and KYC upload
- Product listing creation + dashboard views
- Product listing grid and detail pages

### **Phase 2: Deal Management & Payment Flow (Week 5–6)**
- Deal logging form + status tracker
- Stripe integration for payment simulation
- PDF generation of completed deals

### **Phase 3: QA, Deployment, and Onboarding (Week 7)**
- Admin panel for KYC review + deal verification
- Testing (frontend/backend + PDF rendering)
- Deploy frontend (Vercel) and backend (Render/EC2)
- Invite 3–5 pilot suppliers and buyers

---

## 10. **Next Steps**

1. Set Up GitHub Repository:
   - Initialize main repo (comdex-platform)
   - Push current schema + wireframes
   - Add README with project structure + roadmap
2. Backend Setup:
   - Set up FastAPI project
   - Connect to PostgreSQL DB
   - Define core API endpoints: POST /register, GET /listings, POST /deal
   - Add JWT authentication
3. Frontend Scaffold:
   - Scaffold Next.js + TailwindCSS project
   - Build UI for homepage, product listing, product detail, and dashboard
4. Stripe Integration:
   - Integrate test Stripe keys for fiat payments
   - Setup test transactions
5. PDF Export:
   - Add basic PDF export for deal record
6. Begin Testing + Admin Tools:
   - Manual testing of user flows
   - Build simple admin UI for KYC and listing verification

---

## 11. **GitHub Repository Link**
[SuperFuels/COMDEX](https://github.com/SuperFuels/COMDEX)

## COMDEX Project Summary (Updated - 2025-04-16)

### Progress Updates:
- Switched from Alembic to manual SQLAlchemy table creation.
- Created tables for `users` and `deals` using SQLAlchemy (via `create_tables.py`).
- Resolved import errors and corrected path issues within `models.py` and `__init__.py`.
- Tables (`users` and `deals`) successfully created in the SQLite database.
- The admin panel is now showing at [http://localhost:3000/admin/dashboard].

### Next Steps for Tomorrow:
- Fully test table creation and database connection.
- Test admin panel functionality and its integration with the database.
- Continue with the integration of other features such as product listings, deal creation, and dashboard functionalities.

