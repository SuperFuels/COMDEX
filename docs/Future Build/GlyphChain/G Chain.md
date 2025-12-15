graph TD
  %% ============================================
  %% P0 – BOOTSTRAP & FOUNDATIONS
  %% ============================================
  subgraph P0[Phase 0 – Repo, Architecture & Foundations]
    direction TB

    P0_1[☐ Project Bootstrapping\n• Monorepo: chain, GMA, wallet, holo-bridge, mesh\n• Languages: Rust/Go node, WASM/EVM contracts\n• Coding standards, CI, env + secrets]

    P0_2[☐ Core Specs & Interfaces\n• Canonical encodings: tx/header/state/proofs (“photon algebra”)\n• ChainState, Account, BlockHeader, Tx\n• Proof formats + verification API contracts\n• PHO/TESS token specs\n• GMA types (reserves, bonds, facilities)\n• MeshReconcile types (LocalBalance, MeshTx, ClusterBlock)\n• Transport interfaces: HTTP gossip + optional QWaveBeamTransport\n• Optional artifact interfaces: hologram/replay traces, resonance receipts]

    P0_3[☐ Node Framework Selection\n• Choose base (Cosmos-SDK/Substrate/custom)\n• Execution (WASM or EVM)\n• GMA & Bonds: modules vs contracts\n• MeshReconcile as chain module\n• Extension points for Holo/QWave/QKD (transport + attestations, not consensus deps)]

    P0_4[☐ Security & Crypto Baseline\n• Sig schemes (ed25519/secp256k1/BLS)\n• Hash/commitments (Merkle now / later KZG)\n• Canonical hashing rules (no JSON ambiguity)\n• Key derivation, wallet seeds, device binding\n• Threat model: online chain + offline mesh\n• QKD as optional transport security layer + audit/attestation hooks]
  end

%% ============================================
%% P1 – CORE CHAIN
%% ============================================
subgraph P1[Phase 1 – Core Chain (Ledger, Consensus, Bank)]
direction TB

P1_1[☐ Consensus & Networking\n• BFT PoS engine\n• Validator sets, epochs, staking hooks\n• Block propagation + proposal channels\n• No public mempool: leader inbox / relay model (anti-DoS)\n• Peer discovery, rate limits, spam controls\n• Transport plugin system:\n  – baseline HTTP/WebSocket\n  – optional QWave Beams as accelerator\n• Optional QKD-secured links (transport-only) + link attestation logs]

P1_2[✅ State & Storage (Dev snapshot + root slice)\n• ChainState snapshot: {config, bank, staking}\n• Deterministic state_root = sha256(canonical(state))\n• Dev endpoints: GET/POST /api/chain_sim/dev/state\n• Import resets explorer ledger (blocks/txs start empty)\n• ✅ bank.accounts sub-root committed under state.bank.root BEFORE hashing state_root\n• ✅ staking sub-roots committed BEFORE hashing state_root:\n  – state.staking.validators_root\n  – state.staking.delegations_root\n• Single source of truth: _get_chain_state_snapshot() commits sub-roots\n• NOTE: No trie, persistence, pruning yet]

P1_2A[✅ Proofs & Light Sync (Mobile-first slice)\n• ✅ Account proof format (Merkle over {address, balances, nonce})\n• ✅ Tx inclusion proofs\n• ✅ Proof endpoints (dev):\n  – GET /api/chain_sim/dev/proof/account\n  – GET /api/chain_sim/dev/proof/tx?tx_id=…\n  – POST /api/chain_sim/dev/proof/verify_account\n  – POST /api/chain_sim/dev/proof/verify_tx\n• ✅ Roots returned by proofs match roots committed in /dev/state\n  – _root_matches_state=True semantics enforced by tests\n• ✅ Perf test 404 distinction implemented for staking delegation proofs:\n  – 404 {"detail":"delegation not found"} => route exists, no leaf\n  – 404 {"detail":"Not Found"} => route not mounted\n• Light client sync flow:\n  – download headers\n  – verify state_root\n  – fetch proofs on-demand]

P1_3[✅ Block & Tx Format (Dev slice)\n• Canonical dev tx envelope: {from_addr, nonce, tx_type, payload}\n• /api/chain_sim/dev/submit_tx is canonical sync entrypoint (routes via tx_executor.apply_tx)\n• ✅ Async ingest + deterministic finalize:\n  – POST /api/chain_sim/dev/submit_tx_async (202 Accepted + qid)\n  – GET  /api/chain_sim/dev/tx_status/{qid}\n  – GET  /api/chain_sim/dev/queue_metrics\n• Dev tx identity: canonical(tx) + sha256 → tx_hash, tx_id\n• Dev ledger/explorer:\n  – /api/chain_sim/dev/blocks\n  – /api/chain_sim/dev/block/{height}\n  – /api/chain_sim/dev/tx/{tx_id}\n  – /api/chain_sim/dev/txs?address=…\n• ✅ Ledger batching is ON for async flushes:\n  – worker calls begin_block() once per flush window\n  – record_applied_tx() appends applied txs into the open block\n  – commit_block() finalizes the batched block\n  – abort_open_block() prevents empty shell blocks\n• Block header commitments (always written per flush):\n  – block.header.state_root\n  – block.header.txs_root (used by /dev/proof/tx)\n• ✅ txs_root is computed once per flush and committed with the block header\n• ✅ Hard rule: failed tx must not advance chain\n  – rejected txs: no ledger record, no tx_id/tx_hash/block_height/tx_index\n  – tx_status still reports rejected/error for observability\n• ✅ Signature/auth pipeline (reject fast at ingest)\n  – tx extended: chain_id + pubkey + signature\n  – CHAIN_SIM_SIG_MODE=off|mock|ed25519\n  – verify at ingest; invalid tx never enters queue/worker\n  – ✅ tests: mock + ed25519 (sync apply + async reject-fast)\n• ☐ Wallets: finalize canonical ed25519 sign-bytes spec + wallet-facing docs\n  – (current dev spec: stable_json({chain_id,from_addr,nonce,tx_type,payload}) UTF-8)\n• NOTE: no gas, production ordering rules yet]

