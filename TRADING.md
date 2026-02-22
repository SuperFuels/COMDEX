AION Trading Intelligence System

	2.	Complete LLM weighting + synthesis
	•	tracking + weighted consultation + disagreement rules
	3.	Close Phase 2 gaps
	•	hard invariant enforcement + scoring separation + paper runtime integration
	4.	Close Phase 1 measurement gaps
	•	DMIP artifacts + analysis accuracy tracking + debrief discipline
	5.	Run evidence gates
	•	collect enough logs/trades to prove improvement/compliance
	6.	Then Phase 4 expansion
	7.	Then Phase 5 CIM integration
	8.	Then Phase 6 controlled live
 
flowchart TD

%% =========================================================
%% AION Trading Intelligence v1 - Build Task Mermaid Checklist
%% Status legend in labels: [x] done, [ ] todo
%% =========================================================

ROOT["AION Trading Intelligence v1<br/>Build Task Checklist to Completion"]

ROOT --> DONE
ROOT --> P1
ROOT --> P2
ROOT --> P3
ROOT --> P4
ROOT --> P5
ROOT --> P6
ROOT --> CROSS

%% -------------------------
%% DONE / CONFIRMED
%% -------------------------
subgraph DONE["✅ Confirmed Complete (Current)"]
D1["[x] Trading orchestrator routing tests passing"]
D2["[x] Decision influence parser tests added + passing"]
D3["[x] show decision influence weights → action=show"]
D4["[x] increase ... influence by ... dry run → delta patch parse"]
D5["[x] set ... to ... → set op parse"]
D6["[x] apply live → dry_run=False parse"]
D7["[x] Targeted pytest runs for decision-influence parser tests passing"]
D8["[x] Full backend/tests/test_aion_trading_orchestrator_routing.py passing (20/20)"]
end

%% -------------------------
%% PHASE 1
%% -------------------------
subgraph P1["Phase 1 — Analysis Intelligence First (No Trading)"]
P1A["[ ] Define stable schemas: price snapshots, news digest items, econ calendar events, session summaries, bias sheets, debrief records"]
P1B["[ ] DMIP ingestion basics finalized (with degraded-mode handling)"]
P1C["[ ] Data quality / stale-input trace+debug flags"]
P1D["[ ] Persist ingestion timestamps + recency metadata"]

