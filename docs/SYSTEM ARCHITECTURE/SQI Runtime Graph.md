graph TB

  %% === 🧬 DNA & Mutation Core ===
  subgraph 🧬 DNA CHAIN & MUTATION CORE
    DNA_SWITCH[✅ DNA_SWITCH] --> dna_writer[✅ dna_writer.py]
    DNA_SWITCH --> mutation_checker[✅ mutation_checker.py]
    DNA_SWITCH --> symbolic_entangler[✅ symbolic_entangler.py]
    DNA_SWITCH --> collapse_trace_exporter[✅ collapse_trace_exporter.py]
    DNA_SWITCH --> glyph_executor[✅ glyph_executor.py]
  end

  %% === 🌌 Symbolic Core ===
  subgraph 🌌 SYMBOLIC CORE & LOGIC SYSTEMS
    glyph_executor --> tessaris_engine[✅ tessaris_engine.py]
    glyph_executor --> codex_executor[✅ codex_executor.py]
    glyph_executor --> codex_context_adapter[✅ codex_context_adapter.py]
    glyph_executor --> symbolic_key_deriver[✅ symbolic_key_deriver.py]
    glyph_executor --> glyph_quantum_core[✅ glyph_quantum_core.py]
    glyph_executor --> glyph_logic[✅ glyph_logic.py]
    glyph_quantum_core --> GHX_Encoder[✅ ghx_encoder.py]
    GHX_Encoder --> QEntropy_Beam[🌀 QEntropy Beam]
  end

  %% === 🧠 Memory & Strategy ===
  subgraph 🧠 MEMORY & STRATEGY SYSTEM
    memory_engine[✅ memory_engine.py] --> memory_bridge[✅ memory_bridge.py]
    memory_engine --> strategy_planner[✅ strategy_planner.py]
    strategy_planner --> milestone_tracker[✅ milestone_tracker.py]
    strategy_planner --> Fork_Memory_Path[🪞 Fork Memory Path]
  end

  %% === 🌀 Containers & Holography ===
  subgraph 🌀 SYMBOLIC CONTAINERS & EXPANSION
    hoberman_container[✅ hoberman_container.py] --> container_runtime[✅ container_runtime.py]
    hoberman_container --> teleport_packet[✅ teleport_packet.py]
    hoberman_container --> glyphnet_ws[✅ glyphnet_ws.py]
    container_runtime --> Entanglement_Graph[↔ Entanglement Map]
    container_runtime --> Collapse_Observer[⧖ Collapse Detection]
  end

  %% === 🔐 Security Stack ===
  subgraph 🔐 SECURITY & ENCRYPTION
    symbolic_key_deriver --> vault_bridge[✅ vault_bridge.py]
    symbolic_key_deriver --> soul_law_validator[✅ soul_law_validator.py]
    vault_bridge --> identity_registry[✅ identity_registry.py]
    vault_bridge --> glyphnet_crypto[✅ glyphnet_crypto.py]
  end

  %% === 🛰️ Broadcast ===
  subgraph 🛰️ BROADCAST & TRACE LAYERS
    glyphnet_ws --> glyph_trace_logger[✅ glyph_trace_logger.py]
    glyphnet_ws --> glyphnet_terminal[✅ glyphnet_terminal.py]
    glyphnet_ws --> gip_packet[✅ gip_packet.py]
    glyphnet_ws --> gip_adapter_http[✅ gip_adapter_http.py]
    glyphnet_ws --> GlyphPush_Streamer[🛰️ Push / Replay Engine]
  end

  %% === 🌌 Frontend UI ===
  subgraph 🌌 FRONTEND HUD & VISUALIZERS
    CodexHUD[✅ CodexHUD.tsx] --> RuntimeGlyphTrace[✅ RuntimeGlyphTrace.tsx]
    CodexHUD --> GHXVisualizer[✅ GHXVisualizer.tsx]
    CodexHUD --> HolographicViewer[✅ HolographicViewer.tsx]
    CodexHUD --> replay[✅ replay.tsx]
    EntanglementGraph[✅ entanglement.tsx] --> seed_entangled[📦 seed_entangled.dc.json]
  end

  %% === 🔁 Active Triggers ===
  subgraph 🔁 ACTIVE SYMBOLIC FLOWS
    glyph_executor --> Self_Rewrite[⬁ Self Rewrite Trigger]
    glyph_executor --> Entanglement[↔ Entanglement Trigger]
    glyph_executor --> Collapse[⧖ Collapse Trigger]
    glyph_executor --> Mutation[🧬 Mutation Trigger]
    Collapse --> collapse_trace_exporter
    Self_Rewrite --> DreamSpiral[🌙 Dream Spiral]
  end

  %% === 🎙️ Agent Layer ===
  subgraph 🎙️ Agent & Interface Layer
    agent_comm[✅ agent_comm.py] --> voice_interface[✅ voice_interface.py]
    agent_comm --> aion_prompt_engine[✅ aion_prompt_engine.py]
  end 

  🧠 Key New Insights Added

  Addition
Description
QEntropy Beam
Tracks branching symbolic possibilities like quantum states
Dream Spiral
Rewriting logic spiraling inward to re-inject symbolic alternatives
Collapse Observer
Monitors contradiction events and triggers collapse
Fork Memory Path
Allows branching memory timelines to co-exist and replay
GHX Encoder
Compresses logic into holographic pulses for CodexNet and replay
GlyphPush Streamer
Real-time broadcasting of replayable symbolic thought


