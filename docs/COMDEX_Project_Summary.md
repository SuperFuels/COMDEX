Stickey Ai Project Summary (Updated — 2025-04-30)
🌍 Overview
Stickey Ai is a next-gen global commodity trading platform built for trust, automation, and transparency — combining AI, blockchain, and crypto-native features to reshape how global B2B trade happens.

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


------

NEXT LEVEL

1. Recap: What COMDEX Already Does Today
	1.	On-chain identity + wallet login (SIWE).
	•	Users connect with Ethereum (“Connect Wallet”) or email/password.
	•	We store a JWT and return a server‐side role (supplier/buyer/admin).
	•	The code already routes suppliers to /supplier/dashboard, buyers to /buyer/dashboard, etc.
	2.	OTC Spot Listings & Escrow.
	•	A “supplier” can create a physical product listing (e.g. 1 tonne of coffee, grade X, origin Y, delivery terms).
	•	A “buyer” can browse live market prices, filter, click into a product, and “take the deal.”
	•	When a buyer clicks “Purchase,” we spin up a smart contract escrow where the buyer deposits stablecoins (e.g. USDT) on-chain and the seller deposits (or locks) a proof of inventory or a warehouse receipt.
	•	On successful delivery (off-chain inspection, off-chain logistics), the escrow smart contract releases payment to the supplier and updates both parties’ on-chain reputations/ratings.
	3.	AI-Driven Analytics & Price Charts.
	•	We generate a 24-hour price history (e.g., simulated or via our own price feed).
	•	On supplier dashboards, we show “Sales Today,” “30 day proceeds,” “open orders,” and a placeholder for AI analysis (e.g., “Your 30 day proceeds are up 5% over last month,” “Your feedback rating remains stable at 4.7/5,” etc.).
	4.	Simplified “Swap” Component.
	•	In the Navbar, we have a small “Swap” bar that lets users swap USDT → $GLU via a DEX or an on-chain pair.
	•	This is a convenience for suppliers/buyers who need $GLU to pay on platform fees or vice versa.

At its core today, COMDEX is an on-chain-backed, crypto–native OTC spot marketplace for physical commodities, augmented with basic charts and AI placeholders.

⸻

2. How “Spot vs. Derivatives” Map onto COMDEX

2.1. Spot (Cash) Functionality
	•	What It Means for COMDEX:
	•	Buyers pay right away (either in stablecoin or $GLU), and the supplier ships physical product within the agreed window (e.g., 7 days).
	•	We track delivery status, warehouse receipts, and once “proof of delivery” is satisfied, the escrow releases payment.
	•	This is exactly what we already built: a “spot” marketplace where $USDT (or another on-chain asset) is held in escrow, product is physically moved off-chain, and then money is released.
	•	Key Pieces in Code Today:
	1.	Listings Endpoints:
	•	POST /api/products → Create a new spot listing.
	•	GET /api/products → List all available products (title, price, origin, etc.).
	•	GET /api/products/:id → Fetch one listing’s details (stock, grade, location, seller).
	2.	Deals/Contracts Endpoints:
	•	POST /api/deals → Buyer initiates a “take” on a listing.
	•	Smart contract is spun up on-chain (solidity) to hold buyer’s payment; supplier is notified.
	•	Off-chain (our backend) tracks “shipping in progress.”
	•	Once supplier mints a “ProofOfShipment” NFT or “ProofOfWarehouseReceipt,” the on-chain escrow transitions to “DELIVERED” stage.
	3.	Escrow Smart Contract (solidity):
	•	depositBuyerFunds() locks buyer payment.
	•	depositSupplierCollateral() — either tokenized warehouse receipt or link to an off-chain certificate stored in IPFS.
	•	releaseFundsToSupplier() when both sides have provided proof.
	•	refundBuyer() if the supplier fails to ship within X days.

All of this is “physical goods” → “payment now, delivery soon.” In commodity jargon, that’s “spot” or “cash” trading.

⸻

2.2. Derivatives (Futures) Functionality
	•	Definition (Again):
A futures contract is a standardized, exchange‐traded agreement to buy/sell a set quantity at a set future date. But COMDEX is a decentralized/OTC platform, so we have to replicate some of that “futures” logic ourselves. Specifically:
	1.	A buyer locks in today’s price for delivery on a known future date (e.g., 1 month from now).
	2.	A seller locks in today’s price to deliver at that future date.
	3.	Neither side necessarily wants (or can store) physical product today. Instead, they post margin on-chain, and daily (or periodic) P/L is settled (mark-to-market), just like a traditional futures contract.
	•	Key Characteristics We Must Implement:
	1.	Standardized Contract Terms & Expirations:
	•	Choose a small set of “delivery windows” (e.g., monthly).
	•	Decide on standard “lot sizes.” If ICE coffee is 37,500 lb, we could create our own “COMDEX Coffee” contract for, say, 1 ton or 5 tons—make it a round number.
	•	Each contract must reference exactly:
	•	Underlying commodity (e.g., “Coffee Arabica Grade 1”).
	•	Quantity (e.g., 1 ton).
	•	Delivery month (e.g., “June 2025”).
	•	Delivery location or method (a standard warehouse in origin).
	2.	On-chain Margin & Mark-to-Market:
	•	Each user posts a stablecoin margin—say 10 % of the notional. So if a 1 ton contract is priced at £1200/t, the notional is £1,200. If margin requirement is 10 %, user posts £120 in USDT (token).
	•	We need an on-chain “Clearinghouse” contract that:
	•	Holds margin collateral from both long and short.
	•	Maintains a real-time “mark-to-market” price feed for that commodity (using a Chainlink oracles or our own TWAP feed).
	•	Every “settlement interval” (daily? hourly?), it recomputes each open position’s P/L (e.g., if price moves up 2 %, longs gain 2 % of notional, shorts lose 2 % of notional). Funds are redistributed from losers to winners.
	•	If a margin call is triggered (margin ratio falls below maintenance margin), the contract automatically liquidates positions (on-chain auction or AMM) to protect the pool.
	3.	Delivery vs. Cash Settlement Options:
	•	Some future holders might actually want real beans in a warehouse in July.
	•	Others will cash-settle (they never take delivery).
	•	We can build two flavors of each COMDEX future contract:
	1.	Physically Settled: At expiration, one side must mint a “warehouse receipt NFT” and the other side redeems it for actual beans (off-chain process).
	2.	Cash Settled (CFD Style): At expiration, the difference between final futures price and entry price is paid out in USDT; no physical cargo changes hands.
	4.	Order Book vs. AMM vs. Peer-to-Peer:
	•	Traditional exchanges have a central limit order book (CLOB). On-chain CLOB is possible but expensive (gas, latency).
	•	We could start with a peer-to-peer posting system:
	•	“I want to sell 1 ton June Coffee futures at £1200/t (margin locked).”
	•	“I want to buy 1 ton June Coffee futures at £1198/t (margin locked).”
	•	When they match, our backend aggregates them and opens a single on-chain position.
	•	Eventually we could layer an on-chain AMM (constant product style) for “futures pairs” or use a permissioned off-chain order book + on-chain settlement.