P1_4[✅ Bank Module (Dev correctness slice)\n• BANK_MINT / BANK_SEND / BANK_BURN wired and mutating state\n• Nonce rules enforced (bad nonce rejected, no mutation, no new ledger record)\n• Supply invariants: mint/burn adjust supply, send preserves supply\n• ✅ Dev fee schedule implemented (PHO fixed fee + carve-out mint)\n• ✅ Fee recorded in receipts + persisted in ledger fee column]

P1_4A[✅ ChainSim Dev Bank Slice (Implemented)\n• /api/chain_sim/dev/mint, /dev/transfer, /dev/burn, /dev/account, /dev/supply\n• In-memory AccountState + SupplyState model\n• ✅ test_chain_sim_bank_ops.py updated for PHO fee funding\n• ✅ test_chain_sim_fees.py passing\n• ✅ Perf: test_chain_sim_perf.py measures:\n  – /dev/state\n  – /dev/proof/account (+ root match vs state.bank.root)\n  – /dev/proof/tx + /dev/proof/verify_tx\n• AdminDashboard: ChainSimLedgerPanel renders blocks/txs via /dev/blocks + /dev/txs]

P1_5[✅ Staking Module (Dev slice + proofs)\n• Minimal staking structs: Delegation/Validator/Rewards\n• Dev endpoints: /api/staking/dev/validators, /api/staking/dev/delegations?delegator=…\n• Dev txs: STAKING_DELEGATE / STAKING_UNDELEGATE\n• Bonded pool lock model: TESS moved to pho1-dev-staking-bonded\n• Basic invariants (no negative stake, power=sum(delegations))\n• ✅ Staking proofs implemented + passing tests:\n  – validators_root + delegations_root committed in state snapshot\n  – test_staking_proofs.py ✅]

P1_6[✅ Genesis & Config (dev slice)\n• POST /api/chain_sim/dev/reset clears bank+staking+ledger\n• ✅ Also resets perf caches:\n  – _state_root_reset_cache()\n  – async queue status/metrics cleared (when async enabled)\n• Minimal schema: chain_id/network_id + allocs + validators\n• Genesis seeds state (no blocks)\n• Testable: /dev/supply == sum(allocs), /staking/dev/validators populated]

P1_7[✅ Performance knobs + findings (dev)\n• ✅ Async batching knobs:\n  – CHAIN_SIM_BLOCK_MAX_TX\n  – CHAIN_SIM_BLOCK_MAX_MS\n  → controls block size / flush window (1 flush ≈ 1 block)\n• ✅ Sync state-root policy knob:\n  – CHAIN_SIM_STATE_ROOT_INTERVAL\n  – 1 = recompute per applied tx (sync path)\n  – N = recompute once per N applied txs (sync path)\n• ✅ Invariants validated by ad-hoc tests:\n  – no empty blocks created (abort_open_block works)\n  – /dev/proof/tx verifies and proof.txs_root == block.header.txs_root\n  – ledger contains only applied tx records (no rejected txs in /dev/txs)\n• ✅ Load-test hygiene: run uvicorn without –reload; raised httpx pool limits/timeouts]

P1_8[☐ Persistence + Replay (SQLite/dev first)\n• Persist blocks + txs + header commitments (state_root, txs_root)\n• On startup: replay from genesis snapshot + tx log to rebuild state deterministically\n• Re-run perf sweeps: ingest TPS vs finality TPS + tail latency]

“☐ Runtime acceleration: parallel executor + Rust/Go node for hot paths (sig verify, state updates, networking) to reach 10k+ TPS.”

flowchart TD
A[Goal: world-class throughput + deterministic correctness] –> B[Keep state machine deterministic]
B –> C[Interval=1 collapses at 5k accounts ✅]
C –> D[Make commits block-scoped]

D –> E[Async worker builds blocks (batched flush)]
E –> E1[Env knobs: CHAIN_SIM_BLOCK_MAX_TX, CHAIN_SIM_BLOCK_MAX_MS]
E –> E2[Deterministic ordering: FIFO from ingest queue]
E –> E3[Ledger batching: begin_block → record_applied_tx appends → commit_block]
E –> E4[Compute txs_root once per flush]
E –> E5[Compute state_root once per flush]
E –> E6[Write block header commitments once per flush\n(header.state_root + header.txs_root)]

E6 –> F[Update receipts + status]
F –> F1[/dev/submit_tx_async returns 202+qid ✅]
F –> F2[/dev/tx_status/{qid} lifecycle ✅]
F –> F3[/dev/queue_metrics: TPS + latency + depth ✅]

F3 –> G[✅ Signature/auth pipeline]
G –> G1[Extend tx model: pubkey + signature + chain_id]
G –> G2[CHAIN_SIM_SIG_MODE=off|mock|ed25519]
G –> G3[Verify at ingest; reject fast; never enter worker]
G –> G4[Covered by tests (mock + reject-fast async)]

G4 –> H[☐ NEXT: Persistence + replay]
H –> H1[Persist blocks + txs (SQLite/dev first)]
H –> H2[Replay on startup: rebuild state deterministically]
H –> H3[Re-run sweeps: 5k×2 @ inflight 20/50/100/200]
H –> H4[Compare: ingest TPS vs finality TPS, tails, rejection stability]

H4 –> I[Next levers]
I –> I1[Shorten locks: no snapshot/hash inside critical section]
I –> I2[Persist ledger batches next (already in-memory batched)]
I –> I3[Incremental Merkle/state commitments (no full snapshot rebuild)]
I –> I4[Shard/fair scheduling by sender (future parallelism)]

I4 –> J[Release-grade competitiveness checklist]
J –> J1[Production consensus + cryptography]
J –> J2[Durable storage + replay determinism]
J –> J3[Incremental state commitments + pruning]
J –> J4[Adversarial mempool/DoS design + profiling]

