Document 1: How Everything Works - STICKEY Platform
STICKEY is designed to simplify and streamline global commodity trade, leveraging blockchain technology, AI, and a decentralized approach to create an efficient and transparent marketplace. Here's how it works:

1. Landing Page:
User Interaction:

New users can either sign up or log in via wallet-based authentication (using MetaMask).

The wallet automatically logs users in if previously registered, making the platform easy to use.

Once logged in, users can view their wallet balance in $GLU.

Product Search:

A simple search bar for commodities. Initially, it will feature basic options like Whey Protein and Cocoa. In the future, AI will enable advanced searches (e.g., "Find a supplier in South Africa for 1 tonne of organic coffee beans").

Real-time price and exchange rates for commodities will be displayed in a scrolling bar.

Currency Swap:

Swap currency option will be visible on the homepage but will expand when clicked to facilitate easy conversion of GBP, USD, and other major currencies into $GLU.

2. Product Search Page:
Product Listings:

Displays key information about each product like supplier name, origin, price per kg in $GLU and USD, and certifications.

Basic filters like price, rating, and supplier type.

Product Details:

Clicking on a product brings the user to a dedicated product page.

This page includes detailed specifications, media (images/videos), supplier details, minimum order quantity, production date, and shipping details.

3. Product Page (Amazon-like):
Generate Quote:

The "Generate Quote" button initiates the process of creating a smart contract draft for the product, starting the negotiation process.

Shipping Options:

Users can either arrange shipping themselves or request a quote from the supplier.

Shipping providers (DHL, UPS) can upload a quote, and this becomes part of the contract.

4. Contract Creation & Escrow:
Draft Contract:

Once a quote is generated, a contract is created that includes all the terms (price, quantity, supplier/buyer details, delivery terms, and payment in escrow).

Escrow:

Payment is locked in escrow once both parties agree on the terms.

Shipping Confirmation: Once the product is scanned by the shipping provider, the escrow funds are released to the supplier.

5. Dashboard Features:
Buyer Dashboard:

Displays saved quotes, transaction history, active quotes, and wallet balance.

Allows for accepting or rejecting quotes and finalizing purchases.

Supplier Dashboard:

Allows suppliers to manage incoming quotes, accept/decline quotes, and track active deals.

Shipping provider management: Suppliers can manage their preferred shipping providers and add quotes to deals.

6. Smart Contract and Blockchain:
Smart Contract:

Each transaction is recorded on the blockchain, and an NFT will be generated as a certificate of authenticity.

Escrow System:

Funds are released only when the product is collected by the shipping provider and scanned (via QR code) to confirm delivery.

7. Dispute Resolution:
In case of a dispute, automatic rules are defined to protect both parties.

If a dispute arises, it can be resolved through an internal mediation system or third-party arbitration.

8. Shipping Integration:
Initially, the platform allows manual shipping arrangements between buyers and sellers.

In the future, an integrated API will provide live shipping quotes and tracking (e.g., via DHL, UPS).
📄 “How Everything Works” ⇄ Roadmap Mapping

| Section                        | Doc Details                                                                                            | Roadmap Item(s)                                                                                |
| ------------------------------ | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **Landing Page & Wallet Auth** | • MetaMask‑based login (auto‑reconnect) <br> • Show \$GLU balance                                      | ✅ MVP: MetaMask connect & backend binding <br> ⚙️ Phase 1: Seller/Buyer flows                  |
| **Product Search**             | • Simple search bar for commodities (Whey, Cocoa…) <br> • Future AI‑driven advanced query              | ✅ MVP: Public marketplace search <br> 🤖 Phase 4: AI Matching Engine                           |
| **Real‑time Price Ticker**     | • Scrolling exchange rates (GLU/USD/local)                                                             | 🔄 Phase 3: Live rate API & swap engine integration                                            |
| **Currency Swap**              | • Inline swap of GBP, USD → \$GLU <br> • Expanded view for multi‑currency                              | ✅ MVP: Dummy SwapPanel <br> ⚙️ Phase 3: On‑chain Swap Engine                                   |
| **Product Listings & Filters** | • List product cards with supplier, origin, price/kg in \$GLU & USD <br> • Filters (price, rating…)    | ✅ MVP: Product listing/search <br> ⚙️ Phase 2: Detail page + filters                           |
| **Product Detail Page**        | • Full specs, media, MOQ, production, shipping                                                         | ⚙️ Phase 2: `/product/[id]` detail + “Generate Quote”                                          |
| **Generate Quote & Shipping**  | • “Generate Quote” → smart‑contract draft <br> • Supplier uploads shipping quote or manual arrangement | ⚙️ Phase 2: Quote flow via SwapPanel → deal creation <br> ⚙️ Phase 3: Shipping API integration |
| **Contract & Escrow**          | • Smart contract draft → both parties agree → funds locked in escrow                                   | ✅ MVP: Manual deals + PDF <br> ⚙️ Phase 3: On‑chain escrow integration                         |
| **Shipping Confirmation**      | • QR scan by shipper → escrow release                                                                  | ⚙️ Phase 3: Shipping tracking & escrow release triggers                                        |
| **Buyer Dashboard**            | • Saved quotes, transaction history, active quotes, wallet balance                                     | ⚙️ Phase 2: Buyer Dashboard skeleton + deals                                                   |
| **Supplier Dashboard**         | • Manage incoming quotes, accept/decline, active deals <br> • Manage shipping providers                | ⚙️ Phase 2: Supplier Dashboard + deals tab                                                     |
| **Smart Contract & NFT Certs** | • Record tx on‑chain <br> • Mint NFT as certificate                                                    | ⚙️ Phase 3: Product passport & NFT explorer                                                    |
| **Dispute Resolution**         | • Rules‑based mediation or third‑party arbitration                                                     | 🤖 Phase 4: Dispute workflows                                                                  |