⸻

3. Step-By-Step: Adding Futures‐Style on Top of COMDEX

Below is a suggested multi-phase plan. Each phase builds on the last—so you don’t have to rip out or rewrite your entire spot logic.

Phase 1: Design & Launch “COMDEX Spot” (Already largely done)
	1.	Finalize Spot Listing Contract & Workflows.
	•	Decide which commodities you’ll support initially (e.g., Coffee, Wheat, Corn).
	•	Standardize product attributes:
	•	Commodity Type (enum: coffee, wheat, corn, etc.)
	•	Grade/Quality (Grade 1, Grade 2, etc.)
	•	Origin, Delivery window (e.g., “deliver within 7 days of purchase”)
	•	Ensure your existing /products schema can hold these fields.
	•	Confirm the escrow flow: Buyer pays → Seller confirms shipment → Inspection → Escrow pays seller.
	2.	Integrate Real-World Price Feeds (Optional but desirable).
	•	For the spot side, you may want a “mid-market price” reference (e.g., ICE Coffee C front-month).
	•	Use Chainlink or a WebSocket feed to update a “live price” on your front end, so buyers can see how competitive your OTC price is vs. ICE.
	•	We already have a simple 24h chart in /components/Chart; just swap in real oracle data instead of random.
	3.	Refine UX & AI Analytics.
	•	In /supplier/dashboard, replace the “Chart placeholder” with a small line chart that uses your spot feed.
	•	Under “AI Analysis placeholder,” feed in a short GPT/Azure function or an on-chain aggregator that says, “Sales today are up X% vs. yesterday,” “Inventory turns in last 7 days,” etc.

At the end of Phase 1, you truly have a crypto-native OTC spot marketplace: on-chain escrows, seller/buyer reputations, and live price benchmark charts.

Phase 2: Introduce “Forward” Contracts (OTC Futures) with Manual Settlement

Before building a full “exchange” with daily margin, you can start by allowing two parties to privately negotiate a “forward/derivative” trade in your UI:
	1.	New Database Models & Endpoints
	•	POST /api/forwards 

    {
  "commodity": "coffee",
  "quantity": 1,                 // in tonnes
  "grade": "Arabica Grade 1",
  "deliveryDate": "2025-08-15",  // future date
  "pricePerTonne": 1250,         // locked in now
  "buyerWallet": "0x123…",
  "sellerWallet": "0x456…",
  "marginPercent": 0.10          // e.g. 10% posted each
}

•	When a forward is created, the buyer and seller both have to confirm and each post their margin:
	•	Buyer POST /api/forwards/:id/deposit-buyer-margin → sends e.g. 10% of notional in USDT to our on-chain ForwardEscrow contract.
	•	Seller POST /api/forwards/:id/deposit-seller-collateral → either posts USDT (10% as margin) or an NFT representing a pre-existing warehouse receipt.

	2.	On-chain ForwardEscrow (Single Shared Contract)
	•	Deploy a ForwardEscrow.sol that can:
	1.	Accept collateral from buyer and seller (two separate calls).
	2.	Lock those funds until the agreed deliveryDate.
	3.	On deliveryDate, read a price feed (e.g., Chainlink “spot price in USD per tonne”).
	•	If the underlying spot price has moved, seller or buyer gets the P/L difference in USDT.
	•	E.g. Forward price = £1250, spot on settlement = £1300, buyer owes extra £50 × 1 ton = £50.
	•	If buyer has insufficient funds, protocol liquidates seller’s side to cover.
	4.	Once P/L is settled, return any remaining margin to both parties.
	•	This is a basic cash-settled forward—no daily mark-to-market, but at expiration we reconcile.
	3.	UI/UX for Forward Initiation
	•	On the “Live Market” page (or a new “Derivatives” tab), allow a supplier to say “I will sell 1 tonne Aug 15 ‘25 Coffee Grade 1 forward at £1250.”
	•	A buyer can see that posting in a “Derivatives Orderbook.” If the buyer agrees, they click “Take Position” → both parties are prompted to deposit margin → once both have deposited on-chain, the forward goes “active.”
	•	In /supplier/dashboard or /buyer/dashboard, show a list of “Active Forwards” (open positions). Display:
	•	Entry price, quantity, margin posted.
	•	Countdown to expiration (deliveryDate).
	•	“Settle Now” button (only active after deliveryDate).

By the end of Phase 2, you have a manual cash-settled forward contract system. Both sides have locked margin in a single escrow; on expiration, the contract reads the final oracle price and pays out P/L. You still don’t handle daily mark-to-market or partial liquidations between entry and expiry.

⸻

Phase 3: “Exchange-Style” Futures with Daily Mark-to-Market

If you want to move from a bilateral “forward” approach to a multi-party “futures” market—where many buyers and sellers can trade the same standardized contract, and margin is recalculated daily—you need to build a “clearinghouse” style on-chain infrastructure:
	1.	Standardizing Contract Sizes & Settlement Dates
	•	Decide on a handful of monthly futures contracts for each commodity. For example:
	•	CF_2025_08 = Coffee Grade 1, 1 tonne, deliverable August 2025.
	•	CF_2025_09 = Coffee Grade 1, 1 tonne, deliverable September 2025.
	•	Encode these as on-chain tokens or IDs so that the clearinghouse knows exactly which contract folks are trading.
	2.	On-chain Clearinghouse (Margin & MTM Mechanism)