flowchart TB
  %% ============================================
  %% BUILD PLAN – ON-CHAIN ASSETS + APPS
  %% ============================================

  subgraph P0[Foundations / Required for all]
    P0_1[✅ Deterministic async batching + block-scoped roots]
    P0_2[✅ Ledger batching begin_block/commit_block]
    P0_3[☐ Signature/auth pipeline (reject-fast ingest)]
    P0_4[☐ Persistence + replay (SQLite/dev → prod store)]
    P0_5[☐ Indexer hooks (events → search/listings)]
  end

  subgraph D1[Transactable Documents – Chain Integration]
    D1_1[✅ Off-chain doc system exists (AdminDashboard UI)]
    D1_2[☐ Define on-chain DocCommit state: doc_id, owner, rev, content_hash, metadata_hash, timestamps]
    D1_3[☐ Tx types: DOC_COMMIT, DOC_TRANSFER, DOC_REVOKE/ARCHIVE]
    D1_4[☐ Proofs: doc ownership + latest revision inclusion (rooted under state.docs.root)]
    D1_5[☐ API routes: /api/docs/{id}, /api/docs/list, /api/docs/proof, /api/docs/tx...]
    D1_6[☐ Bridge: dashboard “publish/transfer” emits signed tx; off-chain content stored separately]
    D1_7[☐ Tests: commit → transfer → list → proof verifies vs state_root]
  end

  subgraph D2[Escrow – Production-Ready Integration]
    D2_1[✅ Escrow exists (app/dashboard)]
    D2_2[☐ Ensure escrow is a template contract module on-chain (EscrowState in state.escrow)]
    D2_3[☐ Tx types: ESCROW_OPEN, ESCROW_FUND, ESCROW_RELEASE, ESCROW_CANCEL, ESCROW_DISPUTE(optional)]
    D2_4[☐ Asset support: PHO + memetokens + NFTs + docs (escrow can hold “asset refs”)]
    D2_5[☐ Listing primitive: “Offer” = escrow-open with terms + asset refs]
    D2_6[☐ Tests: no chain advance on failure; happy paths; replay-safe idempotency]
  end

  subgraph D3[Meme Tokens]
    D3_1[☐ Choose model: simple multi-denom bank OR token-factory module]
    D3_2[☐ TokenFactoryState: denom, issuer, supply, metadata_hash, mint/burn permissions]
    D3_3[☐ Tx types: TOKEN_CREATE, TOKEN_MINT, TOKEN_BURN, TOKEN_SET_METADATA]
    D3_4[☐ Bank integration: denom registry + balance accounting + fees]
    D3_5[☐ API: /api/tokens/list, /api/tokens/{denom}, /api/accounts/{addr}/balances]
    D3_6[☐ Dashboard: create token + mint + view holders (via indexer)]
    D3_7[☐ Tests: supply invariants, permissions, proof roots (optional), rejection=no ids/heights]
  end

  subgraph D4[Messenger Payments (PHO)]
    D4_1[✅ Messenger exists]
    D4_2[☐ Message → Payment intent schema (thread_id, to, amount, denom, memo/ref)]
    D4_3[☐ Wallet signing: produce signed BANK_SEND (or async submit) from messenger UI]
    D4_4[☐ Status UX: show qid lifecycle + final tx_id/block_height when applied]
    D4_5[☐ Optional: offline acceptance IOU path + reconcile to on-chain send]
    D4_6[☐ Tests: send from messenger path equals normal send; rejection fast w/ bad sig/nonce]
  end

  subgraph D5[NFTs + Asset Listings (Docs + Art + RWAs)]
    D5_1[☐ NFT module state: collections, token_id, owner, metadata_hash, provenance_hash(optional)]
    D5_2[☐ Tx types: NFT_MINT, NFT_TRANSFER, NFT_BURN, NFT_SET_METADATA]
    D5_3[☐ Unified Asset Registry: asset_ref = {kind: DOC|NFT|TOKEN|RWA, id/denom, meta_hash}]
    D5_4[☐ Marketplace primitives: LIST (offer), BUY (escrow fund), SETTLE (escrow release)]
    D5_5[☐ Indexer queries: list assets, list offers, filter by owner/type/price]
    D5_6[☐ Dashboard: “Assets” page (NFTs + Docs) + “Market” page (offers + escrow status)]
    D5_7[☐ Proofs: ownership proofs for NFT + doc refs + offer inclusion
]
  end

  %% Dependencies
  P0_3 --> D4_3
  P0_3 --> D1_6
  P0_3 --> D5_4
  P0_4 --> D5_5
  P0_5 --> D5_5

  D3_4 --> D2_4
  D5_3 --> D2_4
  D1_2 --> D5_3
  D5_1 --> D5_3
  D2_5 --> D5_4



  %% ============================================
  %% P2 – TOKENS & AMM
  %% ============================================
  subgraph P2[Phase 2 – Photon, Tesseract, wGLYPH, AMM]
    direction TB

    P2_1[☐ Photon Token (PHO)\n• Native / ERC20-style module\n• Mint/burn restricted to GMA\n• Transfer/approve/allowance (if ERC20)\n• Fee token integration]

    P2_2[☐ Tesseract Token (TESS)\n• Native/ERC20-style\n• Genesis mint & vesting\n• Hooks for staking/governance\n• Optional fee discounts]

    P2_3[☐ Wrapped Glyph (wGLYPH)\n• Fungible wrapper for bridged GLYPH\n• Mint/burn by BridgeModule\n• Supply tracking + events]

    P2_4[☐ AMM Pools\n• Constant-product pools\n• wGLYPH/PHO, wGLYPH/TESS, PHO/TESS\n• add/removeLiquidity\n• swapExactIn, getReserves\n• Fees (LPs + GMA cut)]

    P2_5[☐ Fee Routing\n• Route PHO fees to:\n  – validators\n  – GMA revenue bucket\n• Config splits\n• GMA seigniorage hooks]
  end

  %% ============================================
  %% P3 – GLYPH MONETARY AUTHORITY (GMA)
  %% ============================================
  subgraph P3[Phase 3 – GMA Core (Photon/Tesseract, Balance Sheet)]
    direction TB

    P3_1[☐ GMA State & Structs\n• GMAState:\n  – photonSupply, tesseractSupply\n  – reserves[], risk limits\n  – bondSeries[], facilities\n  – governanceParams, council\n• Invariant: Assets - Liabilities = Equity]

    P3_1A[✅ GMA Dev Model + Debug API\n• gma_state_model.py (GMAState, ReservePosition)\n• snapshot_dict() invariants in PHO terms\n• dev_gma_state_smoketest.py\n• /api/gma/state/dev_snapshot for admin dashboard\n• In-process singleton _DEV_GMA_STATE shared by dev routes + dashboard]

    P3_2[☐ Mint/Burn Guard Rails\n• GMA-only PHO.mint/burn\n• gmaMintPhoton/gmaBurnPhoton(reason)\n• Logging & invariants per change]

    P3_2A[✅ PHO Mint/Burn Dev Guard Rails\n• gma_mint_photon/_burn in GMAState\n• mint_burn_log with created_at_ms\n• /api/gma/state/dev_mint & /dev_burn\n• Admin dashboard mint/burn log table\n• Hooks used by dev tools to keep GMA snapshot in sync]

    P3_3[☐ Reserve Positions\n• addReservePosition\n• updateReserveValuation via oracle\n• Aggregate exposures & risk checks\n• Dashboard views]

    P3_4[☐ Reserve Deposit/Redemption\n• record_reserve_deposit\n  – update reserves\n  – mint PHO (minus fees)\n• record_reserve_redemption\n  – burn PHO\n  – adjust reserves\n• Events]

    P3_4A[✅ GMA Reserve Deposit/Redemption Dev Model\n• GMAState.record_reserve_deposit/_redemption\n• Equity recompute: Assets - Liabilities\n• dev_gma_reserve_smoketest.py\n• /api/gma/state/dev_reserve_deposit/_redemption (dev)\n• Admin GMA card surfaces reserve events alongside mint/burn]

    P3_5[☐ Open Market Operations (OMO)\n• omoBuyPhoton / omoSellPhoton\n• Use AMM + reserves\n• Governance caps per period\n• PnL tracking]

    P3_6[☐ Facilities: Deposit & Lending\n• DepositFacility + LendingFacility params\n• open/close deposit positions\n• open/repay/close lending positions\n• Collateral factors, thresholds, liquidation\n• Facility spread P&L fields]

    P3_6A[✅ Photon Savings / Term Deposits (Dev)\n• SavingsProduct + SavingsPosition (in-memory)\n• /api/photon_savings/dev/products\n• /dev/deposit, /dev/positions, /dev/redeem\n• Simple interest calc for dashboard prototyping]

    P3_7[☐ Revenue & Seigniorage\n• Profit from:\n  – OMO PnL\n  – Facility spreads\n  – Fee share\n• distributeRevenues:\n  – TESS buyback/burn\n  – grow reserves\n  – ops treasury\n• Events]

    P3_8[☐ Risk Limits & Basket\n• ReserveRiskLimits enforcement\n• targetBasketId, targetInflationBps\n• Basket oracle hooks\n• No limit-breach on update]

    P3_9[✅ Offline Credit Policy (Mesh)\n• OfflineCreditPolicy helper module\n• offline_credit_limit_pho(A) per account\n• Per-device OfflineCreditShard C_{A,D}\n• Invariants: Σ limit_pho(C_{A,D}) ≤ offline_credit_limit_pho(A)\n• used_pho + spendable_local(A,D) wiring\n• Queried by mesh_wallet_state + reconcile]
  end

  %% ============================================
  %% P4 – BONDS (GlyphBonds)
  %% ============================================
  subgraph P4[Phase 4 – GlyphBond Module]
    direction TB

    P4_1[☐ Bond Series Management\n• BondSeries struct\n• createBondSeries (governance-only)\n• Wallet/dashboard queries]

    P4_1A[✅ GlyphBonds Dev Slice\n• In-memory BondSeries + BondPosition\n• /api/glyph_bonds/dev/series, /dev/issue\n• Admin dashboard “Glyph Bonds (dev)” card]

    P4_2[☐ Issuance\n• issueBonds(seriesId, buyer, principalPHO)\n  – transfer PHO → GMA\n  – create BondPosition\n  – update issued/outstanding\n• Optional secondary market]

    P4_3[☐ Coupon Engine\n• Coupon schedule per series\n• claimCoupon(seriesId)\n  – compute due coupons\n  – pay PHO from GMA\n  – checkpointing\n• Feed coupon cost into P&L]

    P4_4[☐ Redemption\n• redeemAtMaturity(seriesId)\n  – maturity checks\n  – pay principal in PHO\n• Early redemption rules (optional)]
  end

  %% ============================================
  %% P5 – ORACLES & RESERVES
  %% ============================================
  subgraph P5[Phase 5 – Oracles & Off-chain Reserves]
    direction TB

    P5_1[☐ Oracle Framework\n• PriceOracle iface (asset → PHO)\n• Basket index feed\n• Oracle whitelisting\n• Staleness & sanity checks]

    P5_2[☐ Reserve Attestations\n• Custodian → chain flow\n• Attestation tx with holdings\n• Standardized custodianRef + audit trail]

    P5_3[☐ FX & Valuation\n• Map FIAT/assets → PHO via oracles\n• Aggregate by currency / asset class\n• Alerts on big moves]

    P5_4[☐ Risk Monitoring\n• Limit checks (maxCryptoPct, etc.)\n• Warning events\n• Optional automatic halts]
  end

  %% ============================================
  %% P6 – HOLO / QWAVE / QQC BRIDGE
  %% ============================================
  subgraph P6[Phase 6 – Hologram & QWave/QQC Integration]
    direction TB

    P6_1[☐ Tx Types for Holo & Beams\n• TxHoloCommit(container_id, holo_id, rev, hash)\n• TxBeamMetric(container_id, tick, num_beams, sqi)\n• Optional: ResonanceReceipt(commit_id, score, trace_hash)\n• Store holo_state_root, beam_state_root\n• Optional: trace_root for deterministic replay artifacts]

    P6_2[☐ HoloLedger Module\n• (holo_id, container_id, rev, hash)\n• Index by container + block\n• Query holo history/latest]

    P6_3[☐ BeamMetrics Module\n• Beam metrics per container/tick\n• Aggregates (SQI/coherence)\n• Pricing/QoS hooks]

    P6_4[☐ Chain ↔ Holo Runtime Adapter\n• glyph_chain_bridge (subscribe events)\n• holo_chain_committer (commit revisions)\n• Idempotent & replay-safe\n• Transport adapters may use QWave beams, but commits remain deterministic]

    P6_5[☐ Compute Billing Plumbing\n• ComputeMeter iface\n  – registerContainer(price/unit)\n  – openSession/consume/closeSession\n• Settle PHO sessions\n• Fee splits to GMA]
  end

  %% ============================================
  %% P7 – WALLETS, UX, OFFLINE/RADIO/BLE
  %% ============================================
  subgraph P7[Phase 7 – Wallets, Mobile UX & Mesh Modes]
    direction TB

    P7_1[☐ Wallet Core\n• Seed/keys (BIP32-style) + device_id\n• Accounts for PHO/TESS/Bonds\n• GMA views (deposits, loans, bonds)\n• Basic TESS staking UX]

    P7_1A[✅ Browser Wallet Panel + Mesh Wiring\n• /api/wallet/balances backend route\n• WalletPanel wired to mesh local_state\n• PHO card: display PHO + offline spendable\n• MeshPending + offlineLimit from mesh_wallet_state\n• Mesh dev send box → /api/mesh/local_send\n• Mesh activity log from /api/mesh/local_state\n• Mesh local_state inspector (dev) in WalletPanel\n• Mini PHO balance pill in TopBar\n• Recent PhotonPay receipts card + refund backend\n• Recent transactable docs list via /transactable_docs/dev/list?party=…]

    P7_2[☐ Account Abstraction & Session Keys\n• Smart wallets: limits, social recovery\n• Session keys for chat/micropayments\n• Pre-approved PHO send templates]

    P7_3[✅ Transactable Document UX\n• Author DC container in Glyph browser\n• Compile to doc_hash + on-chain\n• Status: Draft → Active → Executed\n• PHO payments + signatures]

        %% --- P7_3 Transactable Document UX subtasks ---
        P7_3A[✅Transactable Docs – Glyph / Browser UI\n• GlyphNote-like editor for contracts\n• Show status: Draft → Active → Executed\n• Basic list/detail view of docs]

        P7_3B[☐ Transactable Docs – DC Container + Holo Commit\n• Dev: doc_hash computed & stored in DevTransactableDoc\n• Dev: /transactable_docs/dev/commit_holo → _commit_doc_to_holo stub (holo_container_id/commit_id)\n• TODO: wrap as dc_transactable_doc_v1 (or GlyphNote doc)\n• TODO: real Holo bridge / chain adapter + query by hash/status]

        P7_3C[☐ Transactable Docs – Signatures\n• Signature objects: who/when/what-hash\n• Support multi-party signature policies\n• Enforce: only DRAFT → ACTIVE once signature conditions met\n• Signature audit trail in doc history]

        P7_3D[✅ Transactable Docs – Real PHO Payment Wiring (Dev)\n• PaymentLeg.channel → ESCROW_DEV / PHO_TRANSFER / PHOTON_PAY_INVOICE\n• Escrow legs execute via dev escrow engine\n• Wallet legs hit dev_transfer_pho with balance guard rails\n• Photon Pay legs log real dev receipts\n• Wallet shows recent docs + executed legs per account]

    P7_3A2[✅ Service Escrow Dev Slice\n• EscrowAgreement in-memory model\n• /api/escrow/dev/create, /dev/list\n• /dev/release + /dev/refund\n• Basis for service + liquidity lockups]

    P7_10[✅ Photon Pay: P2P, POS & Invoices\n• Virtual PHO card bound to wallet/device\n• WaveAddress + QR/Glyph codes for addresses\n• Merchant POS keypad: amount + memo → invoice glyph\n• Buyer scan/paste → confirm → pay via NET/RADIO/BLE/mesh\n• P2P send via wave address, messenger, or scan-to-pay\n• Store signed invoice/receipt containers for history & tax]

    P7_10B[✅ Photon Pay: QR / Glyph Scan\n• Dev: POS keypad renders real QR (qrcode.react) for INVOICE_POS payload\n• Dev: buyer panel can paste QR/glyph JSON/base64 and decode into invoice\n• Dev: inline camera “Scan QR” in buyer panel (react-qr-reader/@zxing)\n  → decoded text fed into loadInvoiceFromString(...) + pay flow]

    P7_10C[☐ Photon Pay over NET / BLE\n• Online PHO send over chain (NET)\n• BLE/radio transport adapters\n• Fallback between NET / mesh]
    P7_10D[☐ Photon Pay: Messenger Integration\n• “Pay from chat” in threads\n• Scan-to-pay inside messenger\n• Inline invoice previews + confirm]

    P7_10E[☐ Photon Pay: Signed Invoice/Receipt Containers\n• dc_photon_invoice_v1 / _receipt_v1 dev containers in photon_pay_routes\n• Dev _commit_dc_container_stub → dc_*_commit_* IDs + container_hash\n• TODO: real Holo bridge + on-chain hash\n• TODO: Holo browser doc view + wallet links]

    P7_10 --> P7_10A
    P7_10 --> P7_10B
    P7_10 --> P7_10C
    P7_10 --> P7_10D
    P7_10 --> P7_10E

    P7_10A[✅ Photon Pay Dev Slice\n• Dev invoices + receipts model\n• Wallet receipts card + refund backend (/wallet/dev/refund)\n• Buyer panel NET/mesh pay paths via wallet + mesh engines\n• Invoice expiry + self-pay guardrails\n• Admin recurring mandates + dev routes\n• POS keypad → /photon_pay/dev/make_invoice\n• POS keypad renders real QR (qrcode.react) for INVOICE_POS payload\n• Buyer panel supports paste-string + camera scan → invoice load]

    %% --- Mesh / Radio / BLE payments ---
    P7_4[☐ Radio / Mesh / BLE Payment Mode\n• LocalBalance + LocalTxLog structs\n• MeshTx + ClusterBlock types\n• Local mesh ledger on device\n• MeshReconcile service (ReconcileRequest/Result)\n• Uses offline_credit_limit_pho from GMA\n• Wallet UI: global vs local balances,\n  accepted vs disputed mesh tx]

    P7_4A[✅ Mesh Core Modules (Backend)\n• mesh_types.py (ids, LocalBalance)\n• mesh_tx.py (MeshTx + helpers)\n• mesh_log.py (LocalTxLog)\n• mesh_cluster_block.py (ClusterBlock)\n• mesh_reconcile_service.py\n• mesh_reconcile_routes.py (REST dev stub)\n• dev_mesh_reconcile_smoketest passing]

    P7_4B[✅ GMA Mesh Policy Hook\n• gma_mesh_policy.py (get/set limits)\n• get_offline_limit_pho + get_policy_snapshot\n• MeshReconcile + mesh_wallet_state query this]

    P7_4C[✅ Wallet Mesh State (Backend core)\n• mesh_wallet_state.py helpers\n• LocalBalance + LocalTxLog per (account, device)\n• OfflineCreditShard C_{A,D} + _effective_spendable()\n• record_local_send_for_api() + credit checks\n• /api/mesh/local_state + /api/mesh/local_send\n• /api/wallet/balances: pho, pho_global, pho_spendable_local]

    P7_4_V1[☐ PHO Mesh Payment over BLE (Vertical Slice)\n• Sender wallet builds MeshTx\n• Sign + update LocalTxLog\n• Send via GIPBluetoothAdapter\n• Receiver validates + applies MeshTx\n• Both update LocalBalance\n• Log to GlyphNetDebugger]

    P7_5[☐ Mobile Light Client\n• Header-only sync + proofs\n• Efficient PHO/TESS/Bond queries\n• Caching + bandwidth constraints\n• Auto-switch online ↔ mesh mode\n• Optional transports:\n  – baseline NET\n  – BLE/radio/mesh\n  – optional QWave beams for fast sync]

    P7_6[☐ GlyphNet Viral Bootstrap\n• Minimal “GlyphCore Skeleton” bundle:\n  – core transports (radio/BLE/Wi-Fi Direct)\n  – minimal wallet + mesh ledger\n  – basic photon/glyph codecs\n• D2D sharing via BLE/radio payloads\n• Install/upgrade flow w/o internet\n• Signature check on bundle]

    %% --- Transports + Identity + PTT ---
    P7_7[✅ BLE / Wi-Fi Direct Transport Adapters\n• gip_adapter_ble.py (GIPBluetoothAdapter stub)\n• glyph_transport_switch: 'ble' channel + auto fallback\n• dev_ble_smoketest.py passing]

    P7_8[✅ Wave Addresses & Wave Numbers\n• Extend identity_registry:\n  – WaveAddress (alice@waves.glyph)\n  – WaveNumber (+wave-44-1234-5678)\n• register/lookup by wave_addr & wave_number\n• Messenger uses these to resolve account/device\n  and choose NET/RADIO/BLE]

    P7_9[☐ PTT (Push-to-Talk) over Radio/BLE\n• ptt_session_manager.py (start/end sessions)\n• ptt_packet_codec.py (PTTPacket, audio frames)\n• Extend gip_packet_schema with type 'ptt'\n• Route PTT via glyphnet_router using\n  wave/radio/BLE carriers\n• PTT UI in GlyphNet messenger\n  (press-to-hold, send audio frames)]
  end

  %% ============================================
  %% P8 – OBSERVABILITY, GOVERNANCE, TESTNETS
  %% ============================================
  subgraph P8[Phase 8 – Observability, Governance, Testnets]
    direction TB

    P8_1[☐ Explorers & Dashboards\n• Block/tx explorer\n• Proof explorer (verify proofs client-side)\n• Replay/hologram trace viewer (dev)\n• GMA dashboard: PHO/TESS, reserves,\n  bonds, rates, OMOs, revenues\n• Holo/Beam explorer\n• MeshReconcile/cluster stats]

    P8_2[☐ Governance Wiring\n• TESS staking → voting power\n• Proposal types:\n  – rates, risk limits\n  – council, recap rules\n  – offline_credit_limit policies\n• Timelocks & emergency powers]

    P8_3[☐ Testnets\n• Local devnet with mocks\n• Internal testnet (fake reserves/oracles)\n• Public testnet (faucet, explorers)\n• Upgrade/migration rehearsals\n• Light-client conformance tests (roots + proofs + replay)]

    P8_4[☐ Security & Audits\n• Internal invariant review (GMA + mesh)\n• External audits:\n  – core chain modules\n  – proofs/light-client correctness\n  – PHO/TESS/bonds\n  – GMA, MeshReconcile, bridges\n• Bug bounty program]
  end

  %% Dependencies
  P0_2 --> P1_2
  P1_2 --> P1_2A --> P1_3 --> P1_4 --> P1_5
  P1_3 --> P2_1
  P2_1 --> P3_2
  P2_2 --> P1_5
  P2_3 --> P2_4
  P2_4 --> P3_5
  P1_4 --> P3_1
  P3_1 --> P3_3 --> P3_4 --> P3_5 --> P3_6 --> P3_7 --> P3_8 --> P3_9
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
  P3_9 --> P7_4
  P1_3 --> P7_5
  P7_5 --> P7_4
  P7_4 --> P7_6
  P1_2 --> P8_1
  P1_2 --> P8_3 --> P8_4

