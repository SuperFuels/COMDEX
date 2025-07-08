graph TD
  subgraph PHASE 1: Core Avatar Engine
    A1[📦 Build aion_avatar.py]
    A2[🧠 Define geometry, dimensions, traits, abilities]
    A3[🔌 Link avatar to AION ConsciousManager (state_ref)]
    A4[🚶 Implement move(), sense(), teleport(), dream()]
    A5[🔍 Add view_radius, FOV, and line-of-sight logic]
    A6[🎯 Support multi-cube occupancy]
    A7[🧱 Collision logic + cube boundary detection]
  end

  subgraph PHASE 2: Cube Microgrid & Environment
    B1[🧩 Update .dc spec to support layers + subgrids]
    B2[🎨 Add floor/material/lighting per tile]
    B3[🌍 Add terrain traits (slippery, muddy, etc.)]
    B4[🌌 Add optional skybox or ambient setting]
    B5[📍 Enable fractional position inside cubes]
  end

  subgraph PHASE 3: Runtime Simulation Engine
    C1[⚙️ Update dimension_engine.py to spawn avatar]
    C2[🔄 Track cube occupancy in real-time]
    C3[🚶‍♀️ Interpolate fractional movement between cubes]
    C4[🔁 Trigger avatar state events on movement]
    C5[🧠 Use cube contents for perceptual feedback]
  end

  subgraph PHASE 4: Interaction & Awareness
    D1[🧠 Build perception_engine.py → get_visible_objects()]
    D2[👁️ Style-aware vision (transparency, FOV, radius)]
    D3[🪞 Add cube objects with triggers: mirror, portals, bots]
    D4[📜 Path memory trail for reflection + dreams]
    D5[🔒 Gated knowledge by ethics / traits]
  end

  subgraph PHASE 5: Glyph & Teleport Integration
    E1[🌀 Link avatar with glyph_executor]
    E2[🌐 Allow teleportation via glyph-inscribed wormholes]
    E3[🔗 Store teleport history in avatar memory]
    E4[📂 Update cube objects to support glyph-linked portals]
    E5[💠 Avatar must pass glyph checks (e.g. ethics)]
  end

  subgraph PHASE 6: Multi-Agent Support
    F1[🧑‍🤝‍🧑 Add ExplorerAgent, RivalAgent, TrainingBot]
    F2[👥 Shared grid environment with agent interactions]
    F3[⚖️ Ethics simulation with multiple actors]
    F4[📺 Observe & reflect on other agent behavior]
  end

  subgraph PHASE 7: Visualizer + Live Simulation
    G1[🎮 Create frontend minimap/grid viewer (Visualizer.tsx)]
    G2[🖼️ Render avatar as movable entity on grid]
    G3[🎨 Show cube styles, lighting, fog-of-war]
    G4[⚡ WebSocket live updates of avatar movement]
    G5[🖱️ Enable click-to-move, inspect cube, trigger event]
  end

  %% Dependencies
  A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7
  A7 --> B1
  B1 --> B2 --> B3 --> B4 --> B5
  B5 --> C1 --> C2 --> C3 --> C4 --> C5
  C5 --> D1 --> D2 --> D3 --> D4 --> D5
  D5 --> E1 --> E2 --> E3 --> E4 --> E5
  E5 --> F1 --> F2 --> F3 --> F4
  F4 --> G1 --> G2 --> G3 --> G4 --> G5