We need a smart contract (or set of contracts) that does the following:
	1.	Open Position (BuyLong / SellShort)
	•	If you “buyLong(contractId, quantity),” you must deposit initialMargin = notional * marginRatio (e.g. 10 %). The contract records:

    struct Position {
  address trader;
  bytes32 contractId;       // e.g., "CF_2025_08"
  int256 quantity;          // (+1 for 1 ton long; –1 for 1 ton short)
  uint256 entryPrice;       // price at which position was opened
  uint256 marginPosted;     // USDT amount locked
}

•	Simultaneously, a market maker or another trader can “sellShort(contractId, quantity)” and post margin.
	•	The contract holds both margins in a pool.

	2.	Daily (or periodic) Mark-to-Market Settlement
	•	Each futures contract has an oracle (Chainlink) that pushes a settlement price every 24 hours (or every block).
	•	function settleDaily(bytes32 contractId) can be called by anyone (often a keeper) to:
	1.	Fetch price = Oracle(contractId).latestRoundData().
	2.	For each open Position on contractId:
	•	Compute ∆P/L = (price – position.entryPrice) * position.quantity * contractSizeMultiplier.
	•	If position.quantity > 0 (long), and price has gone up, that long gains. If price has gone down, that long loses. Shorts get the mirror P/L.
	•	Update each Position’s marginPosted += ∆P/L (long) or marginPosted -= ∆P/L (short).
	3.	If any position’s marginPosted falls below maintenance margin (e.g. 5 % of notional), force an “autoLiquidate(position)” (transfer collateral to the other side and close the position).
	•	In practice, you’d keep a mapping on-chain like mapping(bytes32 => Position[]) public openPositions; and every settleDaily loop pays out winners, debits losers.
	3.	Closing a Position Early
	•	If a trader wants to exit before expiration, they call function closePosition(positionId).
	•	The contract looks up current mark price from Oracle, computes P/L, adjusts the position’s margin, returns leftover margin to the trader, and removes the position from the open list.
	•	If there is no immediate counterparty to “flip” with on-chain, the contract itself can just store unmatched net positions and settle P/L against the margin pool (like a “central counterparty” would).
	4.	Expiration & Final Settlement
	•	On the official expiryTimestamp(contractId), the contract reads the final oracle price one last time.
	•	All remaining open positions on that contract are either:
	•	Cash-settled: P/L is calculated and returned in USDT. No physical delivery.
	•	Physically settled: If a given position.quantity > 0 (long), that holder can mint/redeem a “WarehouseReceiptNFT” and must then pick up actual beans. If a given position.quantity < 0 (short), they must deposit a receipt or arrange to deliver beans into a standard warehouse.
	5.	Governance & Parameter Tweaks
	•	Since margin ratios, maintenance margins, oracles, and contract sizes may need adjustment, you can store them in an on-chain “ClearinghouseParams” struct. If COMDEX has a DAO or admin key, you can update parameters over time as volumes grow.

	3.	Front-End Orderbook & UX
	•	Instead of “POST /api/forwards,” we now have a React page called /derivatives.
	•	A user picks a contract (e.g., “Coffee Aug 2025, 1 ton”). They see:
	•	Current “mid‐price” from the oracle feed.
	•	“Buy Long @ 1200 GBP” form → which calls openLong(contractId, quantity, margin).
	•	“Sell Short @ 1200 GBP” form → openShort(...).
	•	Under the hood, once they sign the transaction (MetaMask, WalletConnect), the margin (USDT) is pulled from their wallet and locked in the Clearinghouse contract. We show them a local “Position” card with:
	•	Entry price, notional, margin.
	•	“MTM P/L,” updated daily (or every few blocks) as /api/trader/positions or via a WebSocket pushing new settled prices.
	•	If they want to “Exit Position” early, they hit “Close,” which calls an on-chain closePosition(positionId).
	4.	Off-Chain Matching vs. On-Chain Autoclearing
	•	In an ideal “exchange,” bids and asks would match on-chain at specific prices. But that is gas‐heavy. A simpler approach:
	1.	Off-Chain Orderbook
	•	Build a standard “limit order” UI in Next.js. All bids and asks are posted to our central backend (Mongo/SQL).
	•	When a “match” occurs (i.e., a buyer’s bid ≥ seller’s ask), our backend automatically executes on-chain functions:
	•	Buyer’s margin deposit, seller’s margin deposit.
	•	Mint a single position for each side.
	•	Remove both orders from the off-chain orderbook.
	•	This keeps user experience smooth (instant matching) while settlement logic remains on-chain (the Clearinghouse contract).
	2.	On-Chain AMM (Advanced)
	•	If trading volume supports it, you can eventually create a constant‐product style AMM for each contract month, e.g. a “pools/CF_2025_08” contract.
	•	Liquidity providers deposit USDT and the futures token, earn fees.
	•	Traders can trade “USDT ↔ CF_2025_08” at on-chain price.
	•	Every swap is effectively opening/closing a tiny fraction of a futures contract.
	•	However, that requires handling LP impermanent loss vs. margin logic—it’s more advanced and optional for v1.

By the end of Phase 3, COMDEX will look and feel much like a mini futures exchange for each commodity, but built entirely on your own smart contracts (no centralized clearinghouse). Both spot and futures functionality coexist:
	•	Spot (Cash) Marketplace: Physical, escrowed trades for immediate delivery.
	•	Forward (OTC) Marketplace: Bilateral forward contracts, cash-settled at maturity.
	•	Futures (Exchange) Marketplace: Standardized monthly futures with on-chain margin, mark-to-market, and optional physical or cash settle.

⸻

4. How This Maps to the COMDEX Project Summary

