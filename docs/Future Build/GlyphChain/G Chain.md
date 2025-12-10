graph TD
  %% ============================================
  %% P0 – BOOTSTRAP & FOUNDATIONS
  %% ============================================
  subgraph P0[Phase 0 – Repo, Architecture & Foundations]
    direction TB

    P0_1[Project Bootstrapping\n• Monorepo layout (chain, GMA, wallet, holo-bridge)\n• Language/runtime choice (Rust/Go for node, Solidity/Move/WASM for contracts)\n• Coding standards, linting, CI skeleton\n• Env config & secrets strategy]    

    P0_2[Core Specs & Interfaces\n• Finalize ChainState, Account, BlockHeader, Tx types\n• Confirm Photon/Tesseract token specs\n• Confirm GMA types (reserves, bonds, facilities)\n• Confirm Holo/QWave bridge interfaces\n• Decide consensus engine (Tendermint/CometBFT/custom BFT)]

    P0_3[Node Framework Selection\n• Choose base (Cosmos-SDK/Substrate/custom)\n• Decide execution layer (EVM-compatible vs WASM)\n• Identify where GMA lives (module vs contracts)\n• Identify extension points for Holo/QQC]

    P0_4[Security & Crypto Baseline\n• Choose signature schemes (ed25519/secp256k1/BLS)\n• Hashing & commitment scheme (Merkle, KZG later)\n• Key derivation & wallet seed format\n• Threat model for chain & GMA]

  end

  %% ============================================
  %% P1 – CORE CHAIN
  %% ============================================
  subgraph P1[Phase 1 – Core Chain (Ledger, Consensus, Bank)]
    direction TB

    P1_1[Consensus & Networking\n• Implement/plug BFT PoS engine\n• Validator set mgmt, epochs, staking hooks\n• Gossip protocol for blocks & txs\n• Peer discovery, anti-DoS basics]

    P1_2[State & Storage\n• Implement ChainState structure\n• Accounts trie (balances, nonces)\n• StateRoot computation\n• Persistence, snapshots, pruning strategy]

    P1_3[Block & Tx Format\n• BlockHeader (state_root, tx_root, holo_state_root, beam_state_root)\n• Tx envelope (from, nonce, gas, type, payload)\n• Sign/verify pipeline\n• Mempool implementation & ordering]

    P1_4[Bank Module\n• Ledger for PHO, TESS and future denoms\n• getBalance, getSupply, send, mint, burn (internal)\n• Fee charging & fee routing plumbing\n• Invariant checks (no negative balances, conserved supply)]

    P1_5[Staking Module (Skeleton)\n• TESS staking / delegation structs\n• delegate(), undelegate(), rewards bookkeeping\n• Validator power from TESS stake\n• Hooks into consensus engine]

    P1_6[Genesis & Config\n• Genesis file schema (allocs, validators, params)\n• ChainID & network IDs\n• Default gas schedule & limits\n• Basic upgrade mechanism placeholder]

  end

  %% ============================================
  %% P2 – TOKENS & AMM
  %% ============================================
  subgraph P2[Phase 2 – Photon, Tesseract, wGLYPH, AMM]
    direction TB

    P2_1[Photon Token (PHO)\n• Implement native asset or ERC20-like module\n• Mint/burn restricted to GMA\n• Transfer, approve, allowance if ERC20 style\n• Gas token integration (fees in PHO)]

    P2_2[Tesseract Token (TESS)\n• Implement as native or ERC20-like\n• Genesis mint & vesting\n• Hooks for staking/governance\n• Optional fee discount logic]

    P2_3[Wrapped Glyph (wGLYPH)\n• Fungible token module for bridged GLYPH\n• Mint/burn restricted to BridgeModule\n• Tracking supply & events]

    P2_4[AMM Pools\n• Generic constant-product pool contract\n• Pools: wGLYPH/PHO, wGLYPH/TESS, PHO/TESS\n• addLiquidity/removeLiquidity\n• swapExactIn, getReserves\n• Fee mechanism (cut for GMA & LPs)]

    P2_5[Fee Routing\n• Route tx fees (PHO) to:\n  – validators\n  – GMA revenue bucket\n• Parameterized splits\n• Accounting entries for GMA seigniorage bucket]

  end

  %% ============================================
  %% P3 – GLYPH MONETARY AUTHORITY (GMA)
  %% ============================================
  subgraph P3[Phase 3 – GMA Core (Photon/Tesseract, Balance Sheet)]
    direction TB

    P3_1[GMA State & Structs\n• Implement GMAState\n  – photonSupply, tesseractSupply\n  – reserves[], risk limits\n  – bondSeries[], facilities\n  – governanceParams, council\n• Invariant checker (Assets - Liabilities = Equity)]

    P3_2[Mint/Burn Guard Rails\n• Only GMA can call PHO.mint/burn\n• Internal functions:\n  – gmaMintPhoton(reason)\n  – gmaBurnPhoton(reason)\n• Logging & invariants on every change]

    P3_3[Reserve Positions\n• addReservePosition(assetClass, currency, qty, custodianRef)\n• updateReserveValuation(reserveId, newValuePHO) from oracle\n• Compute aggregate exposures & check risk limits\n• Helper views for dashboard]

    P3_4[Reserve Deposit/Redemption\n• recordReserveDeposit(depositor, reserveId, valuePHO)\n  – update reserves\n  – mint PHO to depositor (minus fees)\n• recordReserveRedemption(redeemer, reserveId, valuePHO)\n  – burn PHO\n  – adjust reserves\n• Events for each operation]

    P3_5[Open Market Operations (OMO)\n• omoBuyPhoton(amountPHO, maxSlippage)\n  – buy PHO using reserve assets via AMM\n  – burn PHO or hold in GMA account\n• omoSellPhoton(amountPHO, minSlippage)\n  – mint PHO\n  – sell for reserve assets\n• Enforce governance limits (maxOMOAmountPHO)]

    P3_6[Facilities: Deposit & Lending\n• Deposit facility:\n  – openDepositFacility(amountPHO)\n  – accrue interest at depositRateBps\n  – closeDepositFacility() → principal+interest\n• Lending facility:\n  – openLendingFacility(collateral, borrowPHO)\n  – lock collateral (TESS/BONDS/other)\n  – accrue interest at lendingRateBps\n  – closeLendingFacility() & unlock collateral\n• Liquidation hooks (if needed)]

    P3_7[Revenue & Seigniorage\n• ComputeCurrentProfit() from:\n  – OMO PnL\n  – Facility spreads\n  – Fee share from P2_5\n• distributeRevenues():\n  – % to TESS buybacks & burns\n  – % to grow reserves\n  – % to ops budget treasury\n• Events for profit distribution]

    P3_8[Risk Limits & Basket\n• ReserveRiskLimits structure & enforcement\n• targetBasketId & targetInflationBps storage\n• Hooks to oracle basket index\n• Sanity checks: no limit breaches on updates]

  end

  %% ============================================
  %% P4 – BONDS (GlyphBonds)
  %% ============================================
  subgraph P4[Phase 4 – GlyphBond Module]
    direction TB

    P4_1[Bond Series Management\n• BondSeries struct (id, name, coupon, frequency, dates)\n• createBondSeries() restricted to council/governance\n• Query APIs for wallet & dashboard]

    P4_2[Issuance\n• issueBonds(seriesId, buyer, principalPHO)\n  – transfer PHO from buyer to GMA\n  – create BondPosition\n  – update totalIssued, totalOutstanding\n• Secondary trading support later (optional)]

    P4_3[Coupon Engine\n• Schedule coupon dates per series\n• claimCoupon(seriesId) for holder\n  – compute due coupons\n  – pay PHO from GMA\n  – avoid double-claim via checkpoints\n• Aggregate coupon cost into P&L]

    P4_4[Redemption\n• redeemAtMaturity(seriesId)\n  – check maturity\n  – pay principal in PHO\n  – reduce totalOutstanding\n• Edge cases: early redemption rules (if any)]

  end

  %% ============================================
  %% P5 – ORACLES & RESERVES INTEGRATION
  %% ============================================
  subgraph P5[Phase 5 – Oracles & Off-chain Reserve Feeds]
    direction TB

    P5_1[Oracle Framework\n• PriceOracle interface (asset → PHO price)\n• Basket index feed (basketId → value)\n• Governance for whitelisting oracles\n• Staleness & sanity checks]

    P5_2[Reserve Attestations\n• Flow from custodian → chain:\n  – periodic proof of holdings (off-chain docs)\n  – attestation tx to update ReservePosition\n• Standard format for custodianRef & audit trail]

    P5_3[FX & Valuation\n• Convert FIAT/asset valuations → PHO via oracles\n• Aggregate exposures by currency & assetClass\n• Trigger alerts/events on big moves]

    P5_4[Risk Monitoring\n• Continuous checks: maxCryptoPctBps, etc.\n• Emit events when close to limits\n• Optional automatic halts on new risk-increasing ops]

  end

  %% ============================================
  %% P6 – HOLO / QWAVE / QQC BRIDGE
  %% ============================================
  subgraph P6[Phase 6 – Hologram & QWave/QQC Integration]
    direction TB

    P6_1[Tx Types for Holo & Beams\n• TxHoloCommit(container_id, holo_id, tick, revision, hash)\n• TxBeamMetric(container_id, tick, num_beams, sqi_score)\n• Wire into state (holo_state_root, beam_state_root)\n• Minimal storage trees per module]

    P6_2[HoloLedger Module\n• Store (holo_id, container_id, revision, hash)\n• Index by container and block\n• Query API: holo history, last revision\n• Events for devtools]

    P6_3[BeamMetrics Module\n• Store beam metrics per container/tick\n• Simple aggregations for SQI/coherence\n• Hooks for future pricing/QoS]

    P6_4[Chain ↔ Holo Runtime Adapter\n• glyph_chain_bridge\n  – subscribe to chain events\n  – mirror refs into Holo cabinet\n• holo_chain_committer\n  – from devtools/QQC: commit new holo revisions to chain\n• Ensure idempotency & replay safety]

    P6_5[Compute Billing Plumbing\n• Define ComputeMeter contract interface\n  – registerContainer(price_per_unit)\n  – openSession(user, container_id)\n  – consume(units) from QQC runtime\n  – closeSession() settle PHO\n• Connect with PHO payments & GMA fee splits]

  end

  %% ============================================
  %% P7 – WALLETS, UX, OFFLINE/RADIO
  %% ============================================
  subgraph P7[Phase 7 – Wallets, Mobile UX & Radio Mesh Mode]
    direction TB

    P7_1[Wallet Core\n• Seed/keys (BIP32-style) + device binding\n• Accounts for PHO/TESS/Bonds\n• GMA integration (view deposits, loans, bonds)\n• Basic staking UI for TESS]

    P7_2[Account Abstraction & Session Keys\n• Smart wallets for:\n  – spending limits\n  – social recovery\n• Session keys for chat micro-payments\n• Pre-approved templates (e.g. small PHO sends)]

    P7_3[Transactable Document UX\n• Author doc in Glyph browser\n• Compile to doc_hash + on-chain contract\n• Show status: Draft → Active → Executed\n• Integrate PHO payments & signatures]

    P7_4[Radio / Mesh Payment Mode\n• Local ledger on device for PHO balances\n• Device-to-device signed IOUs / transfers\n• Cluster-level consensus (gossip + local finality)\n• Reconciliation protocol when internet returns:\n  – send local tx log to global chain\n  – detect conflicts & apply policy\n• UX: clearly label “local-only” vs “globally-final” PHO]

    P7_5[Mobile Light Client\n• Header sync only + proofs for tx & state\n• Efficient PHO/TESS/Bond balance queries\n• Caching + bandwidth limits\n• Fallback to radio mode when offline]

  end

  %% ============================================
  %% P8 – OBSERVABILITY, GOVERNANCE & TESTNETS
  %% ============================================
  subgraph P8[Phase 8 – Observability, Governance, Testnets]
    direction TB

    P8_1[Explorers & Dashboards\n• Block/tx explorer (basic)\n• GMA dashboard:\n  – PHO supply, TESS supply\n  – reserves composition\n  – bonds outstanding\n  – rates, OMOs, profit distribution\n• Holo/Beam explorer for devs]

    P8_2[Governance Wiring\n• TESS staking → voting power\n• Proposal types:\n  – change rates\n  – change risk limits\n  – change council\n  – recapitalize via TESS\n• Timelocks & emergency powers]

    P8_3[Testnets\n• Local devnet (single-node + mocks)\n• Internal testnet with fake reserves/oracles\n• Public testnet (faucet, explorers)\n• Upgrades & migration rehearsal]

    P8_4[Security & Audits\n• Internal review of GMA invariants\n• External audits for:\n  – core chain modules\n  – PHO/TESS/bonds\n  – GMA & bridge\n• Bug bounty program]

  end

  %% Dependencies
  P0_2 --> P1_2
  P1_2 --> P1_3 --> P1_4 --> P1_5
  P1_3 --> P2_1
  P2_1 --> P3_2
  P2_2 --> P1_5
  P2_3 --> P2_4
  P2_4 --> P3_5
  P1_4 --> P3_1
  P3_1 --> P3_3 --> P3_4 --> P3_5 --> P3_6 --> P3_7
  P3_1 --> P4_1
  P4_1 --> P4_2 --> P4_3 --> P4_4
  P3_3 --> P5_2
  P5_1 --> P3_3
  P5_1 --> P5_3 --> P5_4
  P1_3 --> P6_1
  P6_1 --> P6_2 --> P6_4
  P6_1 --> P6_3 --> P6_5
  P1_5 --> P8_2
  P2_1 --> P7_1
  P3_6 --> P7_1
  P1_3 --> P7_5
  P7_5 --> P7_4
  P1_2 --> P8_1
  P1_2 --> P8_3 --> P8_4



⸻

Quick execution notes

Recommended build order:
	1.	P0 → P1: pick framework, define types, get a bare chain running with PHO/TESS & Bank/Stake.
	2.	P2: wire tokens, AMM, fee routing.
	3.	P3: implement GMA skeleton (mint/burn guard, reserves, facilities) with mocked oracles.
	4.	P4–P5: bonds + real oracle integration + reserve feeds.
	5.	P6: glue chain ↔ Holo/QQC (minimal commit + metrics).
	6.	P7: wallet + mobile + radio-mode plumbing.
	7.	P8: dashboards, testnets, hardening, audits.


