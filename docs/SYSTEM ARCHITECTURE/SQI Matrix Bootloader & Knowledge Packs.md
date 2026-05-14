Matrix Bootloader & Knowledge Packs

User Manual + Technical Guide

⸻

0) TL;DR — What you’re building
	•	Scaffolds = domain packs (*.dc.json) with nodes + links. They define where knowledge goes and how it connects.
	•	Knowledge = actual content (proof libraries, datasets, models) that populate those nodes.
	•	Bootloader wires it all together: loads domain packs into UCS → injects into KG → exports snapshots → bridges domains with cross_links.
	•	SQI/Tessaris then uses the knowledge: replays proofs, runs simulations, detects drift, writes back results.

To specialize on a real problem, you:
	1.	Drop the right domain packs in the right place.
	2.	Load actual sources (math proofs, physics models, curated datasets).
	3.	Run the bootloader to ingest + export.
	4.	Kick off replay/validation jobs.
	5.	Iterate.

⸻

1) Directory map (what goes where)

backend/modules/dimensions/
  containers/                 # ✅ Human-authored seed packs (*.dc.json)
  containers_saved/           # ✅ Snapshots the bootloader saves
    kg_exports/               # ✅ Compact KG exports (for replay / fast reload)
  knowledge_atoms/            # ✅ Big external payloads (proof corpora, large tables)
    math/
    physics/
    econ/

    Other important locations:
	•	Bootloader: backend/modules/hexcore/boot_loader.py
	•	UCS runtime: backend/modules/dimensions/universal_container_system/ucs_runtime.py
	•	KG writer: backend/modules/knowledge_graph/knowledge_graph_writer.py
	•	SQI bus (spam guard toggles): backend/modules/sqi/sqi_event_bus.py

⸻

2) Boot commands & flags

Run

PYTHONPATH=. \
AION_SQI_SIM_BROADCAST=0 \
AION_ENABLE_WS_BROADCAST=0 \
AION_LOG_LEVEL=warn \
python -m backend.modules.hexcore.boot_loader

Why the flags?
	•	AION_SQI_SIM_BROADCAST=0 — mutes simulated SQI spam.
	•	AION_ENABLE_WS_BROADCAST=0 — quiets WebSocket chatter during ingest.
	•	AION_LOG_LEVEL=warn — show warnings+errors only.

⸻

3) Domain pack format (the scaffold)

Minimal schema for *.dc.json:

{
  "id": "physics_core",
  "name": "Physics Core",
  "type": "dc",
  "symbol": "⚛️",
  "metadata": {
    "domain": "physics",
    "description": "Mechanics, Thermo, EM, QFT resonance",
    "version": "1.0"
  },
  "glyph_categories": [
    { "id": "mech", "label": "Mechanics", "emoji": "⚙️" }
  ],
  "nodes": [
    {
      "id": "newton_laws",
      "label": "Newton's Laws",
      "cat": "mech",
      "source": { "tier": "secondary", "ref": "doi:..." }
    }
  ],
  "links": [
    { "src": "newton_laws", "dst": "maxwell_eqs", "relation": "informs" }
  ]
}

Notes
	•	Use id/name consistently. The file name must be <id>.dc.json.
	•	nodes[*].source.tier ∈ {primary, secondary, tertiary} to encode provenance.
	•	links[*] capture semantic relations (e.g., depends_on, proves, validates, influences).

⸻

4) Knowledge sources (the content)

This is where the actual intelligence comes from.

A) Formal math libraries (Lean/Coq/Isabelle)
	•	Export doc JSON (defs/lemmas/theorems + deps).
	•	Store here:
backend/modules/dimensions/knowledge_atoms/math/mathlib_docgen.json
	•	Reference it from a domain pack node, e.g.:

{
  "id": "mathlib_core",
  "label": "Lean mathlib",
  "cat": "library",
  "source": {
    "tier": "primary",
    "ref": "knowledge_atoms/math/mathlib_docgen.json"
  }
}