Your Project Summary has a few high-level goals:
	1.	“On‐chain, Crypto‐Native Physical Commodities Trading”
	•	We already do this for spot.
	•	Our smart contracts hold collateral, mitigate counterparty risk, and encode “release funds on proof of delivery.”
	2.	“Leverage AI for Analytics, Price Forecasts, Terminal-Style Dashboards”
	•	You want a “Bloomberg Terminal” experience where a user can see real-time spot/futures curves, forward curves, volatilities, and AI commentary.
	•	In /supplier/dashboard and /buyer/dashboard, you can add new widgets:
	•	Spot price chart (live from Chainlink).
	•	Futures curve chart (plot of “June/July/Aug…” contract prices on the same axis).
	•	AI commentary box (e.g., GPT-powered insights: “Coffee forward curve is in contango; you might roll your position into October instead of September.”)
	3.	“Simplify Logistics + Settlement via Tokenized Warehouse Receipts”
	•	If a supplier wants to sell a forward that is “physically settled,” they must deposit a WarehouseReceipt NFT.
	•	We can partner with a warehouse operator to issue NFT receipts that the Clearinghouse contract can recognize.
	•	At expiry, if a long calls redeemReceipt(), they receive token ID X, which they can take to the origin warehouse for a physical withdrawal.
	4.	“Make It Easy for Speculators, Hedgers, Arbitrageurs”
	•	Retail speculators: trade small “1 ton,” “0.1 ton,” or “0.01 ton” versions of the futures contract.
	•	Hedgers (like small roasters): can buy “1 ton June forward” to lock price, then close before expiry (no physical receipt needed).
	•	Arbitrageurs: if COMDEX’s spot price differs materially from ICE price + transport, they can buy on COMDEX and short on ICE or vice versa—our public API can provide the “live benchmark.”

All of this aligns with your summary:

“Our platform lets participants trade real world commodities on chain. They can enter spot trades (cash) that immediately settle with escrow, or they can lock in future price exposure with standardized forward/futures contracts. Behind the scenes, our smart contracts manage collateral and settlement. Meanwhile, AI modules provide live analytics and forecasts.”

⸻

5. Concrete “Next Steps” for Your Repo

Below is a checklist of very specific changes (files to create/modify) that will turn your current COMDEX code (which is mostly spot) into a hybrid Spot + Futures platform.

5.1. Smart Contracts
	1.	SpotEscrow.sol (already exists)
	•	Double-check that it has:


    function depositBuyerFunds(uint256 listingId) external payable { … }
function depositSupplierSecurity(uint256 listingId, uint256 warehouseReceiptTokenId) external { … }
function releaseFunds(uint256 listingId) external onlyWhenBothDeposited(…) { … }
function refundBuyer(uint256 listingId) external onlyAfterTimeout(…) { … }

•	Make sure it emits events (ListingFunded, ShipmentConfirmed, DeliveryConfirmed, etc.)

	2.	ForwardEscrow.sol (New)
­ Draft a contract that allows two‐party margin deposits and cash settlement at expiration. Rough sketch:

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract ForwardEscrow {
    IERC20 public immutable usdt;       // stablecoin for margin + settlement
    AggregatorV3Interface public oracle;  // e.g. Chainlink PriceFeed (GBP/USD or GBP per tonne)

    struct Forward {
        address buyer;
        address seller;
        bytes32 commodity;      // e.g. "COFFEE_GRADE1"
        uint256 quantity;       // in kg or tonnes (multiply out internally)
        uint256 pricePerUnit;   // locked price, in GBP per tonne (scaled by 1e18)
        uint256 buyerMargin;    // 10% margin in USDT
        uint256 sellerMargin;   // 10% margin or NFT collateral
        uint256 expiryTimestamp;
        bool    settled;
    }

    mapping(uint256 => Forward) public forwards;
    uint256 public nextForwardId;

    event ForwardCreated(uint256 forwardId, address buyer, address seller, bytes32 commodity, uint256 quantity, uint256 expiry);
    event MarginDeposited(uint256 forwardId, address who, uint256 amount);
    event Settled(uint256 forwardId, int256 pnlBuyer, int256 pnlSeller);

    constructor(address _usdtToken, address _oracle) {
        usdt = IERC20(_usdtToken);
        oracle = AggregatorV3Interface(_oracle);
    }

    function createForward(
        address seller_,
        bytes32 commodity_,
        uint256 quantity_,
        uint256 pricePerUnit_,
        uint256 expiryTimestamp_
    ) external returns (uint256) {
        uint256 id = nextForwardId++;
        Forward storage f = forwards[id];
        f.buyer = msg.sender;
        f.seller = seller_;
        f.commodity = commodity_;
        f.quantity = quantity_;
        f.pricePerUnit = pricePerUnit_;
        f.expiryTimestamp = expiryTimestamp_;
        // buyerMargin and sellerMargin set to 0 until they deposit
        emit ForwardCreated(id, msg.sender, seller_, commodity_, quantity_, expiryTimestamp_);
        return id;
    }

    function depositBuyerMargin(uint256 forwardId, uint256 amount) external {
        Forward storage f = forwards[forwardId];
        require(msg.sender == f.buyer, "Only buyer can deposit margin");
        // e.g. require amount >= 10% of notional (quantity * pricePerUnit) 
        // scaled appropriately
        usdt.transferFrom(msg.sender, address(this), amount);
        f.buyerMargin = amount;
        emit MarginDeposited(forwardId, msg.sender, amount);
    }

    function depositSellerMargin(uint256 forwardId, uint256 amount) external {
        Forward storage f = forwards[forwardId];
        require(msg.sender == f.seller, "Only seller can deposit margin");
        // require amount >= 10% of notional OR deposit NFT as proof
        usdt.transferFrom(msg.sender, address(this), amount);
        f.sellerMargin = amount;
        emit MarginDeposited(forwardId, msg.sender, amount);
    }

    function settle(uint256 forwardId) external {
        Forward storage f = forwards[forwardId];
        require(block.timestamp >= f.expiryTimestamp, "Not yet expired");
        require(!f.settled, "Already settled");
        // 1) Read final oracle price (GBP per tonne * 1e18)
        (, int256 price, , , ) = oracle.latestRoundData();
        uint256 finalPrice = uint256(price);
        // 2) Compute P/L: (finalPrice - f.pricePerUnit) * quantity 
        //   If finalPrice > f.pricePerUnit, buyer owes extra
        int256 priceDiff = int256(finalPrice) - int256(f.pricePerUnit);
        int256 pnlBuyer   = priceDiff * int256(f.quantity) / 1e18; // careful with scaling
        int256 pnlSeller  = -pnlBuyer;

        // 3) Transfer USDT accordingly:
        //    If pnlBuyer > 0: buyer actually *wins* and gets that from seller margin
        //    If pnlBuyer < 0: buyer must pay extra out of their margin
        if (pnlBuyer > 0) {
            // buyerProfit <= sellerMargin
            require(uint256(pnlBuyer) <= f.sellerMargin, "Seller margin insufficient");
            usdt.transfer(f.buyer, uint256(pnlBuyer));
            usdt.transfer(f.seller, f.sellerMargin - uint256(pnlBuyer) + f.buyerMargin);
        } else {
            // buyerLoss: buyerMargin covers it, leftover returns to seller
            int256 loss = -pnlBuyer;
            require(uint256(loss) <= f.buyerMargin, "Buyer margin insufficient");
            usdt.transfer(f.seller, uint256(loss));
            usdt.transfer(f.buyer, f.buyerMargin - uint256(loss) + f.sellerMargin);
        }
        f.settled = true;
        emit Settled(forwardId, pnlBuyer, pnlSeller);
    }
}