If you want it tracked, we can add something like:
	•	P7_4_V1 – PHO mesh payment over BLE (end-to-end slice)
	•	Sender wallet → MeshTx construction
	•	BLE GIP adapter send/recv
	•	Local ledger update on both devices
	•	Logging + debug view in GlyphNetDebugger

Say the word and I’ll write that slice out in full (packet shapes + function calls) next

  Key bits that changed vs your original:
  • New GMA hook: P3_9 Offline Credit Policy ties the grown-up monetary side to the mesh mode (limits, risk, governance).
  • P7_4 expanded to explicitly cover Radio + BLE + Wi-Fi Direct, using the MeshTx / LocalBalance / ClusterBlock / ReconcileRequest/Result types you pasted.
  • P7_6 added for viral GlyphNet bootstrap: minimal skeleton bundle shared D2D when the internet is dead.
  • Everything is wired so that:
  • Online = normal PHO on-chain.
  • Offline = PHO_local claims with bounded risk + later reconciliation.
  • Transports are adapters under GlyphNet (radio/BLE/Wi-Fi Direct), not separate chains.



Below is a code-level build checklist just for:
  • P7_4 Mesh payments + MeshReconcile, and
  • BLE / Wi-Fi Direct transport, including:
  • GlyphNet messenger (browser + backend),
  • wave addresses (email-style IDs),
  • wave numbers (phone-style IDs),
  • PTT (push-to-talk) over radio/BLE.

