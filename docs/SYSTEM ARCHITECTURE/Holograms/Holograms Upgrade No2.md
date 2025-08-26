📘 Technical Documentation: Symbolic Trees and Quantum Field Canvas (QFC)

Overview

This document captures the current implementation status and structure of the Symbolic Tree System and Quantum Field Canvas (QFC) within the COMDEX runtime and container architecture. These systems power the symbolic reasoning, spatial cognition, mutation replay, and introspective knowledge tracing of the IGI (Introspective General Intelligence) system.

⸻

✅ Quantum Field Canvas (QFC)

Location: backend/modules/qfield/

The Quantum Field Canvas is a symbolic visualization system that projects container data into a 3D spatial reasoning field. It enables interactive symbolic cognition, mutation preview, entangled glyph mapping, and predictive overlays.

QFC Subsystem Features

subgraph ✅ QFC [✅ Quantum Field Canvas]
    C1[✅ 🎨 Entangled Glyph Placement]
    C2[✅ 🔦 Light Beam Interaction Paths]
    C3[✅ 🧩 Container → Object → Field Injection]
    C4[✅ 🌀 Real-Time Mutation Surface]
    C5[✅ 🌐 SQI + Prediction Overlay]
end

Key Files
	•	qfc_utils.py — Builds QFC nodes/links from containers (build_qfc_view(...))
	•	qfc_ws_broadcast.py — WebSocket handler for broadcasting QFC payloads
	•	test_qfc_view.py — CLI tool to preview or broadcast QFC payloads
	•	quantum_field_canvas.tsx — React/Three.js renderer for the 3D symbolic field

Data Structure (QFC Payload)

Each QFC payload contains:
	•	type: “qfc”
	•	mode: One of [“live”, “test”, “replay”, “mutation”]
	•	containerId: The originating .dc.json container
	•	nodes: List of glyphs, electrons, predictions (with type, label, metadata, position)
	•	links: Symbolic relationships (tree-link, entanglement, prediction, etc.)

⸻

⬆️ Symbolic Tree Enhancements (STH)

The Symbolic Meaning Tree is a structured symbolic representation of container content. It maps:
	•	Glyphs
	•	Electrons
	•	Predictive paths
	•	Mutations
	•	Logic links

Into a tree-like structure that can be traversed, visualized, or injected into downstream engines (QFC, GHX, ReplayHUD).

subgraph ⬆️ STH [⬆️ 🧱 Symbolic Tree Enhancements]
    T1[✅ Inject root SymbolGlyph into .dc.json]
    T2[✅🛠️ Fix missing container_id → add name + id fields]
    T3[✅➕ Auto-inject all glyphs as SymbolGlyph nodes]
    T4[✅⚛ Add electrons + predictive glyphs as children]
    T5[✅🔗 Link predictions to glyphs/goals via logic]
    T6[✅🌐 Enable replay, entanglement, goal scores]
    T7[✅🛰️ Visualize in GHX, ReplayHUD, or QFC]
end

Key Files
	•	symbol_tree_generator.py — Generates SymbolicMeaningTree from container data
	•	symbolic_tree_node.py — Defines SymbolicTreeNode and traversal/mutation logic
	•	container_loader.py — Loads .dc.json containers (UCS-compatible)
	•	knowledge_graph_writer.py — Can inject symbolic trees during KG write

Tree Node Types
	•	SymbolGlyph — Primary node representing a logic or language glyph
	•	ElectronNode — Represents orbiting electrons, often predictive agents
	•	PredictionNode — Suggested future logic, action, or mutation
	•	GoalNode — Encodes purpose or intent linked to the glyph

Each node supports:
	•	id, label, type, metadata, children[]
	•	Positioning for QFC/ReplayHUD
	•	Entanglement links (↔) and logic links (→)

⸻

🧬 Atom Container Integration

The .dc.json container used in testing:
	•	Path: backend/modules/dimensions/containers/atom_electrons_test.dc.json
	•	Contains:
	•	Root SymbolGlyph
	•	12 orbiting ElectronNodes
	•	PredictiveGlyphs within electrons
	•	Entangled links and logic trails

This container was successfully loaded and visualized using the test_qfc_view.py CLI:

python backend/tools/test_qfc_view.py backend/modules/dimensions/containers/atom_electrons_test.dc.json --broadcast

Broadcast yielded a complete symbolic QFC payload, confirming:
	•	Container integration is correct
	•	WebSocket broadcast hooks are active
	•	Nodes and links properly constructed and serialized

⸻

📡 WebSocket + Tooling Integration
	•	QFC payloads can be sent over live WebSocket for frontend visualization.
	•	Tooling includes:
	•	send_qfc_payload() in qfc_ws_broadcast.py
	•	Broadcast tag: qfc_payload
	•	CLI fallback prints payload to stdout for debugging

⸻

✅ Status Summary

Component	Status
QFC Node/Link Generator	✅ Complete
WebSocket QFC Broadcast	✅ Complete
Symbolic Tree Node Injection	✅ Complete
Electrons + Predictions	✅ Complete
Replay + Goal Hooks	✅ Complete
.dc.json Atom Container	✅ Verified


⸻

📌 Next Steps
	•	Add: symbolic teleport trail generator from SymbolGlyphs
	•	Add: goal alignment scores in PredictionNodes
	•	Visual: Activate full GHX + QFC + ReplayHUD integration layer
	•	Refactor: Migrate legacy containers/ imports → universal_container_system

⸻

This document will be continuously updated as we complete new tasks from the ⬆️ STH and ✅ QFC roadmaps.

🛠️ Save As:
backend/tools/test_qfc_view.py

✅ Usage Examples
	1.	🔍 Print QFC view:

python backend/tools/test_qfc_view.py atom_electrons_test

	2.	📄 Save to file:

python backend/tools/test_qfc_view.py atom_electrons_test --output qfc_dump.json

	3.	🛰️ Broadcast live:

python backend/tools/test_qfc_view.py atom_electrons_test --broadcast

🧠 Overview: SymbolNet

SymbolNet is a plugin-aware bridge between AION’s symbolic glyphs and external semantic knowledge graphs (e.g., ConceptNet, WordNet, Wikidata, Freebase).

Its goals:
	•	Enrich LogicGlyph nodes with common-sense meaning, real-world context, and language associations
	•	Support reasoning tasks like:
	•	Semantic inference (“fire” → “hot”, “dangerous”, “burn”)
	•	Symbol expansion (“water” → “fluid”, “drink”, “ocean”)
	•	Concept validation & contradiction detection
	•	Aid in goal prediction, creative synthesis, and introspection via concept overlays

	