•	This contract is a simple cash-settled forward. You can extend for NFT collateral and physical settlement in Phase 4.

	3.	FuturesClearinghouse.sol (Advanced, Phase 3)
	•	This contract is more complex and requires:
	•	Data structures for open positions (mapping(uint256 => Position) with auto‐incrementing IDs).
	•	Margin logic (initial margin, maintenance margin).
	•	Daily (or periodic) settlement function that reads from the oracle.
	•	Auto liquidation if margin < maintenance.
	•	You can use OpenZeppelin’s ERC20 as the margin token (USDT).
	•	Pseudocode for key functions:

    struct Position {
    address trader;
    bytes32 contractId;   // e.g. "COFFEE_2025_08"
    int256 quantity;      // positive = long, negative = short
    uint256 entryPrice;   // price at which this position was opened
    uint256 margin;       // current margin posted
    bool    isOpen;       // true until closed
}

mapping(uint256 => Position) public positions;
uint256 public nextPosId;

// parameters controlled by governance
uint256 public initialMarginRatio = 10;      // 10%
uint256 public maintenanceMarginRatio = 5;   // 5%

function openPosition(
  bytes32 _contractId,
  int256  _quantity,      // +1 (long 1 ton), –1 (short 1 ton)
  uint256 _priceAtOpen    // external user enters their desired fill price
) external {
  // 1) Calculate notional = _priceAtOpen × abs(_quantity)
  uint256 notional = uint256(_priceAtOpen) * uint256(_quantity < 0 ? -_quantity : _quantity) / 1e18;
  // 2) Calculate requiredMargin = notional * initialMarginRatio / 100
  uint256 requiredMargin = notional * initialMarginRatio / 100;
  // 3) Transfer requiredMargin USDT from msg.sender
  usdt.transferFrom(msg.sender, address(this), requiredMargin);
  // 4) Create Position
  uint256 pid = nextPosId++;
  positions[pid] = Position({
    trader:      msg.sender,
    contractId:  _contractId,
    quantity:    _quantity,
    entryPrice:  _priceAtOpen,
    margin:      requiredMargin,
    isOpen:      true
  });
  // 5) Emit event
  emit PositionOpened(pid, msg.sender, _contractId, _quantity, _priceAtOpen, requiredMargin);
}

function closePosition(uint256 pid) external {
  Position storage pos = positions[pid];
  require(pos.isOpen && pos.trader == msg.sender, "Cannot close");
  // 1) Fetch current oracle price
  (, int256 price, , , ) = oracleFor(pos.contractId).latestRoundData();
  uint256 currentPrice = uint256(price);
  // 2) Compute mark2market P/L = (currentPrice – pos.entryPrice) × pos.quantity
  int256 rawDiff = int256(currentPrice) - int256(pos.entryPrice);
  int256 pAndL   = rawDiff * pos.quantity / 1e18; // careful scaling
  // 3) If P/L > 0: return pos.margin + P/L to trader.  
  //    If P/L < 0: subtract from pos.margin; if pos.margin < 0, liquidate.
  uint256 payout;
  if (pAndL >= 0) {
    payout = pos.margin + uint256(pAndL);
    usdt.transfer(pos.trader, payout);
  } else {
    uint256 loss = uint256(-pAndL);
    require(loss <= pos.margin, "Position under collateralized");
    uint256 leftover = pos.margin - loss;
    // leftover goes back to trader
    usdt.transfer(pos.trader, leftover);
    // and loss is split to whoever is net counterparty or to a default fund
    // (simplify: send loss to a “defaultFund” address)
    usdt.transfer(defaultFund, loss);
  }
  pos.isOpen = false;
  emit PositionClosed(pid, pos.trader, pAndL, payout);
}

function settleDaily(bytes32 contractId) external {
  // Called by a keeper each day for each active contract.
  (, int256 price, , , ) = oracleFor(contractId).latestRoundData();
  uint256 todayPrice = uint256(price);

  // For each open position on this contract:
  //   (you need some iterable data structure, e.g. an array or linked list)
  for (uint256 pid in openList[contractId]) {
     Position storage pos = positions[pid];
     if (!pos.isOpen) continue;
     // 1) Compute yesterday’s P/L for this position:
     int256 rawDiff = int256(todayPrice) - int256(pos.entryPrice);
     int256 dailyPL  = rawDiff * pos.quantity / 1e18;
     // 2) Adjust margin:
     if (dailyPL >= 0) {
       pos.margin += uint256(dailyPL);
     } else {
       uint256 loss = uint256(-dailyPL);
       if (loss >= pos.margin * maintenanceMarginRatio / 100) {
         // If after this loss, margin < min maintenance, liquidate
         _liquidate(pid);
       } else {
         pos.margin -= loss;
       }
     }
     // 3) Update pos.entryPrice = todayPrice (so next MTM is incremental)
     pos.entryPrice = todayPrice;
  }
}

