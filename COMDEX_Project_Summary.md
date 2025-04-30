🧾 COMDEX Project Summary (Updated — 2025-04-30)

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
JWT Stored in LocalStorage

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
COMDEX Stablecoin
For escrow payments
Fiat-pegged

FX Swap Engine
Convert USD/EUR/ETH/BTC to CMDX

CDXT Investor Token ("Shitcoin")
Utility + governance + speculation

CVAL Store-of-Value Coin
Deflationary reserve

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
1. Branding and Naming:
Brand Name: "STICKEY"

Stable Coin: "$GLU"

Display "$GLU" prominently across the platform.

2. Frontend/UI Design Changes:
Landing Page (Main Entry Point):

STICKEY Branding: Replace the existing logo and branding with "STICKEY" and "$GLU".

Currency Swap:

Centralize the swap feature for currency conversion.

Users can swap from GBP to $GLU and other relevant currencies.

Display the exchange rate and update it in real-time.

Search Bar:

Prominently visible for searching commodities.

Initially, a dropdown for available products like Whey Protein, Cocoa, etc.

As the platform grows, this will evolve into a broader search system with categories and filters.

Scrolling Exchange Rates:

Add a scrolling bar at the bottom showing real-time prices of commodities in $GLU, USD, and local currencies.

Allow users to track changes in commodity prices, helping in making purchasing decisions.

UI Design:

Clean, modern design using blue tones consistent with the STICKEY branding.

Intuitive UI, with clearly defined buttons, product tiles, and call-to-action sections.

Product Search Results Page:

Product List:

Display results such as "Whey Protein", "Cocoa", etc., with key information:

Supplier Name

Product Origin

Cost per KG (in $GLU and USD)

Product Specifications

Ratings/Stars

Include the ability to filter and sort by supplier, price, ratings, etc.

Pagination for long product lists (e.g., "1 > 2 > 3 > 4 > 5").

Product Buttons:

Display buttons for each product at the bottom, showcasing price and allowing users to view more details or add the product to their quote.

Product Page:

Product Details:

Supplier information, product specifications, and certifications.

Show the product’s available quantity, lead time, and export details (origin country, packaging).

Add a section for "Contract Terms", where buyers can review product terms, pricing, and MOQ.

Include images and videos of the product.

Media:

Support for videos and images showing the product, production process, or product usage (like an Amazon product page).

Generate Quote:

A "Generate Quote" button that creates a draft contract and triggers the contract creation process.

Shipping Options:

Allow users to view shipping quotes from various providers like DHL, UPS, etc. Include cost estimations for each shipping method.

Buyer and Supplier Dashboards:

Buyer Dashboard:

Notifications for accepted quotes, new offers, and quote expiration timers (e.g., “Offer expires in 1 day”).

Saved Quotes: Display a list of saved quotes with options to refresh prices, accept or decline offers.

Transaction History: Show a record of past transactions, including details on pricing and shipping.

Actionable Buttons: Include actionable buttons for each quote (Accept, Decline, Refresh Price).

Wallet: Display the user’s wallet balance in $GLU and allow for payments through WalletConnect.

Supplier Dashboard:

Notifications: Alert suppliers when a quote has been accepted or when a buyer has requested a quote.

Transaction Management: Allow suppliers to manage their incoming and outgoing quotes, and provide a view of the associated contracts.

Contract Management: Suppliers can accept, decline, or adjust contract terms, and share them via email or download as PDF.

Saved Quotes: Suppliers can manage saved quotes, and view transaction history and active buyers.

Shipping and Logistics: Include options for suppliers to manage preferred shipping providers and rates.

3. Contract Creation Process:
Draft Contract:

Buyer-Supplier Contract Creation: When a buyer generates a quote, the system creates a draft contract that includes:

Product details (quantity, price, specifications).

Supplier and buyer details.

Payment terms, including the escrow amount.

Shipping details, including options to select and pay for shipping providers.

Timeline and expected delivery.

Blockchain contract address and status.

