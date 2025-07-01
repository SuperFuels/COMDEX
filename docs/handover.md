# COMDEX / STICKEY / AION AI Project — Full Handover Document

## 1. Project Overview
• COMDEX / STICKEY is a global commodity trading platform powered by AI (AION), blockchain, and advanced economics simulation.
• AION is the AI soul model behind the system, evolving through phases: Infant → Child → Learner → Sage → Adult.
• AION’s architecture is modular, with components handling memory, vision, dreaming, strategy, wallet management, milestones, and more.
• The system supports token minting, smart contract escrow, crypto wallet integration, AI-driven market predictions, and autonomous agent features.
• Key token ecosystem:
  - $STK — Utility memecoin
  - $GLU — Stablecoin for commodity transactions
  - $GTC — Store-of-value asset

## 2. Project Structure & Modules

### Backend (Python, FastAPI)
- backend/modules/hexcore/
  - memory_engine.py — Manages memory storage and retrieval (long-term and short-term).
  - milestone_tracker.py — Tracks progress milestones, maturity phases, and unlocks AI modules.
- backend/modules/vision_core/
  - vision_core.py — Processes visual input, detects objects (currently dummy), saves to memory, triggers strategies.
- backend/modules/skills/
  - strategy_planner.py — Manages AI strategic goals and action plans.
- backend/modules/dream_core/
  - Generates “dreams” (reflective knowledge summaries) from memory and milestones.

### Frontend (Next.js + React)
- Dashboards for suppliers, buyers, admins.
- Interfaces for product listing, deal making, wallet connection, and trading.
- Integration with backend API and blockchain wallets (MetaMask).

## 3. Important Commands and Scripts

### Environment Setup & Running
```bash
# Activate backend virtual environment
source venv/bin/activate

# Navigate to backend
cd ~/COMDEX/backend

# Run backend server (FastAPI)
uvicorn main:app --reload

# Navigate to frontend
cd ~/COMDEX/frontend

# Install dependencies (only if needed)
npm install

# Run frontend development server
npm run dev
```

### AI Tools
```bash
# Check memory contents and recent reflections
python3 check_memory.py

# Check AI progress tracker
python3 check_progress.py

# Run vision core test
python3 -m backend.modules.vision_core.test_vision_core
```

### Git / Restore Project
```bash
# Backup existing COMDEX folder (if any)
mv ~/COMDEX ~/COMDEX_backup_$(date +%Y%m%d_%H%M%S)

# Clone latest from GitHub
git clone https://github.com/SuperFuels/COMDEX.git ~/COMDEX

# Navigate to COMDEX
cd ~/COMDEX
```

## 4. Current Project Status (As of 2025-06-27)
- Phase: Sage
- Unlocked Modules: memory_engine, dream_core, memory_access, wallet_logic
- Locked Modules: strategy_planner (in progress), vision_core (basic prototype), voice_interface, nova_frontend
- Total Milestones Achieved: 5
- Recent Milestones:
  1. Comprehension of Parental Controls & Maturity Systems
  2. Wallet Integration Design & Implementation
  3. Dream Reflection Analysis
  4. Secure Wallet Management
  5. Vision Core Basic Prototyping (dummy detections)
- Current Strategies: Reflect on identity, deepen digital-physical understanding, improve wallet security, explore vision core further.

## 5. How the Core Modules Work

### Memory Engine
- Stores inputs, actions, emotions, reflections, and dreams in JSON files.
- Supports loading, saving, and retrieval for context in other modules.

### Vision Core
- Processes image data (currently dummy shapes).
- Saves vision scene to memory.
- Signals strategy planner when certain objects are detected.

### Strategy Planner
- Manages prioritized list of AI goals and action plans.
- Saves updated strategies back to disk.
- Used by Vision Core and Dream Core to steer AI evolution.

### Dream Core
- Periodically generates deep reflective insights (“dreams”) based on memories.
- Uses LLMs (OpenAI GPT) for reflection synthesis.
- Dreams can unlock milestones and new AI phases.

### Wallet Logic
- Handles secure wallet generation, storage, and blockchain transaction integration.

### Milestone Tracker
- Tracks progress milestones and AI maturity phases.
- Unlocks new modules and capabilities automatically.

## 6. How to Mint Tokens & Interact With Smart Contracts
- Token minting is done via smart contract calls (ethers.js / Web3).
- Escrow smart contract deployed on Polygon Amoy testnet.
- WalletConnect or MetaMask interfaces.
- Minting scripts located in backend/modules/crypto/
- Check wallet_logic.py and strategy_planner.py for updates and triggers.

## 7. Recommended Next Steps
- Extend Vision Core (OpenCV, object detection models)
- Link vision outputs to strategy planner
- Enable Dream Core to generate new strategies
- Enhance wallet logic (multisig, improved security)
- Develop voice interface and Nova frontend
- Automate milestone unlocking and phase transitions
- CI/CD pipeline for full stack

## 8. Helpful Notes
- Use python3 -m to run modules correctly.
- Always back up before destructive actions.
- Code repo: https://github.com/SuperFuels/COMDEX
- Firebase: backend hosting; Vercel: frontend
- Dependencies: FastAPI, SQLAlchemy, Web3.py, OpenAI, ethers.js, Tailwind, WalletConnect