function _liquidate(uint256 pid) internal {
  Position storage pos = positions[pid];
  // Force‐close at current oracle price
  (, int256 price, , , ) = oracleFor(pos.contractId).latestRoundData();
  uint256 currentPrice = uint256(price);
  // Calculate final P/L same as closePosition
  int256 rawDiff = int256(currentPrice) - int256(pos.entryPrice);
  int256 pAndL   = rawDiff * pos.quantity / 1e18;
  // If net P/L < 0, penalty is subtracted from margin; if net P/L >= 0, send profit to trader
  if (pAndL >= 0) {
    usdt.transfer(pos.trader, pos.margin + uint256(pAndL));
  } else {
    uint256 loss = uint256(-pAndL);
    // all margin is lost to defaultFund
    pos.margin = 0;
    usdt.transfer(defaultFund, loss);
  }
  pos.isOpen = false;
  emit PositionLiquidated(pid, pos.trader, pAndL);
}

	•	This is only a pseudocode sketch—real implementation must handle:
	•	Precision/scaling (1e18 vs. decimals).
	•	Gas costs (iterating over all positions is expensive → use a data structure per contract).
	•	Who pays “defaultFund” and how losers are redistributed.

	4.	WarehouseReceiptNFT.sol (Phase 4, Optional)
	•	For “physical settlement” on futures, you might mint an ERC-721 onto an approved warehouse operator’s contract.
	•	If a long holds open into expiry and wants beans, they call issueReceipt() → the NFT is minted to them. Then COMDEX’s back-end (or the warehouse operator) triggers an off-chain shipping workflow.
	•	If the long just wants cash, they call cashSettle() on that same contract, which pays out from margin.

⸻

5.2. Backend & Database Enhancements
	1.	New Models / Collections
	•	“Forwards” or “FuturesMarket” collections that store each open forward/futures position (with references to on-chain tx hashes, margin amounts, expiry).
	•	“Orders” collection for off-chain orderbook (Phase 3): { user, contractId, quantity, price, side, timestamp }
	2.	APIs
	•	Phase 2 (Forwards):
	•	POST /api/forwards → create a forward offer (buyer/seller pair).
	•	POST /api/forwards/:id/deposit-buyer-margin → server calls on-chain depositBuyerMargin.
	•	POST /api/forwards/:id/deposit-seller-margin → server calls on-chain depositSellerMargin.
	•	POST /api/forwards/:id/settle → server calls on-chain settle once expiryTimestamp passes.
	•	GET  /api/forwards/:id → read forward details & on-chain status.
	•	Phase 3 (Futures):
	•	POST /api/futures/open → open a long/short position (backend orchestrates the on-chain openPosition(...)).
	•	POST /api/futures/close → close a position early (calls on-chain closePosition(...)).
	•	GET  /api/futures/positions?user=0xABC... → list the user’s open positions (fetch on-chain state + DB metadata).
	•	GET  /api/futures/book?contractId=CF_2025_08 → if you’re running an off-chain orderbook, return current bids/asks.
	•	POST /api/futures/orderbook → place a new limit order (backend keeps it in Mongo, matches it, and triggers the on-chain open/close calls).
	•	GET  /api/futures/curve → return the full list of all front-month, next-month, next-next-month prices as an array—fed from Chainlink or COMDEX’s own front end.
	3.	Authentication & Role Logic
	•	useAuthRedirect('buyer') and useAuthRedirect('supplier') already handle the routing.
	•	For futures, anyone (supplier or buyer) can take a long or short position. You don’t need a special “futures trader” role—just any authenticated user.
	•	You might add a new role “trader” if you eventually want to whitelist only certain users for high-leverage futures, or if KYC is required to exceed a volume threshold.

⸻

5.3. Front-End Code Changes
	1.	New Pages & Components
	•	/derivatives/index.tsx
	•	A page that lists all available COMDEX futures (e.g. “Coffee Aug 2025, 1 ton,” “Corn Sep 2025, 1 ton,” etc.).
	•	Each row shows: Current price (from oracle), time to expiry, bid/ask fields.
	•	“Buy Long” form → calls a hook that signs a transaction for openPosition(...).
	•	“Sell Short” form → calls openPosition(contractId, -quantity, price).
	•	/components/FuturesBook.tsx
	•	Displays the live off-chain orderbook (bids/asks) for one contract.
	•	Hooks into a WebSocket or useSWR('/api/futures/book?contractId=CF_2025_08') to update every few seconds.
	•	/components/PositionCard.tsx
	•	Shows an individual open position’s details: entry price, margin, current MTM P/L, expiration countdown.
	•	“Close Position” button calls closePosition(...).
	•	/components/CurveChart.tsx
	•	A line chart (or bar chart) showing the futures curve: each contract’s front-month price, next-month price, etc.
	•	Use your existing <Chart /> component, but feed it an array of { time: expiryTimestamp, value: price }.
	•	Modify Navbar.tsx
	•	Add a new “Derivatives” link next to “Live Market” so that traders can click to view the futures page.
	•	E.g.

    <Link href="/derivatives" …>
  <button className="px-3 py-1 border border-text-primary …">
    Derivatives
  </button>
</Link>

	•	Modify Sidebar.tsx
	•	If a user has any “open futures positions,” show a quick link “My Positions” that navigates to /derivatives/positions.
	•	In SidebarProps, you may add an extra boolean or count: openPositionsCount: number → so the menu can display “My Positions (2).”

	2.	Dashboard Enhancements
	•	/supplier/dashboard.tsx
	•	Under the “Spot Chart” placeholder, replace the placeholder box with <SpotPriceChart commodity="coffee" />, which fetches a Chainlink price feed for spot.
	•	Under “AI Analysis,” add a small <AIInsights commodity="coffee" /> component that uses an API to ask GPT: “Given last 30 days of spot/midcurves, what’s the trend?”
	•	Below “My Listings,” add a small widget “My Open Forwards” if the supplier has created or taken any forward contracts.
	•	/buyer/dashboard.tsx
	•	Similarly, show “My Spot Purchases” and “My Open Forwards/Positions” with quick links to /derivatives/positions.
	3.	Utility Hooks & Context
	•	Create a new hook useFuturesPositions() that fetches from /api/futures/positions?user=… and returns an array of open positions.
	•	Create useOraclePrice(contractId) that subscribes to a WebSocket or poll for the latest price from Chainlink, so you can display real-time quotes on the UI.
	4.	Styling & UX Considerations
	•	Futures/forwards pages should maintain the same styling system as your spot pages (Tailwind classes, dark mode toggle, spacing conventions).
	•	Make sure all new buttons (“Open Long,” “Open Short,” “Close Position”) use the same height, border colors, text alignment, and hover states as the rest of your UI (as you just updated in Navbar.tsx and Sidebar.tsx).