Contract Clauses:

Both buyer and supplier should be able to view and adjust standard contract clauses.

Include an option for “Additional Clauses” if either party requires special terms.

Contracts will be logged onto the blockchain once accepted.

Escrow System:

Escrow: Payment will be locked in escrow until the shipping provider confirms collection.

QR Code for Collection: Once the shipment is collected, the shipping provider scans the QR code to release escrow funds.

Blockchain Contract:

Each contract should be recorded on the blockchain, accessible for both parties.

An NFT will be generated for each contract as a certificate of authenticity.

4. User Interaction and Smart Contracts:
Notifications:

Alert users about contract status, price changes, expiring offers, and updates in real-time.

Notifications should be visible in both the buyer and supplier dashboards.

Quote/Contract Timeline:

The contract's price should update over time based on market rates, and users should be notified of these updates.

The system should ensure that both parties are aware of the changing prices until the contract is locked in.

5. Wallet Integration and Payments:
WalletConnect Integration:

Allow users to connect their wallets using WalletConnect (MetaMask, etc.) to manage $GLU balances and transactions.

Allow for easy deposit and withdrawal of $GLU.

Escrow Payment:

Ensure escrow payments are processed correctly and can be tracked within the user’s wallet.

6. Shipping Integration:
Shipping Providers:

Support for quoting from multiple shipping providers like DHL, UPS, and Parcel Force.

Display shipping costs, estimated delivery time, and the ability for buyers and suppliers to select the preferred provider.

Shipping confirmation and QR code generation for the collection process.

7. Product Page for Advanced Details:
Advanced Product Details:

Include more detailed specifications, certifications, and any additional required documents (e.g., business documentation).

Option for buyers to initiate the contract process from the product page (click to generate quote).

Add media (images and videos) showcasing the product in use, as well as factory or supplier facilities.

8. Mobile & Responsiveness:
Mobile-First Design:

Ensure all pages, including dashboards, contract pages, and product pages, are fully responsive and optimized for mobile devices.

Fluid Design:

Use flexible grids, responsive elements, and scalable images to ensure a smooth user experience on all devices.

9. Backend/Database Updates:
Contract Data:

Store all contract details, including terms, supplier and buyer details, payment status, and blockchain contract IDs.

Transaction History:

Log all quote requests, contract creation, and transactions for both buyers and suppliers.

Escrow Tracking:

Track escrow status and payments, ensuring correct data is stored for each contract.

10. Security & Compliance:
User Authentication:

Ensure that buyer and supplier logins are secure using JWT tokens and role-based access controls.

Smart Contract Security:

Ensure the smart contract code is secure, protecting users’ funds in escrow and preventing vulnerabilities.

Data Privacy:

Comply with relevant data privacy laws, ensuring that all personal and transactional data is stored securely.

Features and Functionality Summary:
Landing Page: Currency swap, product search, exchange rates.

Product Search Page: Display search results with sortable filters.

Product Detail Page: Specifications, media, contract generation, shipping quotes.

Buyer Dashboard: Quote management, notifications, transaction history.

Supplier Dashboard: Quote management, notifications, contract approvals.

Smart Contract Integration: Blockchain-backed contracts with NFT generation.

Escrow System: Payment release after shipping confirmation via QR code.

Wallet Integration: Using WalletConnect for transaction management.

Shipping Provider Integration: Multiple options for shipping and delivery.

Mobile Compatibility: Ensure all features are mobile-optimized.

Next Steps in Development:
UI/UX Design Finalization: Improve the interface for product search, contract creation, and dashboard management based on the new design.

Smart Contract Development: Finalize the contract creation and escrow system with integration to the blockchain.

Backend Integration: Connect all user and product data to the blockchain for secure contract storage and tracking.

Payment & Escrow Processing: Implement WalletConnect for handling payments and escrow funds.

Shipping Integration: Develop shipping provider API integrations for quotes and parcel tracking.

Testing & QA: Thoroughly test all components, from contract creation to payment and shipping tracking.