⸻

1) Mesh Payments & Reconciliation Layer (backend)

1.1 New mesh core types

New dir: backend/modules/mesh/

Files:
  1.  backend/modules/mesh/mesh_types.py
  • Implement the types you already specced:



# identifiers
DeviceId = str
AccountId = str
ClusterId = str

class LocalIdentity(TypedDict):
    device_id: DeviceId
    primary_account: AccountId

class LocalBalance(TypedDict):
    account: AccountId
    global_confirmed_pho: str
    local_net_delta_pho: str
    offline_credit_limit_pho: str
    safety_buffer_pho: str


  2.  backend/modules/mesh/mesh_tx.py


class MeshTx(TypedDict):
    mesh_tx_id: str
    cluster_id: ClusterId
    from_account: AccountId
    to_account: AccountId
    amount_pho: str
    created_at_ms: int
    prev_local_seq: int
    sender_device_id: DeviceId
    sender_signature: str


  3.  backend/modules/mesh/mesh_log.py

  class LocalTxLog(TypedDict):
    account: AccountId
    entries: list[MeshTx]
    last_seq: int


  4.  backend/modules/mesh/cluster_block.py
class ClusterBlock(TypedDict):
    cluster_id: ClusterId
    height: int
    prev_block_hash: str
    txs: list[MeshTx]
    hash: str
    notary_device_id: DeviceId
    notary_signature: str