⸻

6. Putting It All Together: Example Workflows

Below are two “end‐to‐end” user journeys—one purely spot, one purely futures—so you can see how the front end, back end, and smart contracts interact.

⸻

6.1. Spot Purchase Flow (Already in Place)
	1.	Supplier Lists a Product
	•	/supplier/dashboard → “+ Sell Product” → fill out “New Product” form:
	•	Title = “100 kg Arabica Grade 1 (Warehouse A)”
	•	Price per kg = £1.23
	•	Origin = USA, Category = Coffee, Quantity = 100 kg
	•	Delivery terms = “Within 7 days of purchase, deliver to Buyer’s warehouse.”
	•	On submit, React calls POST /api/products → server stores the listing in DB and emits an event.
	2.	Buyer Views Live Market
	•	/products → sees the 100 kg listing PLUS an aggregate line chart showing “Average Spot Price (last 24 h).”
	•	If buyer likes it, they click “Buy” → React calls POST /api/deals with { productId, buyerAddress }.
	3.	Escrow Is Funded
	•	Back-end relays that to SpotEscrow.depositBuyerFunds(productId, amountInWei) on-chain. Buyer signs that TX with MetaMask.
	•	That locks buyer’s USDT in the escrow contract.
	4.	Supplier Confirms Shipment
	•	In /supplier/dashboard, the supplier sees “Incoming purchase for product #42” → clicks “Confirm Shipment.”
	•	Off-chain, they update the record to “Shipment initiated,” and on-chain they call depositSupplierSecurity(productId, tokenId) where tokenId is an NFT representing a warehouse receipt.
	•	That deposits either additional collateral or a pointer to off-chain proof of inventory.
	5.	Buyer Confirms Delivery & Escrow Release
	•	Buyer’s side triggers an off-chain inspection (3rd party). Once satisfied, React calls POST /api/deals/:dealId/confirm-delivery.
	•	Back-end verifies inspection, and then calls on-chain SpotEscrow.releaseFunds(productId). That releases buyer’s USDT to supplier.
	•	Supplier is paid, buyer is marked complete, both parties’ sold/purchase counts are updated, and the listing closes.

⸻

6.2. Futures Position Flow (Phase 3)
	1.	User Selects a Futures Contract
	•	Trader goes to /derivatives → sees a list:

    | Commodity | Expiry     | Contract Size | Last Price | 24h Change | Buy/Sell Forms |
| Coffee     | Aug 2025   | 1 tonne       | £1230/t    | +0.50%     | [ Buy Long ] [ Sell Short ] |
| Coffee     | Sep 2025   | 1 tonne       | £1245/t    | +0.75%     | [ Buy Long ] [ Sell Short ] |
| Wheat      | Sep 2025   | 1 tonne       | £210/t     | –1.20%     | [ Buy Long ] [ Sell Short ] |

	•	Each “Last Price” is pulled from a Chainlink feed or from our on-chain Clearinghouse state.

	2.	Trader Opens a Long Position
	•	Trader clicks “Buy Long” next to “Coffee Aug 2025 @ £1230/t.”
	•	A modal pops up: “How many tonnes? [1] [2] [5]”
	•	They choose “1,” hit “Confirm,” and MetaMask asks them to sign a transaction:

    •	Each “Last Price” is pulled from a Chainlink feed or from our on-chain Clearinghouse state.

	2.	Trader Opens a Long Position
	•	Trader clicks “Buy Long” next to “Coffee Aug 2025 @ £1230/t.”
	•	A modal pops up: “How many tonnes? [1] [2] [5]”
	•	They choose “1,” hit “Confirm,” and MetaMask asks them to sign a transaction:

    Clearinghouse.openPosition(
  contractId = keccak256("COFFEE_2025_08"),
  quantity = +1 * 1e18,            // 1 tonne (scaled)
  entryPrice = 1230 * 1e18         // £1230/t (scaled)
);

	•	On success, the smart contract locks initialMargin = £1230/t × 1 ton × 0.10 = £123 in USDT.
	•	Front end stores positionId = 17 in the back end for quick reference. The UI now shows “Open Position #17: Long 1 ton COFFEE Aug 2025 @ £1230/t, Margin £123.00. P/L: 0.00.”

	3.	Daily Mark-to-Market
	•	A cron job or off-chain “keeper” hits Clearinghouse.settleDaily("COFFEE_2025_08") every 24 h:
	1.	Reads price from Chainlink: Suppose tomorrow’s price is £1250.
	2.	Our code computes pAndL = (1250 – 1230) × 1 ton = £20.
	3.	The contract takes “£20” from the short side’s margin pool and adds it to the long side’s margin.
	4.	Position #17’s margin becomes £123 + £20 = £143.
	•	Front end fetches updated margin with useFuturesPositions() → shows “Updated Margin: £143, Unrealized P/L: +£20.”
	4.	Trader Closes Position Early
	•	On day 5, the trader decides “I’m done.” They click “Close Position #17.”
	•	React calls Clearinghouse.closePosition(17).
	•	Suppose today’s mark price is £1270. That P/L = (1270 – 1230) × 1 ton = £40.
	•	The contract calculates: “Long had margin £143. P/L = +£40. So send £143 + £40 = £183 back to trader.”
	•	The short side loses £40 from their margin pool; the remainder (whatever is left) goes to default fund or back to them.
	•	Position #17 is marked closed; front end removes it from “Open Positions” and moves it to “Closed Positions: P/L = +£40.”
	5.	Position at Expiry (If Held)
	•	If the trader had held to expiry (Aug 1, 2025 at midnight UTC), then:
	•	A keeper calls Clearinghouse.settleExpiry("COFFEE_2025_08").
	•	Oracle price at that time is, say, £1300.
	•	The contract computes final P/L = (1300 – 1230) × 1 ton = £70.
	•	Since it’s a cash-settled contract, we simply send the net amount to the winner’s wallet (long or short).
	•	If it were a “physically settled” flavor, the long’s margin would convert into WarehouseReceiptNFT + leftover USDT. They could then go pick up beans from a partner warehouse.