P1E["[ ] DMIP core skills operational:
- run_morning_briefing()
- generate_daily_bias_sheet()
- run_session_analysis(session) (start London)
- run_mid_session_review(session, open_trades)
- run_eod_debrief(daily_trades, daily_bias_sheet)"]
P1F["[ ] Persist DMIP outputs as artifacts (not only response text)"]

P1G["[ ] Implement DMIP checkpoints:
06:00 Pre-market, 07:45 London pre-open, 10:00 Mid-London, 13:30 NY pre-open, 22:30 Asia prep, 22:00 EOD debrief"]
P1H["[ ] Each checkpoint outputs structured plans/bias/go-no-go/avoid lists"]

P1I["[ ] Red/Amber event protocols (NFP, CPI, rates, CB remarks, PMI, GDP, ADP, etc.)"]
P1J["[ ] Event behavior enforcement:
consensus/prior/revisions, 'priced-in' framing, no-trade windows, post-event wait, follow-through only"]

P1K["[ ] Multi-LLM verification workflow:
AION-first → Claude → GPT → compare/synthesise"]
P1L["[ ] Early-stage disagreement rule:
material Claude/GPT conflict ⇒ AVOID (unless later governed override)"]
P1M["[ ] Persist LLM consult outputs + disagreements for audit"]

P1N["[ ] Analysis learning logs (log_analysis_record)"]
P1O["[ ] Analysis record stores: saw/concluded/why/trade-allowed?/what happened/critique"]
P1P["[ ] Analysis score separation present:
process_score, outcome_score, rule_compliance_score, context_quality_score, reward_score"]
P1Q["[ ] Analysis accuracy tracking by pair/session/event"]

P1R["[ ] Phase 1 success gate:
30–60 days bias/debrief logs, measurable analysis improvement, stable data/schema pipelines"]
end

%% -------------------------
%% PHASE 2
%% -------------------------
subgraph P2["Phase 2 — Paper Trading (Single Pair, Single Strategy)"]
P2A["[ ] Paper execution runtime implemented (paper-only authorization boundary)"]
P2B["[ ] submit_paper_trade / manage_open_trade / close_trade implemented"]

P2C["[ ] Scope lock enforced:
EUR/USD only + London only + SMC Intraday (15m)"]
P2D["[ ] Execution progression enforced: analysis-only → paper-trading → no live"]
P2E["[ ] Initial trade limits enforced:
max 1–2 trades/session, A-grade only, strict event filters, mandatory EOD debrief"]

P2F["[ ] Risk invariants hard gates implemented (absolute, non-learnable)"]
P2G["[ ] Position sizing invariants:
1% trade / 3% daily / 6% weekly / stop-distance sizing / no size-up in drawdown / no averaging down"]
P2H["[ ] Stop-loss invariants:
stop at entry / structural stops / trail only toward profit / never widen / reject >1% valid stop"]
P2I["[ ] TP/Exit invariants:
min RR 1:2 / preferred 1:3+ / BE at 1:1 (strategy-dependent) / partials structured"]
P2J["[ ] Session rules:
max 3 losers/session, stop-on-daily-loss, restricted open-minute windows, red-event stand-down, late-Friday protection"]
P2K["[ ] Account protection:
10% max drawdown stop + mandatory review before resume"]

P2L["[ ] Risk validation skill enforced as hard gate:
validate_risk_rules(trade_proposal)"]
P2M["[ ] Safe defaults preserved (paper mode default) + explicit reject reasons logged"]

P2N["[ ] Tier 3 SMC Intraday strategy module operational (15m)"]
P2O["[ ] Pattern coverage:
liquidity sweep + CHoCH + return / order block retest / FVG fill / session timing confluence"]
P2P["[ ] Strategy outputs structured thesis:
evidence + invalidation + risk proposal + confidence + no-trade rationale"]

P2Q["[ ] Trade logging + full lifecycle persistence:
proposal / validation / execution / management actions / close / final result"]
P2R["[ ] Score separation for trades:
process_score, outcome_score, rule_compliance_score, context_quality_score, execution_quality_score, reward_score"]

P2S["[ ] Phase 2 success gate:
~100 paper trades, positive/improving expectancy, high rule compliance, zero invariant violations"]
end

%% -------------------------
%% PHASE 3
%% -------------------------
subgraph P3["Phase 3 — LLM Weighting + Governed Learning Influence"]
P3A["[ ] LLM task-specific performance tracking (log_llm_accuracy)"]
P3B["[ ] Track by pair/session/event type/directional bias/level prediction/reaction interpretation"]
P3C["[ ] Accuracy summaries available for weighting"]

P3D["[ ] Weighted consultation synthesis implemented (synthesise_llm_responses + get_llm_weighted_bias)"]
P3E["[ ] Disagreement remains a signal (not suppressed)"]
P3F["[ ] Weighting changes confidence/filtering only (not risk invariants)"]

P3G["[ ] Governed decision influence writes (Sprint 3 / Phase D) fully runtime-hardened"]
P3H["[ ] Allowed writes only:
setup confidence, stand-down sensitivity, pair/session preferences, LLM trust weights, event caution multipliers"]
P3I["[ ] Forbidden writes blocked:
risk invariants, max loss/sizing rules, auth gates, autonomous live enablement"]

P3J["[ ] update_decision_influence_weights runtime complete (beyond parser tests)"]
P3K["[ ] Supports: show, update, dry_run default True, apply/live path with auth guard"]
P3L["[ ] Patch validation schema:
set/delta ops + allowed keys only"]
P3M["[ ] Decision influence writes persisted + versioned + auditable"]
P3N["[ ] Pre/post snapshots logged; rollback/revert path defined"]

P3O["[ ] Decision influence capture/journal integration"]
P3P["[ ] Non-breaking capture failure behavior maintained"]
P3Q["[ ] Debug/metadata contract stable:
trading_journal + journal summaries + trading_capture_result"]

P3R["[ ] Phase 3 success gate:
improved filtering, fewer false positives, no risk-rule drift, auditable governed updates"]
end

%% -------------------------
%% PHASE 4
%% -------------------------
subgraph P4["Phase 4 — Strategy Expansion (Breadth After Proof)"]
P4A["[ ] Expansion order locked and followed:
1) Momentum/ORB (London/NY)
2) More majors
3) Asia (JPY/AUD focus)
4) Swing
5) Order-flow sniping (if infra supports)"]

P4B["[ ] Strategy isolation:
separate performance tracking, separate learning stats, separate expectancy by pair/session/setup"]
P4C["[ ] No cross-strategy weight contamination without explicit governance"]

P4D["[ ] Momentum/ORB module implemented:
ORB breakout+retest, momentum pullbacks (EMA/VWAP), HTF alignment, breakout failure invalidation"]
P4E["[ ] Additional majors unlocked pair-by-pair with evidence gates"]
P4F["[ ] Pair-specific spread/volatility/event sensitivity tracking"]

P4G["[ ] Asia session rollout:
timing logic, liquidity windows, JPY/AUD suitability, no-go conditions, session-specific performance tracking"]

P4H["[ ] Swing strategy rollout:
structural break + first pullback, weekly/monthly levels, macro filter integration when available, multi-day management"]

P4I["[ ] Order-flow sniping later unlock only:
provider quality validated, spread checks, no first-2-minute open execution, pattern coverage (absorption/delta divergence/imbalances/etc.)"]
end

%% -------------------------
%% PHASE 5
%% -------------------------
subgraph P5["Phase 5 — Macro Chessboard / Country Intelligence Matrix (CIM)"]
P5A["[ ] Country scorecard schema + evidence bundle schema defined"]
P5B["[ ] Country dimensions implemented with weight/confidence/recency:
CB stance, inflation, growth, fiscal/debt, trade health, geopolitics, leadership quality proxy, sentiment trajectory, capital flow proxy, commodity sensitivity, stability/uncertainty"]

P5C["[ ] 4D time features implemented:
level, velocity, acceleration, confidence/evidence quality, recency decay"]

P5D["[ ] CIM skills implemented:
update_country_scorecard
calculate_country_composite
compute_country_score_velocity
calculate_pair_macro_spread
run_macro_chessboard_review
generate_macro_pair_priority_sheet"]

P5E["[ ] Pair macro spread logic explainable + confidence-aware"]
P5F["[ ] CIM used as:
directional filter, confidence modifier, contradiction stand-down trigger, swing/macro input"]

P5G["[ ] Daily/weekly LLM macro discussion loop operational:
what changed / second-order impacts / exposed pairs"]
P5H["[ ] Persist macro consultations + weekly/monthly macro theme summaries"]
end

%% -------------------------
%% PHASE 6
%% -------------------------
subgraph P6["Phase 6 — Controlled Live Exposure (Much Later)"]
P6A["[ ] Live exposure unlock criteria defined and audited (paper performance + governance proof first)"]
P6B["[ ] Tiny-size live mode only (initial)"]
P6C["[ ] Human approval gates required"]
P6D["[ ] Hard kill switch implemented + tested"]
P6E["[ ] No autonomous risk-rule changes possible"]
P6F["[ ] Live-vs-paper separation, audit trails, and rollback plans documented"]
end

%% -------------------------
%% CROSS-CUTTING / MUST-STAY-TRUE
%% -------------------------
subgraph CROSS["Cross-Cutting Locks (Must Remain True Across All Phases)"]
C1["[ ] Process quality scored separately from outcome quality"]
C2["[ ] Risk management remains invariant (learning cannot rewrite hard rules)"]
C3["[ ] AION analyses before it trades"]
C4["[ ] LLMs are challengers/referees/debriefers (not unquestioned authorities)"]
C5["[ ] LLM disagreement treated as a signal"]
C6["[ ] Layered unlocks only (no jumping ahead)"]
C7["[ ] No live autonomous trading in early phases"]
C8["[ ] No unrestricted strategy self-modification"]
C9["[ ] No risk invariant mutation"]
C10["[ ] No broad multi-pair/multi-strategy rollout before evidence"]
C11["[ ] Persistent artifacts stored:
daily intelligence, trade artifacts, learning artifacts, CIM artifacts"]
C12["[ ] Auditability everywhere:
decision traces, journal summaries, LLM disagreements, weight updates, invariant rejects"]
end









_______________________________________________

Final Implementation Blueprint (v1)

Purpose: Build AION into a governed, learning trading intelligence (not a bot) that can analyse markets, generate structured trade theses, execute in paper trading under hard risk rules, and improve via reinforcement + LLM critique.

Core loop:
Ingest → Analyse → Conclude → (Paper) Execute → Observe → Debrief → Reinforce → Improve

⸻

1) What AION Is (and Is Not)

AION is
	•	A multi-layered trading intelligence
	•	A governed decision system
	•	A learning architecture that improves from outcomes and critique
	•	A discipline engine that executes risk rules consistently
	•	A macro + intraday reasoning system

AION is not
	•	A fixed-rule forex bot
	•	A single-strategy EA
	•	An HFT engine (microsecond competition)
	•	A live autonomous trader (early phases)

⸻

2) Final System Architecture (the actual stack)

This is the stack we implement, top to bottom:

Layer A — Macro Chessboard / Country Intelligence Matrix (CIM)

Top-level world model (country-by-country weighted scoring) that creates pair-level directional probability and regime context.

Layer B — DMIP (Daily Market Intelligence Protocol)

Multi-checkpoint session intelligence and LLM-verified briefings (pre-market, London, NY, Asia, EOD debrief).

Layer C — Strategy Engines

Execution logic by timeframe/type:
	•	SMC intraday
	•	Momentum / ORB
	•	Order flow (HFT-adjacent)
	•	Swing
	•	Macro positioning (context/filter layer)

Layer D — Risk Invariants (Hard Gates)

Non-negotiable constraints (position sizing, max loss, event stand-down, stop rules, etc.).

Layer E — Execution Runtime (Paper-first)

Paper trading execution only initially, with strict authorization boundaries.

Layer F — Learning Intelligence (Phase D)

Logs analysis/trade events, scores process vs outcome, clusters failures, refines confidence and weighting (not risk rules).

⸻

3) Core Design Principles (must remain true)
	1.	Process quality is scored separately from outcome quality
(A good process loss is not a failure; a poor process win is not success.)
	2.	Risk management is invariant
Learning can influence confidence/weighting, not hard safety rules.
	3.	AION analyses before it trades
Analysis quality is built and measured before execution is enabled.
	4.	LLMs are challengers/referees/debriefers, not unquestioned authorities
	5.	LLM disagreement is a signal
If model outputs conflict materially, reduce exposure or avoid.
	6.	Layered unlocks only
No jumping to multi-pair / order flow / live trading before proving prior layers.

⸻

4) What AION Must Learn (Complete Knowledge Curriculum)

This is the full knowledge curriculum to teach AION before serious execution.

4.1 Market Structure & Mechanics
	•	Forex pair quoting (base/quote, bid/ask, spread)
	•	OTC market mechanics and price discovery
	•	Session structure (Sydney/Tokyo/London/NY)
	•	Liquidity windows and rollover
	•	Market participants (CBs, institutions, MM, HFT, retail)
	•	Spread dynamics and execution implications

4.2 Price Action & Technical Structure
	•	Candlestick anatomy and pattern interpretation
	•	Support/resistance (horizontal + dynamic)
	•	Trend structure (HH/HL, LH/LL)
	•	Breakout vs fakeout
	•	Chart patterns (flags, wedges, triangles, etc.)
	•	Timeframe confluence
	•	Volume context (where available)
	•	Gap behavior / sentiment implications

4.3 Order Flow & Market Microstructure
	•	Level 2 / depth interpretation
	•	Footprint charts and delta
	•	Iceberg/absorption signatures
	•	Stop hunts / liquidity grabs
	•	Liquidity pools and stop clustering
	•	Institutional flow footprints
	•	Relationship between order flow and visible price action

4.4 Smart Money Concepts (SMC)
	•	BOS / CHoCH
	•	Order blocks
	•	FVG / imbalance
	•	Premium/discount zones
	•	Inducement and traps
	•	Liquidity raids / sweeps
	•	Return-to-origin / institutional positioning logic

4.5 Technical Indicators (Understanding, Not Dependency)

AION must understand what they measure, lag, and limitations:
	•	EMA/SMA/VWAP
	•	RSI
	•	MACD
	•	Bollinger Bands
	•	ATR
	•	Stochastic
	•	Fibonacci (self-fulfilling behavior)
	•	Volume profile / OBV (where data supports)

4.6 Forex Fundamentals
	•	Central bank policy and rate differentials
	•	CPI/NFP/GDP/PMI and reaction mechanics
	•	Currency strength and relative value
	•	Pair correlations (e.g., EURUSD/GBPUSD/USDCHF)
	•	Carry trade logic
	•	Geopolitics and risk-on/off
	•	Safe havens and commodity currencies

4.7 Session & Timing Intelligence
	•	Session opens and typical behavior
	•	London/NY overlap dynamics
	•	Prime windows and dead zones
	•	End-of-week/month flows
	•	Holiday liquidity conditions

4.8 Macroeconomic Context
	•	Inflation regimes
	•	Rate cycles
	•	DXY influence
	•	Bond yields and FX impact
	•	Equity/commodity spillovers
	•	Risk sentiment cycles

4.9 Geopolitical Intelligence (Macro Chessboard Thinking)
	•	Political actor mapping (backgrounds, incentives, networks)
	•	Consequence mapping (trade flows, capital flows, policy effects)
	•	2nd/3rd-order impacts across countries
	•	Long-horizon pair implications (3/6/12/24 months)
	•	Regime shifts before they appear in price

⸻

5) Strategy Architecture (All Strategies, Separated Cleanly)

These are separate strategy modules with separate performance tracking and learning.

Tier 1 — Order Flow Sniping (HFT-adjacent)

Timeframe: sub-minute to 1m
Goal: Trade just above HFT speed by reading footprints, not competing in microseconds.
Use: later unlock

Inputs
	•	Order book depth
	•	Footprint/delta
	•	Key structural levels
	•	Spread checks
	•	Session open windows

Patterns
	•	Stop hunt + reversal
	•	Absorption
	•	Delta divergence
	•	Order book thinning path
	•	Imbalance bursts

Constraints
	•	Very short holds
	•	Tight stops
	•	No first-2-minute session open execution
	•	High data quality requirement

⸻

Tier 2 — Momentum / Opening Range (ORB)

Timeframe: 1m–15m
Use: early-mid phase after SMC baseline

Patterns
	•	London/NY opening range breakout (with retest)
	•	Momentum continuation pullbacks (EMA/VWAP)
	•	Volume confirmation (if available)
	•	Higher timeframe alignment

Rules
	•	Entry on confirmation/retest, not blind chase
	•	Defined stop opposite structure/range
	•	Hard invalidation if return inside failed breakout conditions

⸻

Tier 3 — SMC Intraday (Core Starting Strategy)

Timeframe: 15m–1h
Use: first strategy to implement for paper trading

Patterns
	•	Liquidity sweep + CHoCH + return
	•	Order block retest
	•	FVG fill continuation/reversal
	•	Structural confluence with session timing

Why first
	•	Explains why price moves (liquidity + structure)
	•	Strong fit with AION’s reasoning architecture
	•	Enough signal frequency without extreme noise

⸻

Tier 4 — Swing Trading

Timeframe: 4h–Daily
Use: after intraday process discipline proven

Inputs
	•	Structural breaks
	•	Macro filter (CIM + DMIP)
	•	Fundamental alignment
	•	Weekly/monthly levels

Execution
	•	First pullback after break
	•	1–2% risk max (still under invariants)
	•	Multi-day holds
	•	Trail after 1:1

⸻

Tier 5 — Macro Positioning (Filter / Bias Layer)

Timeframe: Weekly+
Use: context and directional filter for all lower tiers

Inputs
	•	Central bank divergence
	•	COT and positioning proxies
	•	Geopolitical shifts
	•	Country score spreads (CIM)
	•	Monthly/quarterly themes

Role
	•	Not an early “trade every signal” engine
	•	High-level directional bias and veto/filter layer

⸻

6) Risk Management Rules (Absolute Invariants)

These are hard gates, not suggestions. Learning cannot rewrite them.

6.1 Position Sizing
	•	Max risk per trade: 1%
	•	Max daily risk: 3%
	•	Max weekly risk: 6%
	•	Position size derived from stop distance + pip value
	•	No sizing up during drawdown
	•	No averaging down

6.2 Stop-Loss Rules
	•	Every trade must have a stop at entry
	•	Stop beyond structure, not arbitrary
	•	Stop may move toward profit only (trail), never widen
	•	If valid stop requires >1% risk → no trade

6.3 Take-Profit / Exit Rules
	•	Min RR: 1:2
	•	Preferred RR: 1:3+
	•	Breakeven at 1:1 (strategy-dependent if partials used)
	•	Partials allowed (e.g., 50% at 1:1)
	•	No emotional early exits if thesis/risk remains valid

6.4 Session Rules
	•	Max 3 losing trades/session → stop session
	•	Daily loss limit hit → no more trading that day
	•	No trading first minutes around key opens (as defined by strategy)
	•	No trading during red events until protocol says re-entry allowed
	•	No late Friday exposure near close (rule-configurable)

6.5 Account Protection
	•	Max drawdown before full stop: 10%
	•	Mandatory review before resuming after drawdown stop
	•	Detailed logging required for every trade and no-trade decision

⸻

7) DMIP — Daily Market Intelligence Protocol (Final Version to Implement)

DMIP is the intelligence layer above execution. AION must never trade blind.

7.1 Daily Checkpoint Schedule (Operational)

Implement these checkpoints as skills/jobs:
	1.	06:00 GMT — Pre-Market Global Briefing
	•	Overnight moves, Asian session summary, news digest, econ calendar, DXY, futures, bonds, commodities, sentiment
	•	Claude + GPT consultations
	•	Output: Daily Bias Sheet (per pair + risk environment + avoid list)
	2.	07:45 GMT — London Pre-Open Check
	•	Revalidate morning bias
	•	Pre-London liquidity sweeps
	•	Spread/order book checks
	•	Triple-check key pairs
	•	Output: London Session Plan (go/no-go + setups + levels)
	3.	10:00 GMT — Mid-London Review
	•	Did bias play out?
	•	Trade management decisions
	•	Reassess range vs trend
	•	Output: Continue / stand down + NY bias update
	4.	13:30 GMT — NY Pre-Open Analysis
	•	London summary, US data, DXY, futures, media sentiment
	•	Quad-check on red-event days
	•	Output: NY Session Plan (go/no-go + continuation/reversal framework)
	5.	22:30 GMT — Asia Open Preparation
	•	Full-day summary
	•	APAC data/BOJ/RBA context
	•	Range vs trend expectations for Asia pairs
	•	Output: Asia Session Plan (often no-go for some pairs)
	6.	22:00 GMT — End-of-Day Learning Debrief
	•	Review all trades / passes / bias accuracy / LLM accuracy
	•	LLM critique of AION reasoning
	•	Output: Daily learning record + knowledge updates

(If you want exact times shifted around your operating window, that can be config, but this is the baseline.)

⸻

7.2 High-Impact Event Protocols (Red/Amber)

AION must have specific event protocols (not generic rules).

Red events (examples)
	•	NFP
	•	CPI
	•	Central bank rate decisions
	•	Major press conferences / unscheduled CB remarks (when material)

Amber events
	•	PMI
	•	GDP prelims
	•	Retail sales
	•	ADP
	•	Medium-impact policy remarks

Required behavior
	•	Pre-event analysis (consensus/prior/revisions)
	•	“What is priced in?” question to both LLMs
	•	Time-based no-trade windows
	•	Post-event wait period
	•	Follow-through confirmation only (no spike chasing)

⸻

7.3 Multi-LLM Verification Framework (Final)

This is mandatory in early stages.

Workflow
	1.	AION runs its own analysis first
	2.	Send structured query to Claude
	3.	Send same structured query to GPT
	4.	Compare:
	•	Agreement = confidence increase
	•	Disagreement = uncertainty signal / reduce or avoid
	5.	If both disagree with AION materially → stand down unless strong historical evidence supports AION thesis

Rule (early stage)
	•	If Claude and GPT return conflicting directional bias on a pair/session setup → mark pair AVOID unless confidence override conditions are met (later phase only).

Performance Tracking

Track model accuracy by:
	•	Pair
	•	Session
	•	Event type
	•	Directional bias
	•	Level prediction
	•	Event reaction interpretation

This eventually becomes weighted consultation instead of equal weighting.

⸻

8) Macro Chessboard / Country Intelligence Matrix (CIM) (Final Required Layer)

This is the top-level “4D chessboard” you described and it is officially part of the implementation.

8.1 Purpose

Represent each country/currency region as a continuously updated weighted scorecard to estimate:
	•	Country strength trajectory
	•	Macro regime shifts
	•	Pair directional probability (country A vs country B)

8.2 Country Dimensions (Scored)

Each country gets weighted dimensions (with confidence + recency):
	•	Central bank stance
	•	Inflation trajectory
	•	Growth momentum
	•	Fiscal position / debt trajectory
	•	Trade relationship health
	•	Geopolitical positioning
	•	Political leadership quality / strategic moves
	•	Sentiment trajectory (retail + institutional narrative)
	•	Capital flow direction (proxy)
	•	Commodity exposure sensitivity
	•	Stability / uncertainty score

8.3 Time Dimension (4D element)

Track not just value, but:
	•	Level
	•	Velocity (improving/deteriorating)
	•	Acceleration (change in trend)
	•	Confidence / evidence quality
	•	Recency decay

8.4 Pair Probability Logic

Pair directional macro score = weighted differential between two country scorecards
Example: Score(EUR) - Score(USD) → macro bias tendency for EURUSD.

8.5 Usage in Trading

CIM does not force entries. It acts as:
	•	directional filter
	•	confidence modifier
	•	stand-down trigger when intraday setup contradicts strong macro regime without confirmation
	•	swing/macro strategy input

8.6 Daily LLM Macro Discussion

AION + LLMs discuss the macro chessboard daily/weekly:
	•	What changed?
	•	Which country scores moved materially?
	•	What is second-order impact?
	•	Which pairs are most exposed?

⸻

9) What AION Starts With (Exact Starting Point)

Do not start broad. Start narrow and measured.

9.1 First Instrument
	•	EUR/USD

9.2 First Session
	•	London session only (initially)

9.3 First Strategy
	•	SMC Intraday (15m)

9.4 First Execution Mode
	•	Analysis-only first
	•	Then paper trading
	•	No live capital initially

9.5 Trade Limits (initial)
	•	Max 1–2 trades/session
	•	A-grade setups only
	•	Strict event filters
	•	Mandatory EOD debrief

⸻

10) What We Teach First (Teaching Sequence to Implement)

This order matters and is part of the implementation plan.
	1.	Risk invariants + stand-down rules
	2.	Session logic / market timing
	3.	Market structure basics
	4.	Candlestick reading / price action
	5.	SMC framework
	6.	Event protocol behavior (NFP/CPI/rates)
	7.	Historical chart walkthroughs (labelled examples)
	8.	Order flow basics
	9.	Paper-trade reasoning walkthroughs (10+ manually reviewed)
	10.	Daily DMIP briefing + debrief discipline

This ensures AION learns discipline before entries.

⸻

11) Reinforcement Learning & Learning Intelligence (Final)

This is where AION gets better without becoming unsafe.

11.1 Every Trade / Analysis Event Must Become a Learning Record

AION logs:
	•	what it saw
	•	what it concluded
	•	why
	•	whether it traded
	•	what happened
	•	critique and corrections

11.2 Mandatory Score Separation

Each record should score at least:
	•	process_score
	•	outcome_score
	•	rule_compliance_score
	•	context_quality_score
	•	execution_quality_score (if trade)
	•	reward_score (derived)

This is non-negotiable for valid learning.

11.3 Pattern Accumulation Cadence
	•	Every 10 trades: mini clustering review
	•	Every 50 trades: setup performance review
	•	Every 100 trades: full strategy weighting review
	•	Continuous: expectancy by pair/session/setup/event context

11.4 LLM Debrief as Teacher Loop

After each session/day:
	•	AION presents thesis vs reality
	•	LLM critiques reasoning
	•	Corrections stored
	•	Repeated confirmed corrections promoted to semantic knowledge

⸻

12) Phase D Integration (What Sprint 3 Actually Does in Trading)

Sprint 2 (already aligned with your path)
	•	Read-only learning context injection into orchestrator/debug/trace
	•	Learning summaries visible, not decision-mutating

Sprint 3 (the correct next behavior)

Governed writable decision influence (not strategy mutation)

Allowed writes:
	•	confidence weights by setup type
	•	stand-down sensitivity modifiers
	•	pair/session preference weights
	•	LLM trust weighting by task/pair/event
	•	caution multipliers for event regimes

Not allowed:
	•	rewriting risk invariants
	•	changing max loss/position sizing rules
	•	changing execution authorization gates
	•	autonomous live-trading enablement

This is the correct safety boundary.

⸻

13) Skills to Implement (Final Registry Scope)

Below is the actual skill map to build.

13.1 Data Skills
	•	fetch_price_data(pair, timeframe, bars)
	•	fetch_orderbook(pair)
	•	fetch_footprint(pair, window) (if provider supports)
	•	fetch_economic_calendar(hours_ahead)
	•	fetch_news_digest(pairs_or_currencies, window)
	•	fetch_sentiment_data(pair_or_currency)
	•	fetch_cot_report(currency)
	•	fetch_dxy_data()
	•	fetch_bond_yields()
	•	fetch_equity_futures()
	•	fetch_commodity_prices()
	•	fetch_session_times(session, timezone)

13.2 Analysis Skills
	•	identify_market_structure(chart_data)
	•	find_support_resistance(chart_data)
	•	identify_order_blocks(chart_data)
	•	find_fair_value_gaps(chart_data)
	•	detect_liquidity_pools(chart_data)
	•	detect_bos_choch(chart_data)
	•	read_orderflow_signals(orderbook, footprint)
	•	calculate_atr(chart_data, period)
	•	assess_confluence(signals)
	•	check_news_proximity(timestamp)
	•	classify_volatility_regime(data)
	•	classify_market_regime(macro, sentiment, volatility)

13.3 DMIP Intelligence Skills
	•	run_morning_briefing()
	•	generate_daily_bias_sheet()
	•	run_session_analysis(session)  (London/NY/Asia)
	•	run_mid_session_review(session, open_trades)
	•	run_nfp_protocol(days_before)
	•	run_rate_decision_protocol(bank, hours_before)
	•	run_eod_debrief(daily_trades, daily_bias_sheet)

13.4 LLM Consultation Skills
	•	consult_claude(query, context)
	•	consult_gpt(query, context)
	•	synthesise_llm_responses(responses)
	•	log_llm_accuracy(model, prediction, actual)
	•	get_llm_weighted_bias(pair, task_type)

13.5 Monitoring Skills
	•	monitor_hft_footprints(pair)
	•	monitor_retail_sentiment(pair)
	•	monitor_correlation_breaks()
	•	monitor_spread(pair)
	•	check_stand_down_triggers()

13.6 CIM / Macro Chessboard Skills
	•	update_country_scorecard(country_code, evidence_bundle)
	•	calculate_country_composite(country_code)
	•	calculate_pair_macro_spread(base_ccy, quote_ccy)
	•	compute_country_score_velocity(country_code)
	•	run_macro_chessboard_review()
	•	generate_macro_pair_priority_sheet()

13.7 Execution Skills (Paper-first)
	•	calculate_position_size(account_equity, risk_pct, stop_pips, pip_value)
	•	validate_risk_rules(trade_proposal)
	•	submit_paper_trade(pair, direction, size, stop, target)
	•	manage_open_trade(trade_id, market_state)
	•	close_trade(trade_id, reason)

13.8 Learning Skills
	•	log_analysis_record(record)
	•	log_trade_record(record)
	•	calculate_expectancy(trade_history)
	•	cluster_trade_patterns(trade_history)
	•	cluster_analysis_failures(analysis_history)
	•	generate_session_review(session_data)
	•	promote_pattern_to_semantic_memory(pattern)
	•	update_decision_influence_weights(signals) (Sprint 3 governed)

⸻

14) Data & Memory Objects (What Must Be Persisted)

These are the persistent artifacts AION needs to build a real edge.

14.1 Daily Intelligence Artifacts
	•	Daily bias sheet
	•	Session plans (London/NY/Asia)
	•	Event protocol outputs
	•	EOD debrief record
	•	LLM consultations + disagreements

14.2 Trade Artifacts
	•	Trade proposals (including rejected/no-trade decisions)
	•	Executed trade logs
	•	Management actions
	•	Final results
	•	Process and outcome scoring

14.3 Learning Artifacts
	•	Episodic learning events
	•	Failure clusters / weakness signals
	•	Pattern library entries
	•	LLM accuracy logs by task
	•	Decision influence weights (Sprint 3+)
	•	Strategy performance summaries by pair/session/setup

14.4 Macro Chessboard Artifacts
	•	Country scorecards
	•	Evidence bundles
	•	Pair spread probability sheets
	•	Weekly/monthly macro theme summaries

⸻

15) Build Order (Actual Implementation Roadmap)

This is the practical order to implement.

Phase 1 — Analysis Intelligence First (No Trading)

Goal: Build DMIP and score analysis quality before execution.

Implement:
	•	data ingestion basics
	•	run_morning_briefing()
	•	generate_daily_bias_sheet()
	•	LLM consultations + comparison
	•	EOD debrief and analysis accuracy tracking
	•	learning logs for analysis events

Success gate
	•	30–60 days of consistent bias/debrief logs
	•	measurable improvement in analysis accuracy
	•	stable data pipelines and schemas

⸻

Phase 2 — Paper Trading (Single Pair, Single Strategy)

Goal: Add execution with hard risk gates.

Implement:
	•	paper execution runtime
	•	risk validation skill
	•	SMC 15m EURUSD London only
	•	trade logging + process/outcome scoring
	•	stand-down triggers enforcement

Success gate
	•	Minimum sample size (e.g., 100 paper trades)
	•	Positive expectancy (or improving expectancy with high process quality)
	•	High rule compliance
	•	No invariant violations

⸻

Phase 3 — LLM Weighting + Learning Influence (Governed)

Goal: Improve decision quality safely.

Implement:
	•	LLM task-specific performance tracking
	•	weighted consultation synthesis
	•	Phase D Sprint 3 decision influence writes
	•	setup confidence and pair/session preference adjustments

Success gate
	•	Demonstrated improved filtering
	•	Lower false-positive trades
	•	No drift into risk-rule violations

⸻

Phase 4 — Strategy Expansion

Goal: Add breadth only after proof.

Order:
	1.	Momentum / ORB (London/NY)
	2.	More pairs (majors)
	3.	Asia session (JPY/AUD focus)
	4.	Swing strategy
	5.	Order flow sniping (if data/infrastructure quality supports)

Each strategy gets separate performance and learning tracking.

⸻

Phase 5 — Macro Chessboard Integration (CIM as live filter)

Goal: Top-down regime-aware intelligence.

Implement:
	•	country scorecards
	•	pair macro spread probabilities
	•	weekly/monthly macro reviews
	•	CIM-based confidence modifiers and veto logic

⸻

Phase 6 — Controlled Live Exposure (Much Later)

Only after paper performance + governance + audits
	•	Tiny size
	•	Human approval gates
	•	Hard kill switch
	•	No autonomous risk-rule changes

⸻

16) Early-Stage Operating Rules (Important)

At the early stage, AION must operate under these meta-rules:
	•	No live trading
	•	No strategy mutation
	•	No risk-rule edits
	•	No trusting a single LLM
	•	No trading red-event spikes
	•	No overtrading
	•	No broad multi-pair rollout before evidence

This is how you prevent “looks intelligent” from becoming “unsafe and inconsistent”.

⸻

17) What Makes AION Actually Better Than Typical Traders (the real edge)

The edge is not secret indicators.

The edge is:
	•	disciplined risk execution every time
	•	structured pre-market and session intelligence
	•	multi-LLM challenge/debrief loops
	•	process-vs-outcome learning separation
	•	continuous pattern accumulation
	•	macro chessboard context layered over intraday execution
	•	no fatigue / no revenge / no overconfidence

That is a real, buildable edge.

⸻

18) Final Implementation Decision (Locked v1)

We are implementing AION trading in this order:
	1.	DMIP + analysis-only learning
	2.	Paper trading EURUSD, London, SMC 15m
	3.	Risk invariants + stand-down enforcement
	4.	LLM weighting + governed learning influence
	5.	Strategy expansion
	6.	Macro Chessboard/CIM integration as top-level filter
	7.	Only later controlled live exposure

We are explicitly not doing (yet):
	•	live autonomous trading
	•	HFT competition
	•	unrestricted strategy self-modification
	•	risk invariant mutation
	•	multi-strategy/multi-pair rollout before proof

⸻

If you want, next I can turn this into a Tessaris house-style LaTeX spec (final lockable document) with:
	•	RFC-style MUST/SHOULD/MAY wording
	•	phase gates / unlock criteria
	•	exact schemas list for v1
	•	lock footer format matching your standard













-------------



AION TRADING INTELLIGENCE
Forex, Day Trading & Multi-Strategy Intelligence System
Complete Knowledge Architecture, Strategy Specification & Training Curriculum

Kevin Robinson  |  Tessaris AI  |  2026
Lock ID: AION-TRADING-V1.0-2026-02-21

1. Executive Overview
This document defines the complete knowledge architecture, strategy framework, and training curriculum required to develop AION into a professional-grade multi-strategy trading intelligence system. AION is not a trading bot. It is a governed learning intelligence that will develop genuine trading knowledge, execute with mechanical discipline, and continuously improve through structured reinforcement.
The fundamental thesis is this: professional trading is not a secret. The rules of risk management, the mechanics of order flow, the patterns of momentum are all known. What separates consistently profitable traders from losing ones is not secret knowledge but disciplined execution, pattern recognition at scale, and continuous adaptation. AION can develop all three.

2. What AION Must Learn — Core Knowledge Domains
AION must ingest, understand, and be able to reason about the following knowledge domains before any strategy execution begins. These are not optional. They form the cognitive foundation.
2.1 Market Structure & Mechanics
How currency pairs are quoted (base/quote, bid/ask, spread)
How forex markets operate: session times, liquidity windows, rollover
Major, minor, and exotic pairs — characteristics and behavior differences
Market participants: central banks, institutional players, retail traders, HFT firms
How price discovery actually works in a decentralised OTC market
The role of market makers and liquidity providers
How spreads widen and narrow and why this matters for execution
2.2 Price Action & Technical Analysis
Candlestick anatomy and multi-candle patterns (engulfing, doji, pin bar, inside bar)
Support and resistance: horizontal levels, dynamic levels, structural zones
Trend identification: higher highs/lows, lower highs/lows, trend channels
Breakouts versus fakeouts — how to distinguish them
Chart patterns: triangles, flags, wedges, head and shoulders, double tops/bottoms
Volume analysis: what volume reveals about conviction and institutional participation
Timeframe confluence: reading multiple timeframes simultaneously
Gap analysis: what gaps reveal about sentiment and likely fill behaviour
2.3 Order Flow & Market Microstructure
Level 2 order book: bid/ask depth, how to read pending orders
Footprint charts: volume traded at each price level within a candle
Delta analysis: difference between buying and selling volume at each level
Iceberg orders: large hidden orders and how to detect their footprint
Stop hunting: how institutional players move price to trigger retail stop losses
Liquidity pools: where stop clusters accumulate above/below key levels
Order absorption: when large orders are being absorbed at a level
Institutional order flow signatures: how large money enters without tipping its hand
The relationship between order flow and price action
2.4 Smart Money Concepts (SMC)
Market structure from an institutional perspective
Break of structure (BOS) and change of character (CHoCH)
Order blocks: zones where institutional orders were previously placed
Fair value gaps (FVG): imbalances in price that tend to get filled
Premium and discount zones: where price is expensive versus cheap relative to range
Inducement: how smart money creates the appearance of setups to trap retail
Liquidity voids and why price moves through them quickly
The concept of raids: moves designed purely to collect liquidity
2.5 Technical Indicators — Understanding Not Dependency
AION must understand what indicators actually measure, their lag characteristics, and their limitations — not use them as signals in isolation.
Moving averages (SMA, EMA, VWAP): what they represent and their lag
RSI: momentum measurement, divergence, overbought/oversold in context
MACD: momentum shift detection and its limitations
Bollinger Bands: volatility measurement and squeeze patterns
ATR (Average True Range): volatility quantification for position sizing
Stochastic oscillator: momentum in ranging markets
Fibonacci retracements and extensions: why they work (self-fulfilling) and when they don't
Volume indicators: OBV, VWAP, volume profile
2.6 Fundamental Analysis for Forex
Central bank policy: interest rate decisions and their market impact
Economic calendar: NFP, CPI, GDP, PMI — what each reveals and expected market reaction
Currency strength analysis: relative strength across all major pairs
Correlation between pairs: EUR/USD and USD/CHF inverse relationship, etc.
Carry trades: interest rate differentials driving long-term flows
Geopolitical events and risk-on/risk-off dynamics
Safe haven currencies: USD, JPY, CHF behaviour during stress
Commodity-linked currencies: AUD, CAD, NZD relationships
2.7 Market Sessions & Timing
Sydney session: low liquidity, range-bound, Asian pairs most active
Tokyo session: JPY pairs most active, often establishes daily range
London session: highest liquidity, major moves initiated, 8am-12pm GMT prime window
New York session: overlaps London creating highest volatility, US data releases
London/New York overlap (1pm-5pm GMT): most volume of the day
Session opens as high-probability trade windows
End of week and month-end flows and their predictable patterns
Holiday effects on liquidity
2.8 Macroeconomic Context
Understanding the current interest rate environment and its implications
Inflation dynamics and central bank response patterns
Risk sentiment cycles: what drives risk-on versus risk-off globally
The dollar index (DXY) and its relationship to all USD pairs
Bond market signals and their forex implications
Equity market correlation patterns with forex

3. Strategy Architecture — From HFT-Adjacent to Swing
AION will operate across multiple strategy types simultaneously, each with its own signal inputs, execution logic, and reinforcement loop. They share a common risk management core. Strategies are listed from fastest to slowest timeframe.
3.1 Strategy Tier 1 — Order Flow Sniping (HFT-Adjacent)
Timeframe: Sub-minute to 1-minute | Pairs: EUR/USD, GBP/USD, USD/JPY
This is the layer just above true HFT. AION reads order book dynamics and footprint data to identify where large players are operating and executes ahead of or alongside their flow. This is not reaction — it is anticipation based on microstructure reading.
What AION looks for:
Large iceberg orders appearing at key levels — signals institutional intent
Stop hunt signatures: rapid move through obvious level followed by reversal
Delta divergence: price rising but sell delta increasing — warning of reversal
Absorption: large buying volume not moving price — sell pressure being absorbed
Order book thinning above/below price — path of least resistance
Imbalance candles: large single-direction candles revealing institutional aggression
Execution rules:
Entry only when order flow signal aligns with structural level
Maximum hold time: 5 minutes
Stop loss: beyond the structural level, never more than 5 pips on majors
Target: next liquidity pool or imbalance
No trade during first 2 minutes of session open (spread risk)
3.2 Strategy Tier 2 — Momentum & Opening Range
Timeframe: 1-minute to 15-minute | Pairs: All majors
Opening range trading exploits the directional bias established in the first 15-30 minutes of the London and New York sessions. Momentum trading rides established directional moves with high conviction entries.
Opening Range Breakout (ORB):
Define range: high and low of first 15 minutes of London open (8am GMT)
Wait for clear breakout with volume confirmation
Entry on retest of broken level (not blind breakout chase)
Target: 1.5x to 2x the opening range size
Stop: opposite side of range
Invalidation: false break and return inside range
Momentum continuation:
Identify established trend on 5-minute chart
Wait for pullback to 20 EMA or VWAP
Entry on rejection candle at pullback level
Stop: below the pullback low
Target: previous swing high (trend continuation)
Confluence required: higher timeframe trend alignment
3.3 Strategy Tier 3 — Smart Money Concepts (SMC) Intraday
Timeframe: 15-minute to 1-hour | Pairs: All majors and select minors
Trading from the institutional perspective: identifying where smart money has placed orders, where they will engineer liquidity grabs, and entering with them on the return move.
Core setup — Liquidity grab and return:
Identify obvious swing high/low where retail stops cluster
Wait for price to sweep that level (stop hunt)
Confirm reversal: change of character on lower timeframe
Entry: on retracement into order block or fair value gap
Stop: beyond the liquidity grab wick
Target: opposite liquidity pool
Order block entry:
Identify origin of a strong move (the order block candle)
Wait for price to return to that zone
Confirm with lower timeframe entry trigger
Entry at order block with tight stop
Target: next imbalance or structural level
3.4 Strategy Tier 4 — Swing Trading
Timeframe: 4-hour to Daily | Pairs: All majors
Swing trades capture multi-day moves based on structural breaks, momentum shifts, and fundamental alignment. Lower frequency but higher point capture per trade.
Setup criteria:
Daily or 4H structure break with momentum
Fundamental alignment (currency strength, central bank direction)
Key level: weekly or monthly support/resistance
Pattern completion: flag, triangle, or range breakout on daily
Volume expansion on breakout candle
Execution:
Entry: on first pullback after structure break
Stop: beyond structure, sized for 1-2% account risk
Target: measured move (pattern height projected) or next major level
Hold time: 2 to 10 days
Trail stop after 1:1 risk/reward achieved
3.5 Strategy Tier 5 — Macro Positioning
Timeframe: Weekly | Pairs: Major pairs aligned with central bank divergence
Long-term directional bias based on interest rate differentials, central bank policy divergence, and macro flows. This provides the directional filter for all lower timeframe strategies.
Track central bank meeting schedules and rate decisions
Monitor COT (Commitment of Traders) reports for institutional positioning
Identify pairs with largest interest rate divergence
Use as directional filter: only take lower timeframe longs in bullish macro pairs
Review and update weekly — not a trading strategy itself but a context layer

4. Risk Management Rules — Absolute and Non-Negotiable
These rules are not guidelines. They are invariants. AION must enforce every single one without exception on every single trade. This is where most human traders fail. AION cannot fail here.
4.1 Position Sizing
Maximum risk per trade: 1% of account equity
Maximum risk per day: 3% of account equity
Maximum risk per week: 6% of account equity
Position size calculated from: (Account equity × risk %) / (Stop loss in pips × pip value)
Never increase position size during a losing period
Never add to a losing position (no averaging down)
4.2 Stop Loss Rules
Every trade must have a stop loss set at entry — no exceptions
Stop loss must be placed beyond a structural level, not arbitrary pip distance
Stop loss must never be moved further from entry (only trail toward profit)
If stop loss would require more than 1% risk, do not take the trade
4.3 Take Profit & Exit Rules
Minimum risk/reward ratio: 1:2 (risk 1, target 2)
Preferred risk/reward: 1:3 or better
Move stop to breakeven after 1:1 is achieved
Take partial profit (50%) at 1:1, trail remainder
Never close a trade early due to anxiety if stop and target are valid
4.4 Daily & Session Rules
Maximum 3 losing trades in a session — stop trading for that session
After daily loss limit hit — no more trading that day
No trading during major news events (NFP, rate decisions) — wait for volatility to settle
No trading during first 2 minutes of session opens
No trading in last 30 minutes before weekend close (Friday 4:30pm EST)
4.5 Account Protection Rules
Maximum drawdown before full stop: 10% of starting equity
After 10% drawdown: mandatory review before resuming
Never risk more on a single trade than the potential reward justifies
Keep detailed trade log: entry, exit, reason, result, learning

5. What AION Starts With — Phase 1 Implementation
AION does not start by trading all strategies simultaneously. It starts with the most learnable, most data-rich, most feedback-efficient environment and expands only as performance proves readiness.
5.1 Starting Instrument: EUR/USD
Highest liquidity pair in the world — tightest spreads, cleanest price action
Most studied and documented — vast historical data available
Most liquid during London and NY sessions — AION's primary trading windows
Technically clean: respects levels well, less susceptible to random manipulation
24-hour trading enables continuous learning cycles
5.2 Starting Strategy: SMC Intraday on 15-minute chart
Reason: SMC provides a complete framework that explains why price moves, not just what it does. It aligns with the order flow knowledge AION is building. The 15-minute chart provides enough data for pattern learning without the noise of sub-minute charts.
Focus exclusively on London session initially (8am-12pm GMT)
Maximum 2 trades per session
Only A-grade setups: all criteria must align
Paper trading only until 100 trades logged with positive expectancy
5.3 Starting Data Feeds AION Requires

5.4 First Teaching Sessions — What AION Learns First
Before any live paper trading, AION requires structured teaching sessions in this order:
Market structure fundamentals — what a trend is, what support/resistance means, how sessions work
Risk management rules — all rules in Section 4, tested for comprehension before proceeding
Candlestick reading — pattern identification and what each pattern reveals about intent
SMC concepts — order blocks, FVGs, liquidity, BOS, CHoCH in detail
Historical chart analysis — 500+ examples of setups, labelled with outcome
Order flow basics — reading the footprint chart and delta
Paper trade simulation — first 10 trades walked through step by step with AION reasoning aloud

6. The Reinforcement Learning Loop — How AION Gets Better
Every trade AION executes becomes a learning event. The quality of this loop determines how fast AION develops genuine edge. The loop must be structured, not vague.
6.1 Per-Trade Learning Record

6.2 Reinforcement Signal Structure
Win with good process: strong positive reinforcement of all elements
Win with poor process: weak positive — flag execution issues
Loss with good process: weak negative — correct analysis, market randomness
Loss with poor process: strong negative — reinforce rule violations as critical failures
The key distinction: AION must learn to evaluate process quality independently from outcome. A good process loss is not a failure. A poor process win is not a success.
6.3 Pattern Accumulation
After every 10 trades: cluster analysis on setup type vs outcome
After every 50 trades: identify highest and lowest performing setups
After every 100 trades: full performance review, adjust strategy weighting
Continuous: track expectancy by session, pair, setup type, time of day
Flag any pattern appearing 3+ times with consistent outcome for skill promotion
6.4 Conversation-Based Review
After each session, AION engages in structured review conversation with an LLM teacher (Claude or GPT-4), presenting its trade reasoning and receiving critique. This mirrors the professional trading desk debrief process.
AION presents each trade with full reasoning
Teacher identifies reasoning errors or missed signals
AION stores the corrected reasoning as an episodic learning event
Corrected reasoning is promoted to semantic memory after 3 consistent confirmations

7. Expansion Roadmap — From Single Pair to Multi-Strategy


8. AION Technical Skill Architecture for Trading
Each of the following represents a discrete skill in AION's skill registry. They are built, tested, and promoted through the standard skill promotion workflow (experimental → verified → core).
8.1 Data Skills
fetch_price_data(pair, timeframe, bars) — retrieve OHLCV data
fetch_orderbook(pair) — real-time L2 order book snapshot
fetch_economic_calendar(days_ahead) — upcoming news events
fetch_cot_report(currency) — COT positioning data
calculate_currency_strength(pairs) — relative strength matrix
fetch_session_times(session) — current session with DST adjustment
8.2 Analysis Skills
identify_market_structure(chart_data) — trend direction, swing points
find_support_resistance(chart_data) — key horizontal levels
identify_order_blocks(chart_data) — institutional order zones
find_fair_value_gaps(chart_data) — price imbalances
detect_liquidity_pools(chart_data) — stop cluster locations
read_footprint(footprint_data) — delta and volume at price
calculate_atr(chart_data, period) — volatility measurement
assess_confluence(signals_list) — score all alignment factors
check_news_proximity(timestamp) — news avoidance validation
8.3 Execution Skills
calculate_position_size(account_equity, risk_pct, stop_pips, pip_value)
validate_risk_rules(trade_proposal) — check all invariants before entry
submit_paper_trade(pair, direction, size, stop, target)
manage_open_trade(trade_id, current_price) — trail stop, partial close
close_trade(trade_id, reason)
8.4 Learning Skills
log_trade_record(trade_data) — full structured trade logging
calculate_expectancy(trade_history) — statistical performance
cluster_trade_patterns(trade_history) — pattern analysis
generate_session_review(session_trades) — structured debrief
promote_pattern_to_skill(pattern_data) — validated pattern → skill

9. Summary
AION's path to world-class trading intelligence follows a clear progression: deep domain knowledge first, mechanical rule encoding second, structured paper trading with tight reinforcement loops third, and gradual expansion as performance proves readiness.
The edge is not a secret strategy. The edge is AION's ability to execute the same correct process every single time without exception, recognise patterns across thousands of trades faster than any human, and continuously refine its model through structured reinforcement.
Every professional trader already knows what AION will be taught. The difference is AION will execute it perfectly.

Lock ID: AION-TRADING-V1.0-2026-02-21
Status: DRAFT — Knowledge Architecture Complete
Maintainer: Tessaris AI  |  Author: Kevin Robinson



________________


AION DAILY MARKET
INTELLIGENCE PROTOCOL
Multi-Checkpoint LLM Analysis System — Daily Briefing, Event Response & Edge Detection

Kevin Robinson  |  Tessaris AI  |  2026
Lock ID: AION-DMIP-V1.0-2026-02-21

1. Purpose & Design Philosophy
This document defines the AION Daily Market Intelligence Protocol (DMIP) — a structured multi-checkpoint system that ensures AION never enters a trading session without a complete, LLM-verified understanding of the current market environment.
The core principle: trading without context is gambling. Every professional trading desk runs a morning briefing. AION runs a better one — multiple times per day, with triple and quadruple verification on high-impact events, and continuous background monitoring between checkpoints.
AION does not react to markets. AION understands markets before they open, monitors them as they evolve, and only acts when its multi-checkpoint analysis confirms a genuine edge exists.
The LLM consultation layer serves two purposes: it provides external analytical perspective to challenge AION's own analysis, and it ensures that AION's reasoning is stress-tested before any capital is at risk — even paper capital at the early stage.

2. Daily Checkpoint Schedule
AION runs six structured checkpoints per day aligned with market session opens and high-impact windows. Each checkpoint has a specific scope, data sources, analytical questions, and decision output.
Checkpoint 1 — Pre-Market Global Briefing
06:00 GMT  Daily Intelligence Briefing
This is the most important checkpoint of the day. AION constructs a complete picture of overnight developments before any session opens.
Data AION ingests:
Overnight price action on all major pairs — what moved, how far, on what volume
Asian session summary — did Tokyo establish a range or trend, key levels hit
Overnight news digest — geopolitical developments, central bank statements, economic data releases
Economic calendar for the full day — all red and amber events with consensus vs prior
Currency strength matrix — which currencies gained/lost overnight
DXY overnight movement — directional bias for all USD pairs
Equity futures — risk-on/risk-off signal from S&P 500, DAX, Nikkei futures
Bond yield movements — 10-year US Treasury, Bund — carry and risk signals
Commodity prices — Gold (safe haven), Oil (CAD/NOK correlation)
Sentiment scan — Twitter/X financial community, trading forums, institutional research headlines
LLM Consultation Questions (sent to Claude + GPT-4 independently):
What is the dominant directional bias for EUR/USD, GBP/USD, USD/JPY today based on overnight data?
Which pairs have the cleanest technical setups heading into London open?
Are there any scheduled events today that could invalidate technical setups?
What is the current risk sentiment and which pairs benefit most?
Are there any contradictions between technical picture and fundamental context?
Output — Daily Bias Sheet:
Directional bias per pair: BULLISH / BEARISH / NEUTRAL / AVOID
Key levels to watch per pair
News events to avoid per session
Overall risk environment: RISK-ON / RISK-OFF / MIXED
Trading confidence score: HIGH / MEDIUM / LOW / STAND DOWN
If Claude and GPT-4 return conflicting directional bias on a pair — AION marks that pair as AVOID for the day. Disagreement between LLMs signals genuine uncertainty.
Checkpoint 2 — London Open Analysis
07:45 GMT  15 Minutes Before London Open
Final verification before the highest volume session of the day begins.
AION checks:
Has anything changed since the 06:00 briefing? Breaking news, sudden price moves
Pre-London price action — did price sweep obvious liquidity levels overnight?
Order book depth on EUR/USD and GBP/USD — is there visible institutional positioning?
Spread check — are spreads normal or widening (signal of news risk)
Confirm daily bias still valid — no new developments invalidating morning analysis
LLM Consultation (triple check on key pairs):
Based on current pre-London price position, is the morning bias still valid?
What is the most probable first move at London open — continuation or reversal of overnight range?
Are there obvious stop clusters above/below current price that London players will likely target first?
Output — London Session Plan:
Go/No-Go decision for London session trading
Primary setup to watch with specific entry criteria
Levels to watch for stop hunt before real move
Maximum trades for London session: 1 or 2 only
Checkpoint 3 — Mid-London Review
10:00 GMT  2 Hours Into London Session
Reassessment after initial London price action has established direction.
AION evaluates:
Did morning bias play out? What happened at open?
Was there a stop hunt before the real move — confirming or denying institutional thesis
Current momentum: is London trending or ranging?
Any trades taken: current status, management decisions
Remaining opportunity in London session (closes around 12:00 GMT)
LLM Consultation (if trades active):
Given what actually happened at London open, is the trade thesis still valid?
Should the stop be trailed or remain at original placement?
Is momentum sufficient to hold for full target or should partial profit be taken?
Output:
Trade management decision for any open positions
Decision on remaining London session: continue / stand down
Updated bias for NY session based on London price action
Checkpoint 4 — New York Open Analysis
13:30 GMT  30 Minutes Before NY Open
The NY open overlapping with London is the highest volatility window of the day. Triple verification required before any NY session trading.
AION ingests:
Full London session summary — what direction, what levels taken, what levels held
Any US economic data released pre-market (often 13:30 GMT — NFP, CPI, retail sales)
US equity futures final positioning before cash open
DXY direction heading into NY — strongest USD signal of the day
Any Fed speaker scheduled — comments can move markets immediately
News sentiment from US financial media (Bloomberg, Reuters, WSJ headlines)
LLM Consultation (quadruple check on high-impact event days):
Does the London price action confirm or contradict the morning directional bias?
Is there a continuation or reversal setup forming for the NY session?
If major US data just released — what is the expected market reaction and how long before it settles?
What is the institutional flow likely to be in the NY/London overlap window?
On Red event days (NFP, CPI, rate decisions): AION does not trade the first 15 minutes after release regardless of what any LLM says. Wait for volatility to settle and direction to confirm. No exceptions.
Output — NY Session Plan:
Go/No-Go for NY session
Bias: continuation of London trend or reversal watch
Specific setup criteria for NY entry
Hard stop time: no new entries after 17:00 GMT
Checkpoint 5 — Asia Open Preparation
22:30 GMT  30 Minutes Before Tokyo Open
For 24-hour coverage across forex pairs. Asia session is lower volatility but provides setups for JPY and AUD pairs. Also sets the range that London will later break.
AION reviews:
Full day summary — what happened in London and NY, net directional moves
Any Asia-Pacific economic data due (RBA, BOJ statements, Chinese data)
JPY pairs specifically — BOJ intervention risk assessment
AUD/USD — commodity correlation check (iron ore, gold prices)
NZD/USD — RBNZ policy context
Overall risk sentiment from US session close
LLM Consultation:
What range is likely for EUR/USD in the Asia session based on today's volatility?
Are there any JPY pairs with clean range-bound setups for the Asia session?
Any overnight risk events (speeches, data) that should trigger stand-down?
Output — Asia Session Plan:
Go/No-Go for Asia session (often NO-GO for EUR/USD — low liquidity)
Pairs to focus on: typically JPY crosses, AUD, NZD
Range expectation — avoid breakout trades in Asia, favour mean reversion
Checkpoint 6 — End of Day Learning Debrief
22:00 GMT  Daily Close Review
This is not a trading checkpoint. This is the reinforcement learning session. AION reviews the full day, stress-tests its reasoning with LLM feedback, and updates its knowledge base.
AION reviews:
All trades taken today — entry, exit, result, process quality score
All signals identified but not taken — were they correct to pass?
Bias accuracy — did morning analysis predict actual market behaviour?
LLM consultation accuracy — which LLM gave better analysis today?
Any patterns observed that were not in existing knowledge base
LLM Debrief Consultation:
Here is what I thought would happen today. Here is what actually happened. Where was my analysis wrong?
Here is a trade I took. Here is my reasoning. Where could this have been better?
Here is a setup I avoided due to high volatility. Was that the correct decision?
Output — Daily Learning Record:
Bias accuracy score for the day (0-100%)
Trade process quality scores
Knowledge updates: new patterns, corrected assumptions
LLM teacher performance log — tracking which model gives better analysis over time

3. High-Impact Event Protocol — Red & Amber Events
Economic events are the single biggest source of manipulation and retail trader destruction. AION treats them with extreme caution and applies a specific multi-check protocol for each tier.
3.1 Event Classification

3.2 NFP Protocol (Non-Farm Payrolls — First Friday Each Month)
NFP is the single most market-moving event in forex. AION applies maximum caution.
48 hours before NFP:
Collect consensus forecast, prior reading, and revision history
Assess ADP employment data (released Wednesday before NFP) as leading indicator
Gather analyst sentiment range — what outcome would be a surprise?
LLM consultation: what is the market pricing in, and what would cause maximum surprise?
Day before NFP:
Reduce position sizing on all trades by 50%
Close any swing trades that would be exposed to NFP
Identify key levels that will matter post-NFP
NFP release day:
No new trades from 13:00 GMT until 30 minutes after release
At release: AION records actual vs forecast vs prior
LLM consultation immediately after: what does this number mean for dollar direction?
Wait minimum 15 minutes for initial volatility to exhaust
Look for institutional direction confirmation — not the spike, the follow-through
If direction confirmed with volume: may enter in direction of institutional flow
If contradictory moves (spike up then down): stand down, manipulation likely
3.3 Central Bank Rate Decision Protocol
Rate decisions from Fed, ECB, BOE, BOJ, RBA are second only to NFP in market impact.
Pre-decision analysis (LLM triple check):
Current market pricing: what is priced in (check Fed Funds futures, OIS swaps)
Analyst consensus: what does the street expect?
Recent central bank communication: what have they signalled?
AION question to LLMs: what would be a hawkish surprise, what would be a dovish surprise?
Decision day execution rules:
No new trades 2 hours before decision
Watch the statement AND the press conference — often the press conference moves markets more
Wait 30 minutes after press conference ends before considering any trade
Look for the second move — initial reaction is often reversed or extended after 30 minutes
3.4 Sentiment Analysis Protocol
Beyond scheduled events, AION monitors unscheduled sentiment shifts that can signal edge or manipulation risk.
Sources AION monitors daily:
Twitter/X financial community: search for pair-specific discussion and sentiment shift
Reddit (r/Forex, r/investing, r/wallstreetbets for equity correlation)
TradingView public ideas: retail trader bias (contrarian signal when extreme)
Bloomberg and Reuters headline sentiment: institutional narrative
ForexFactory forum: retail sentiment (often a contrarian indicator at extremes)
LLM Sentiment Synthesis:
AION aggregates raw sentiment data and asks LLMs:
Is there extreme retail consensus in one direction? (contrarian risk)
Is institutional commentary diverging from retail sentiment? (follow institutions)
Are there narrative shifts that have not yet shown in price action? (leading signal)
When retail sentiment on a pair reaches extreme consensus (80%+ one direction on TradingView polls or similar), AION flags this as a potential contrarian signal — institutional players often move against crowded retail positioning.

4. Multi-LLM Verification Framework
AION does not rely on a single LLM for market analysis. It runs consultations across multiple models and treats disagreement as a signal in itself.
4.1 Consultation Architecture

4.2 Consultation Protocol
Standard consultation structure (every checkpoint):
Step 1: AION runs its own analysis first — forms independent view
Step 2: Send structured query to Claude with all relevant data
Step 3: Send identical query to GPT-4
Step 4: Compare responses — identify agreements and disagreements
Step 5: Where both agree: high confidence signal
Step 6: Where they disagree: AION flags pair as uncertain, reduces or eliminates exposure
Step 7: Where both disagree with AION's own analysis: AION defers unless it has strong pattern-based reason not to
4.3 Structured Query Template
Every LLM consultation uses a structured format to ensure consistent, comparable responses:
MARKET CONTEXT: [Current date, session, major overnight moves]
PAIR FOCUS: [Specific pair being analysed]
TECHNICAL PICTURE: [Current price, key levels, recent structure]
FUNDAMENTAL CONTEXT: [Relevant news, upcoming events, central bank stance]
SENTIMENT DATA: [Current retail positioning, analyst consensus]
QUESTION: [Specific analytical question]
OUTPUT FORMAT: Directional bias (BULLISH/BEARISH/NEUTRAL), confidence (HIGH/MEDIUM/LOW), key risk to thesis, key levels to watch
4.4 LLM Performance Tracking
AION tracks the accuracy of each LLM over time to weight their input intelligently.
Per-model accuracy score updated after every day's events resolve
Accuracy tracked by: directional bias, key level identification, event reaction prediction
Models that consistently outperform on specific pairs get higher weighting on those pairs
If a model's accuracy drops below 55% over 20 consultations: flag for review

5. Continuous Pattern Recognition & Edge Detection
Between checkpoints, AION runs continuous background analysis to detect emerging patterns and edge opportunities that develop during the trading day.
5.1 Continuous Monitoring — What AION Watches
Price approaching key levels identified in morning briefing
Volume spikes on any major pair — possible institutional activity
Correlation breaks: EUR/USD and GBP/USD diverging significantly (unusual, signals specific news)
Volatility expansion on normally quiet pairs
Order book changes: large orders appearing or disappearing at key levels
News wire alerts: any unscheduled central bank communication
DXY breaking key level — affects all USD pairs simultaneously
5.2 HFT Footprint Detection
AION monitors for signatures of HFT activity that precede larger moves:
Rapid order book changes at a single level — HFT testing liquidity
Sub-second price spikes that immediately retrace — HFT stop hunting
Volume concentration at specific price levels before breakout
Spoofing patterns: large orders that appear and disappear without executing
Momentum ignition: rapid price move to trigger momentum algorithms
When AION detects HFT footprints, it does not chase. It waits for the HFT activity to exhaust and then evaluates whether the resulting price position creates a genuine setup for human-speed execution.
5.3 Day Trader Pattern Recognition
Most day traders use identical strategies taught by the same educators. Their collective behaviour creates predictable patterns AION can exploit.
Opening range breakout chasing — retail buys breakout, AION watches for failure and reversal
Round number magnetism — price always tests round numbers, retail stops cluster there
Double top/bottom chasing — retail enters on pattern completion, smart money fakes the pattern
Indicator crossover entries — retail enters on MACD cross, often late
AION approach: identify where retail is entering, assess whether smart money is positioned against them
5.4 Weekly & Monthly Pattern Analysis
AION maintains rolling analysis of longer-term patterns to inform daily bias:
Weekly review (every Sunday before Asia open):
Previous week summary: net moves on all major pairs, key levels established
Monthly performance relative to expectations
COT report analysis: has institutional positioning changed significantly?
LLM consultation: what is the dominant weekly theme and which pairs benefit most?
Identify weekly key levels: previous week high/low as targets for next week
Monthly analysis (first Sunday of month):
Previous month OHLC on all pairs: major structural reference points
Central bank meeting schedule for the month
Major economic data calendar for the month
Seasonal patterns: certain months have consistent directional tendencies
LLM consultation: what is the macro theme for this month and which pairs align best?

6. Stand Down Protocol — When AION Does Not Trade
Knowing when NOT to trade is as important as knowing when to trade. AION operates a formal stand-down protocol triggered by specific conditions.
6.1 Automatic Stand-Down Triggers

6.2 High Volatility vs Edge Assessment
Not all volatility should be avoided. AION distinguishes between:
Manipulative volatility: random spikes, stop hunts, fake breakouts — STAND DOWN
Directional volatility: strong momentum move with institutional backing — POTENTIAL EDGE
News volatility: initial spike after data release — STAND DOWN, then reassess
Session volatility: normal London/NY open activity — NORMAL OPERATION
The question AION asks at every volatile moment: Is this chaos or is this direction? Chaos = stand down. Confirmed direction with volume = potential trade.

7. Implementation as AION Skills
Each checkpoint and protocol element maps to a specific skill in AION's skill registry.
7.1 Intelligence Skills
run_morning_briefing() — full checkpoint 1 pipeline
run_session_analysis(session) — pre-session checkpoint for London/NY/Asia
run_mid_session_review(session, open_trades) — mid-session checkpoint
run_eod_debrief(daily_trades) — end of day learning session
fetch_economic_calendar(hours_ahead) — upcoming events with impact rating
run_nfp_protocol(days_before) — NFP-specific multi-stage analysis
run_rate_decision_protocol(bank, hours_before) — central bank protocol
7.2 LLM Consultation Skills
consult_claude(query, context_data) — structured Claude consultation
consult_gpt4(query, context_data) — structured GPT-4 consultation
synthesise_llm_responses(claude_response, gpt4_response) — agreement/disagreement analysis
log_llm_accuracy(model, prediction, actual_outcome) — performance tracking
get_llm_weighted_bias(pair) — bias weighted by historical model accuracy
7.3 Monitoring Skills
monitor_hft_footprints(pair) — continuous order book pattern detection
monitor_retail_sentiment(pair) — aggregated retail positioning signals
monitor_correlation_breaks() — detect unusual divergence between correlated pairs
monitor_spread(pair) — real-time spread checking
check_stand_down_triggers() — evaluate all automatic stand-down conditions
7.4 Pattern Recognition Skills
analyse_weekly_structure(pair) — weekly key levels and theme
analyse_monthly_context(pair) — monthly bias and calendar
detect_retail_trap_patterns(chart_data) — identify where retail is likely trapped
detect_institutional_accumulation(orderbook, footprint) — smart money activity
generate_daily_bias_sheet() — consolidated output from morning briefing

8. Reinforcement Learning from Analysis Quality
AION's analysis improves through the same reinforcement loop applied to trading. Every morning bias prediction is verified against actual market behaviour and fed back into the learning system.
8.1 Bias Accuracy Tracking
Morning directional bias per pair tracked against actual daily direction
Session setup identification: was the predicted setup correct?
Key level accuracy: did price react at predicted levels?
Event reaction prediction: did AION correctly anticipate news-driven moves?
Weekly theme accuracy: did the weekly macro view play out?
8.2 LLM Teacher Quality Evolution
Over time, AION builds a performance record for each LLM across different analytical tasks:
Which model is better at predicting direction after economic data?
Which model is better at identifying key technical levels?
Which model gives more accurate sentiment analysis?
Which model better anticipates central bank reactions?
This data feeds into the consultation weighting — better-performing models on specific tasks receive higher weight for those tasks.
8.3 Pattern Library Growth
Every market event AION observes and analyses becomes a potential pattern entry in its growing knowledge base. Patterns are promoted from episodic memory to semantic memory when:
The pattern has been observed minimum 10 times
The outcome is consistent at least 65% of the time
The LLM consultation confirms the pattern is structurally sound
The pattern survives stress-testing against counter-examples

9. Summary — The Intelligence Advantage
The AION Daily Market Intelligence Protocol gives AION something no individual human trader has: complete, consistent, emotionally neutral market analysis at every session open, verified by multiple LLMs, updated continuously throughout the day, and improved systematically through reinforcement learning.
Human traders miss morning briefings, skip analysis when tired, ignore stand-down rules under pressure, and fail to debrief consistently. AION executes every element of this protocol without exception, every single day.
The edge compounds. Better analysis leads to better trades. Better trades produce better reinforcement signals. Better signals improve future analysis. Over hundreds of cycles, AION's market intelligence becomes genuinely world-class — not because it was programmed with secrets, but because it consistently does what professionals know works, without the human failures that prevent them from doing it every time.
The market does not reward intelligence. It rewards disciplined, consistent application of intelligence. That is AION's structural advantage.

Lock ID: AION-DMIP-V1.0-2026-02-21
Status: DRAFT — Daily Market Intelligence Protocol Complete
Maintainer: Tessaris AI  |  Author: Kevin Robinson