{
  "id": "mathlib_core",
  "label": "Lean mathlib",
  "cat": "library",
  "source": {
    "tier": "primary",
    "ref": "knowledge_atoms/math/mathlib_docgen.json"
  }
}

B) Physics/Engineering models
	•	Put big model sets (equations, parameter tables) under knowledge_atoms/physics/…
	•	Reference them similarly via source.ref.

C) Data (primary/secondary/tertiary)
	•	You already have data_primary, data_secondary packs.
	•	Drop CSV/Parquet/HDF under knowledge_atoms/<domain>/data/... and reference via nodes.
	•	Link datasets to the theories they validate:

{ "src": "market_ticks", "dst": "efficient_market_hypothesis", "relation": "validates" }

5) Bootloader pipeline (what actually happens)
	1.	Preload containers
	•	Finds containers/<id>.dc.json or containers_saved/<id>.dc.json.
	•	Loads into UCS (so it’s runtime-visible).
	2.	Persist
	•	Saves the current pack to containers_saved/<id>.dc.json for cold starts.
	3.	Inject into KG
	•	kg_writer.attach_container(container) to keep glyphs scoped.
	•	kg_writer.load_domain_pack(...) or generic _ingest_dc_into_kg fallback creates KG nodes/edges.
	4.	Export compact KG pack
	•	containers_saved/kg_exports/<id>.kg.json (small, fast to reload).
	5.	Bridge last
	•	cross_links.dc.json is applied after all domain packs to stitch them together.

You’ll see logs like:

🧠 KG: physics_core domain loaded into Knowledge Graph.
💾 KG export saved to .../kg_exports/physics_core.kg.json

6) Cross-domain links (cross_links.dc.json)

Purpose: ensure graph connectivity across domains so reasoning can flow.
You already created a comprehensive file; keep it in containers/ and the bootloader will apply it last.

Tips:
	•	Only link existing node IDs (avoid typos).
	•	Use meaningful relations: derives_from, validates, models, controls, applied_to, influences.

⸻

7) From scaffold → “actually solves problems”

Step 1: Pick a target problem

Example: Stabilize a plasma (MHD) with minimal actuator power.

Step 2: Ensure required packs exist
	•	physics_core (MHD, EM)
	•	control_systems (LQR/H∞/MPC)
	•	engineering_materials (thermal limits, conductivity)
	•	economics_core (cost/trade-offs, decision theory)
	•	data_primary, data_secondary (diagnostic time series + curated features)

Step 3: Load real knowledge
	•	Import proof corpus (functional analysis → PDE well-posedness).
	•	Import model packs (MHD equations, device parameters).
	•	Import datasets (sensor timeseries, power logs).

Step 4: Link it
	•	Add edges:
	•	MHD_model -> sobolev_spaces : requires
	•	feature_marts -> mpc : feeds
	•	bode_plot -> power_supply_constraints : respects
	•	market_ticks -> power_price_model : validates

Step 5: Boot
	•	Run the bootloader (with quiet flags).
	•	Verify exports were written to kg_exports.

Step 6: Replay/validate
	•	Run proof replay on the imported math (see §8).
	•	Run simulation/estimators and write drift reports.
	•	Iterate until drift is low and proofs/constraints are satisfied.

⸻

8) Proof replay & verification (SQI/Tessaris)

You can automate formal verification so the system continuously checks itself.

Ingredients
	•	mathlib_import.py (adapter) — reads doc-gen JSON → emits KG nodes (axiom/lemma/theorem) + depends_on edges.
	•	run_proof_replay.py — walks imported theorems, tries replay (or static confirmation), emits:
	•	proof_state glyphs (status: verified | failed | unknown)
	•	drift_report glyphs on inconsistencies
	•	edges: theorem_X -> dataset_Y : validated_by if you link empirical checks

Where to put

backend/modules/tessaris/mathlib_import.py
backend/modules/tessaris/run_proof_replay.py

Kickoff

PYTHONPATH=. AION_LOG_LEVEL=info python -m backend.modules.tessaris.mathlib_import \
  --doc-json backend/modules/dimensions/knowledge_atoms/math/mathlib_docgen.json