⸻

7. Why COMDEX Can Be a “Crypto Coffee Exchange + Spot Hub”

By incrementally layering:
	1.	Phase 1: Spot (OTC) “Cash” Trades
	2.	Phase 2: Bilateral Forwards (Cash-Settled at Expiry)
	3.	Phase 3: Multi-Party Futures with Daily MTM

you turn your existing OTC code into a full hybrid platform. Here’s why this matches your project summary:

“We’re building a decentralized commodities hub where producers, roasters, and speculators can all meet.
	1.	A local coffee roaster can come to COMDEX, log in, and buy 1 tonne of Grade 1 coffee at spot price. On chain, we lock funds in escrow, track shipping, and release payment on proof of delivery.
	2.	A small coffee importer can come to “Forwards,” lock in £1200/t for August delivery. They post margin; the exporter posts margin. On August 1, our contract automatically settles the difference in USDT.
	3.	A speculator (with 0.1 ETH) can go to “Futures,” deposit margin for a 1 tonne “Coffee Sep 2025” contract, and trade it daily. They can exit any time, never touching beans.
	4.	Meanwhile, AI modules generate “Morning Coffee Dashboard” insights: “The August ’25 contract is in steep contango versus spot. If you hold to expiry, you’ll pay a premium relative to ICE. We recommend entering a short position if you have coffee in inventory.”**

Dozens of commodity platforms exist in TradFi, but few do both spot + futures in a single interface, and none do it in a truly on-chain, tokenized, crypto-native way—until COMDEX.

⸻

8. Summary & Next “Sprint” Checklist

Below is a very concrete list of “to-do” items you can treat as your next sprint:
	1.	Deploy ForwardEscrow.sol
	•	Write tests (Hardhat/Foundry) for:
	•	Two parties deposit margin.
	•	Price moves up/down on expiry → correct payout.
	•	If a party never deposits margin, the other party can cancel and reclaim.
	•	Integrate Chainlink Price Feeds for each commodity.
	2.	Build Forward REST API & UI
	•	In Next.js:
	•	New page /forwards/index.tsx (list open forwards, create new).
	•	Hook up POST /api/forwards → calls ForwardEscrow.createForward(...).
	•	UI flow: “Select commodity,” “Enter quantity & target expiry + price,” “Choose counterparty or let the system auto‐match.”
	•	After creation, show a “Deposit Margin” button (calls depositBuyerMargin or depositSellerMargin).
	•	Show status: “Waiting on seller margin,” “Fully collateralized,” “Expiry in 5 days,” etc.
	3.	Deploy FuturesClearinghouse.sol (Phase 3)
	•	Define a handful of contract IDs (e.g., keccak256(“COFFEE_2025_08”) → subgraph or on-chain metadata).
	•	Write tests for open/close, daily MTM, auto-liquidation.
	•	Add oracle feed addresses → make sure prices are denominated in the same units (e.g. GBP per tonne ×1e18).
	4.	Build Futures REST API & UI
	•	Pages:
	•	/derivatives/index.tsx (list active futures contracts, buy/sell form).
	•	/derivatives/positions.tsx (list your open positions & closed history).
	•	Components:
	•	<FuturesBook contractId="COFFEE_2025_08" /> to show current bid/ask from off-chain DB.
	•	<PositionCard positionId={…} /> to show each open position’s real-time P/L.
	•	<CurveChart /> to visualize the entire futures curve.
	5.	Back End
	•	New collections: forwards, futures_orders, futures_positions.
	•	New endpoints:
	•	/api/forwards, /api/forwards/:id/deposit-buyer, /api/forwards/:id/deposit-seller, /api/forwards/:id/settle.
	•	/api/futures/order (create/modify limit orders), /api/futures/book?contractId=…, /api/futures/positions?user=….
	•	Worker scripts/cron jobs:
	•	A “keeper” that runs ForwardEscrow.settle(...) when any forward expires.
	•	A “daily MTM” job that calls FuturesClearinghouse.settleDaily(...) for each active contract.
	6.	Front-End Alignment & Styling
	•	Make sure all new buttons use the same Tailwind classes you standardized in Navbar.tsx—consistent border, height, text alignment.
	•	In Sidebar.tsx, show “Forwards” and “Futures” only if the user has any open positions or if their role = buyer/supplier.
	•	On each new page, re-use your existing Header (navbar + sidebar), Footer, and dark mode toggle for a uniform look.

Once you complete those six high-level tasks, COMDEX will truly be:
	•	A unified Spot + Forward + Futures platform for physical commodities,
	•	Fully on-chain margin, escrow, and settlement,
	•	Deeply integrated with AI insights (via your existing <AIAnalysis /> component),
	•	Able to serve producers, end-users, and speculators all in one place.

I hope this step-by-step roadmap gives you clarity on how to “build in those futures/derivatives features” on top of your existing spot/OTC code. In essence:

	1.	Stand up a Phase 2 ForwardEscrow (cash-settled on expiry).
	2.	Extend to a Phase 3 Clearinghouse (daily mark-to-market, on-chain margin, multi-party matching).
	3.	Connect both back end and front end to reflect new “forwards” and “futures” pages.
	4.	Keep using the same AI & charting modules (just swap in new data sources from Chainlink or on-chain states).

That way, your next few sprints can focus on one piece at a time (ForwardEscrow, then Clearinghouse), without ripping out your spot infrastructure—ultimately giving COMDEX a fully end-to-end crypto-native commodity trading platform.