1.2 MeshReconcile service
  5.  backend/modules/mesh/mesh_reconcile_service.py
  • Implement:  


class ReconcileRequest(TypedDict):
    account: AccountId
    device_id: DeviceId
    last_global_block_height: int
    local_mesh_blocks: list[ClusterBlock]  # or compressed form

class ReconcileResult(TypedDict):
    account: AccountId
    accepted_local_delta_pho: str
    disputed_mesh_tx_ids: list[str]
    settlement_tx_hash: str | None



  • Functions:
  • compute_local_delta(req) -> Decimal
  • detect_conflicts(req, chain_state, offline_limit) -> list[MeshTx]
  • apply_policy(...) -> ReconcileResult (respect per-account offline_credit_limit_pho from GMA).

  6.  backend/modules/mesh/mesh_reconcile_routes.py
  • REST / gRPC entrypoints used by wallet / browser:
  • POST /mesh/reconcile → ReconcileResult
  • GET /mesh/limits/{account} → returns offline limits from GMA.

1.3 GMA → Mesh policy hook
  7.  Modify backend/modules/gma/gma_state.py (or wherever GMA structs live):
  • Add per-account limits:  



class OfflineCreditPolicy(TypedDict):
    default_limit_pho: str
    per_account_overrides: dict[AccountId, str] 


  • Add to main GMAState:

offline_credit_policy: OfflineCreditPolicy




  8.  New module: backend/modules/gma/gma_mesh_policy.py
  • get_offline_limit(account) -> Decimal
  • set_offline_limit(account, new_limit) -> None (governance-gated)
  • Used by mesh_reconcile_service and wallet APIs.

⸻

2) BLE / Wi-Fi Direct Transports for GlyphNet

You already have:
  • gip_adapter_wave.py
  • gip_adapter_net.py
  • gip_adapter_http.py
  • glyph_transport_config.py
  • glyph_transport_switch.py
  • glyphnet_transport.py
  • glyph_transmitter.py
  • glyph_receiver.py

We’ll mirror those for BLE / Wi-Fi Direct.

2.1 GIP BLE adapter (backend)
  9.  New file: backend/modules/glyphnet/gip_adapter_ble.py
  • Interface-compatible with gip_adapter_wave.py:


class GIPBluetoothAdapter:
    def __init__(self, device_id: str | None = None):
        ...

    async def send_packet(self, packet: GIPPacket) -> None:
        """Serialize and send over BLE link to nearby peers."""

    async def receive_loop(self, on_packet: Callable[[GIPPacket], Awaitable[None]]) -> None:
        """Listen for BLE frames, decode to GIPPacket, callback."""

    async def scan_peers(self) -> list[DeviceId]:
        ...

    async def close(self) -> None:
        ...



• Stub out actual OS BLE integration behind a small native shim so we can mock in dev.

  10. Optional: backend/modules/glyphnet/gip_adapter_wifi_direct.py
  • Same interface; transport using Wi-Fi Direct (or local TCP hotspot).

2.2 Transport config & switch
  11. Modify backend/modules/glyphnet/glyph_transport_config.py

  • Extend carrier types:


CARRIER_BLE = "BLE"
CARRIER_WIFI_DIRECT = "WIFI_DIRECT"


  • Add defaults:


DEFAULT_CARRIERS = ["RADIO", "BLE", "NET"]


  12. Modify backend/modules/glyphnet/glyph_transport_switch.py

  • Map new carriers:


from backend.modules.glyphnet.gip_adapter_ble import GIPBluetoothAdapter
from backend.modules.glyphnet.gip_adapter_wifi_direct import GIPWiFiDirectAdapter

def get_adapter(carrier: str):
    if carrier == "BLE":
        return GIPBluetoothAdapter()
    if carrier == "WIFI_DIRECT":
        return GIPWiFiDirectAdapter()
    ...



  13. Modify backend/modules/glyphnet/glyphnet_transport.py

  • Update routing so any GlyphNetPacket can be sent via RADIO | BLE | WIFI_DIRECT depending on:
  • user preference,
  • availability (online/offline),
  • message type (payments / chat / PTT).



⸻

3) Wallet & Messenger Integration (browser / webapp)

3.1 Wallet: local mesh state
  14. New backend module: backend/modules/wallet/mesh_wallet_state.py

  • Mirror LocalBalance, LocalTxLog, plus helper functions:


  def apply_mesh_tx(balance: LocalBalance, tx: MeshTx) -> LocalBalance: ...
def effective_spendable_local(balance: LocalBalance) -> Decimal: ...




  15. Front-end (Next.js / browser): add a Mesh wallet store (e.g. Zustand or Redux):

  • globalConfirmedPho
  • localNetDeltaPho
  • offlineLimitPho
  • meshTxLog[]
  • clusterBlocks[]
  • Methods:
  • enterMeshMode()
  • recordLocalSend()
  • recordLocalReceive()
  • syncAndReconcile() (call backend /mesh/reconcile).

3.2 Wave addresses + wave numbers
  16. Backend type registry: backend/modules/glyphnet/identity_registry.py (you already have something similar) → extend:



class WaveAddress(TypedDict):
    wave_addr: str  # e.g. "alice@waves.glyph"
    account: AccountId
    device_id: DeviceId
    created_at: float


class WaveNumber(TypedDict):
    wave_number: str  # e.g. "+wave-44-1234-5678"
    account: AccountId
    region: str
    device_id: DeviceId




  • Add:
  • register_wave_address(account, preferred_handle)
  • lookup_by_wave_addr(wave_addr)
  • lookup_by_wave_number(wave_number)

  17. Front-end:

  • Modify GlyphNet messenger contact list to show:
  • WaveAddress (email-like) as primary handle.
  • WaveNumber as “call/voice/PTT” handle.
  • When composing:
  • If user types a wave address → resolve to account + device → choose best transport (NET / RADIO / BLE).
  • If they tap a wave number → open PTT session (below).

⸻

4) PTT (Push-to-Talk) over Radio & BLE

4.1 Backend: PTT session manager
  18. New module: backend/modules/ptt/ptt_session_manager.py   



class PTTSession(TypedDict):
    session_id: str
    caller: AccountId
    callee: AccountId
    started_at: float
    transport: str  # "RADIO" | "BLE"
    codec: str      # e.g. "opus-low"  


  • Methods:
  • start_session(caller, callee, transport) -> PTTSession
  • end_session(session_id)
  • handle_audio_chunk(session_id, chunk_bytes)

  19. New module: backend/modules/ptt/ptt_packet_codec.py

  • Define PTTPacket (wrapped into GlyphNet / GIP):


 class PTTPacket(TypedDict):
    session_id: str
    seq: int
    codec: str
    payload: bytes  # compressed audio chunk
    ts: int     



  • Functions:
  • encode_audio_frame(raw_pcm) -> PTTPacket
  • decode_audio_frame(packet) -> raw_pcm

  20. Wire into GlyphNet:

  • Extend gip_packet_schema.py to add a type: "ptt" variant.
  • Modify glyphnet_router.py to route PTTPacket via:
  • gip_adapter_wave (radio),
  • gip_adapter_ble (BLE).

4.2 Front-end: PTT UI + audio
  21. Browser / desktop GlyphNet UI:

  • Add a PTT button to chat/messenger:
  • On press:
  • open mic,
  • encode into small audio frames,
  • wrap as PTTPacket → send via active transport (priority: BLE > RADIO > NET).
  • On release:
  • close session or mark as pause.

  22. Mobile (when you get native wrapper):

  • Equivalent PTT UI, but audio pipeline uses OS audio APIs.
  • Transport chosen by availability:
  • online → normal WebSocket/NET,
  • offline → RADIO / BLE.

⸻

5) “Update current stack to use BLE” – concrete tasks

Here’s a compact task list just for BLE + mesh + PTT updates to existing code:
  1.  Transport adapters
  • Add gip_adapter_ble.py (GIPBluetoothAdapter).
  • (Optional) Add gip_adapter_wifi_direct.py.
  • Extend glyph_transport_config.py with BLE, WIFI_DIRECT.
  • Extend glyph_transport_switch.py to return BLE/Wi-Fi adapters.
  • Update glyphnet_transport.py to allow multiple active carriers.
  2.  Mesh payments
  • Add mesh_types.py, mesh_tx.py, mesh_log.py, cluster_block.py.
  • Add mesh_reconcile_service.py + mesh_reconcile_routes.py.
  • Add gma_mesh_policy.py, extend GMA state with offline credit policy.
  • Add wallet mesh store (front-end) + backend mesh_wallet_state.py.
  3.  Messenger & identity
  • Extend identity_registry.py with WaveAddress + WaveNumber.
  • Update GlyphNet messenger UI to use wave addresses & wave numbers.
  • Teach messenger to pick carrier: NET vs RADIO vs BLE depending on online status & user choice.
  4.  PTT
  • Add ptt_session_manager.py & ptt_packet_codec.py.
  • Extend gip_packet_schema.py for type: "ptt".
  • Route PTT packets through glyphnet_router.py via radio/BLE.
  • Implement PTT UI (press-to-hold) in browser/app using existing GlyphNet messenger panel.

If you like, next step I can pick one vertical slice (e.g. “PHO mesh payment over BLE between two nearby phones”) and write it as a full end-to-end flow: exact packet shapes, which functions fire in which module, and what you’d log where.