PYTHONPATH=. AION_LOG_LEVEL=info python -m backend.modules.tessaris.run_proof_replay \
  --scope mathlib_core --max 500

  (If you want, I’ll hand you ready-to-drop stubs next.)

⸻

9) Data tiers (what each is for)
	•	Primary: unprocessed reality (sensors, logs, raw lab data).
	•	Secondary: cleaned/curated/feature-engineered; model-ready.
	•	Tertiary: derivative artifacts (benchmarks, reports, dashboards), often many-to-one summaries.

Link them
	•	Primary → Secondary: "relation": "promoted_to" | "transforms_to"
	•	Secondary → Model nodes: "feeds"
	•	Tertiary → Theorems/Policies: "summarizes" | "supports" | "explains"

⸻

10) Observability & hygiene
	•	Spam control
	•	AION_SQI_SIM_BROADCAST=0
	•	AION_ENABLE_WS_BROADCAST=0
	•	AION_LOG_LEVEL=warn
	•	Memory sanitize
	•	Bootloader calls sanitize_memory_file_at(...)—you’ll see how many bad rows got dropped.
	•	Exports
	•	After boot you should have JSON in containers_saved/ and kg_exports/.
	•	Inspect with:

    jq '.nodes | length' backend/modules/dimensions/containers_saved/kg_exports/physics_core.kg.json
jq '.links | length' backend/modules/dimensions/containers_saved/kg_exports/physics_core.kg.json

11) Troubleshooting
	•	“seed not found for ”
	•	Ensure containers/<id>.dc.json exists & id matches filename.
	•	“KG export failed: name ‘KG_EXPORT_DIR’ is not defined”
	•	Make sure bootloader defines KG_EXPORT_DIR before use.
	•	WS/GPIO spam
	•	Use the env flags above; ensure debouncing is enabled in sqi_event_bus.py.
	•	UCSGeometryLoader.register_geometry() missing ... 'description'
	•	If your cross_links is treated as a geometry, add "description" or ensure it loads as a normal DC container (not a geometry). Keep it in containers/, not the geometry registry.
	•	jq: Cannot index array with string "links"
	•	You probably piped the raw nodes array into .links. Run jq '.nodes|length, .links|length' file.json from root of the JSON, not inside a sub-array.

⸻

12) Versioning & persistence
	•	Boot saves canonical snapshots to containers_saved/.
	•	KG exports are compact—prefer these for quick cold starts.
	•	Keep IDs stable; links depend on exact node IDs.
	•	For huge payloads, put content in knowledge_atoms/ and reference it from domain packs (don’t inline massive data).

⸻

13) Security & ethics
	•	The system emits SoulLaw approvals/violations as glyphs.
	•	If you integrate external actions (actuators, trading), put risk guards into the KG (e.g., policy_node -> action_node : governs) and enforce checks before execution.

⸻

14) Typical “specialize me” workflow (checklist)
	1.	Create/extend domain packs needed by your problem.
	2.	Put actual knowledge under knowledge_atoms/ (proofs, models, data).
	3.	Reference those files in domain nodes via source.ref.
	4.	Write cross links that connect the domains.
	5.	Run bootloader (quiet flags).
	6.	Verify exports in kg_exports/.
	7.	Run mathlib_import (if using formal libraries).
	8.	Run run_proof_replay (batch).
	9.	Attach datasets → write validation edges.
	10.	Iterate: fix drift, add missing theorems, refine features, re-run.

⸻

15) FAQ

Q: Isn’t this just metadata?
A: The domain packs are scaffolds. The knowledge is the referenced content (proof corpora, models, data) + the derived glyphs SQI/Tessaris produce during replay/validation.

Q: When does it become “intelligent”?
A: When the graph is dense enough—math ↔ models ↔ data ↔ proofs ↔ policies—and replay/validation loops keep it consistent. Cross-links make inferences propagate.

Q: What do I upload exactly?
A: For math: doc-gen JSON; for physics/engineering: model specs/equations/params; for data: raw CSV/Parquet/HDF; for curation: feature definitions & splits. Reference them via source.ref.


