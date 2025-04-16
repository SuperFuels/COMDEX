
# COMDEX Project Summary (Updated - 2025-04-16)

## 1. Overview
**COMDEX** is a modern global commodity marketplace, starting with whey protein. It enables verified suppliers to list products, and buyers to transact using fiat or crypto. The platform includes product traceability, escrow logic (future), and AI-based matching and pricing (v2).

## 2. Business Plan
### Mission:
To revolutionize global commodity trading by offering a transparent, traceable, and frictionless digital platform for buyers and sellers.

### Core Problems Solved:
- Fragmented, offline commodity trade
- Lack of transparency and trust in product origin
- Cross-border payment and contract friction
- No central, trusted discovery hub for verified commodities

### Target Market:
- Initial: Whey protein producers and bulk buyers in the EU, USA, India, NZ
- Expansion: Commodities like cocoa, coffee, pea protein, oils, spices

### Revenue Model:
- 2–3% commission on successful trades
- Premium seller subscriptions (badging, analytics)
- Add-ons (lab verification, COA upload, carbon offsetting)
- Future: White-labeling traceability passport tech

## 3. MVP v1 Features (Confirmed)
1. **Buyer and Supplier Dashboards**
2. **Supplier Onboarding and KYC Upload**
3. **Product Listings** (origin, title, price, COA)
4. **Contact Seller** (messaging or email initiation)
5. **Manual Deal Record Logging**
6. **Status Flow:** Negotiation → Confirmed → Completed
7. **Stripe Fiat Checkout Integration**
8. **Crypto Wallet Field** (stored, not active)
9. **PDF Export of Deal Records**

## 4. COMDEX v2 Features (Roadmap)
1. **AI-Based Supplier Matching Engine**
2. **Dynamic Pricing Intelligence**
3. **Smart Contract Escrow System** (on Polygon)
4. **Blockchain-Based Traceability Passport**
5. **Commodity Pricing Charts with TradingView-Style UI**
6. **Mobile-First App Version**

## 5. Pitch Deck Summary
1. **Title Slide + Logo**
2. **The Problem**
3. **The Solution**
4. **Product Flow** (MVP walkthrough)
5. **Why Now**
6. **Unique Selling Points**
7. **Market Opportunity** ($5.2T+ commodity market)
8. **Business Model**
9. **Go-To-Market Plan**
10. **Roadmap & Traction**
11. **Team**
12. **Fundraising Ask** ($500k seed)
13. **Closing Vision**

## 6. Wireframes Overview (Desktop-First)
Key Wireframe Pages:
1. **Homepage:** Search bar, browse button, create listing CTA
2. **Listing Page:** Product cards with price chart, origin, certification, % price change
3. **Product Detail Page:** Full details, COA link, contact supplier button
4. **Deal Record Page:** Buyer/seller info, agreed volume, price, status, download PDF
5. **Dashboard:** User’s active listings or deal history, crypto wallet field

**Design Style:** TradingView-inspired, focusing on clarity and professional usability.

## 7. Tech Stack
- **Frontend:** Next.js (React), TailwindCSS
- **Backend:** FastAPI or Django REST
- **Database:** PostgreSQL (Supabase or AWS RDS)
- **File Storage:** Supabase / AWS S3
- **Fiat Payments:** Stripe
- **Crypto (Future):** Polygon + MetaMask
- **PDF Export:** ReportLab or wkhtmltopdf
- **Deployment:** Vercel (Frontend), Render or AWS (Backend)

## 8. MVP v1 Database Schema
1. **Users Table**
   - id (PK)
   - name
   - email
   - password_hash
   - role (buyer, seller, admin)
   - kyc_status (pending, verified, rejected)
   - created_at
   - updated_at

2. **Products Table**
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

3. **Deals Table**
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

4. **Files Table**
   - id (PK)
   - user_id (FK → Users)
   - file_type (COA, KYC, Invoice)
   - filename
   - storage_path
   - uploaded_at

5. **Wallets Table**
   - id (PK)
   - user_id (FK → Users)
   - crypto_address
   - preferred_chain (Polygon, Ethereum)
   - created_at

## 9. Phased Build Plan
### Phase 0: Planning & Architecture (Week 0–2)
- Finalize wireframes + database schema
- Set up GitHub + environments
- Define backend API endpoints and frontend routes

### Phase 1: Core Platform Build (Week 3–4)
- Supplier + Buyer registration and KYC upload
- Product listing creation + dashboard views
- Product listing grid and detail pages

### Phase 2: Deal Management & Payment Flow (Week 5–6)
- Deal logging form + status tracker
- Stripe integration for payment simulation
- PDF generation of completed deals

### Phase 3: QA, Deployment, and Onboarding (Week 7)
- Admin panel for KYC review + deal verification
- Testing (frontend/backend + PDF rendering)
- Deploy frontend (Vercel) and backend (Render/EC2)
- Invite 3–5 pilot suppliers and buyers

## 10. Next Steps
### Set Up GitHub Repository:
- Initialize main repo (comdex-platform)
- Push current schema + wireframes
- Add README with project structure + roadmap

### Backend Setup:
- Set up FastAPI project
- Connect to PostgreSQL DB
- Define core API endpoints: POST /register, GET /listings, POST /deal
- Add JWT authentication

### Frontend Scaffold:
- Scaffold Next.js + TailwindCSS project
- Build UI for homepage, product listing, product detail, and dashboard

### Stripe Integration:
- Integrate test Stripe keys for fiat payments
- Setup test transactions

### PDF Export:
- Add basic PDF export for deal record

### Begin Testing + Admin Tools:
- Manual testing of user flows
- Build simple admin UI for KYC and listing verification

## 11. GitHub Repository Link
**SuperFuels/COMDEX**

## COMDEX Project Summary (Updated - 2025-04-16)

### Progress Updates:
- Switched from Alembic to manual SQLAlchemy table creation.
- Created tables for users and deals using SQLAlchemy (via create_tables.py).
- Resolved import errors and corrected path issues within models.py and `__init__.py`.
- Tables (users and deals) successfully created in the PostgreSQL database.
- The admin panel is now showing at [http://localhost:3000/admin/dashboard].

### Next Steps for Tomorrow:
- Fully test table creation and database connection.
- Test admin panel functionality and its integration with the database.
- Continue with the integration of other features such as product listings, deal creation, and dashboard functionalities.

## File Structure Summary:

```plaintext
/COMDEX
  ├── backend
  │    ├── app
  │    ├── models
  │    ├── routes
  │    ├── utils
  │    ├── create_tables.py
  │    ├── main.py
  │    ├── database.py
  │    └── requirements.txt
  ├── frontend
  │    ├── pages
  │    ├── components
  │    ├── public
  │    ├── styles
  │    ├── tailwind.config.js
  │    ├── next.config.js
  │    └── package.json
  ├── .gitignore
  ├── README.md
  ├── docker-compose.yml
  └── migrations (optional)
```

### Commands Summary:
#### Backend Setup:
```bash
# Activate the virtual environment
source venv/bin/activate

# Navigate to backend
cd backend

# Run the backend server
uvicorn main:app --reload
```

#### Frontend Setup:
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run the frontend server
npm run dev
```

#### Database Setup:
```bash
# Create tables
python create_tables.py
```
