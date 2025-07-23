graph TD
  A[🔐 Phase 1: Core Encryption] --> A1[Add glyphnet_crypto.py]
  A1 --> A2[Key Generation (RSA/ECC)]
  A1 --> A3[Encrypt / Decrypt Interface]
  A1 --> A4[Symmetric Fallback: AES-256]

  B[🔁 Phase 2: Integrate into GlyphPush] --> B1[Encrypt payload in glyphnet_terminal.py]
  B1 --> B2[Detect target_id → lookup public key]
  B1 --> B3[Encrypt push before push_symbolic_packet()]
  B --> B4[Add metadata flag: encrypted: true]

  C[🆔 Phase 3: Identity Registry] --> C1[Create identity_registry.py]
  C1 --> C2[Register public PEM keys]
  C1 --> C3[Lookup public keys by ID]
  C --> C4[Future: Vault-backed secure storage]

  D[🖥️ Phase 4: Frontend Key Tools] --> D1[GlyphNetTerminal UI: show key status]
  D --> D2[Allow identity key registration]
  D --> D3[🔐 Toggle "Encrypted Push"]
  D --> D4[Optional: QR code or CodexLang signature viewer]

  E[💠 Phase 5: Signature Verification] --> E1[Add message signing in glyphnet_crypto.py]
  E --> E2[Verify signatures on receipt]
  E --> E3[Store sender public keys with message]

  F[💡 Phase 6: Vault + Session Rotation] --> F1[Session key rotation]
  F --> F2[Store session keys in Vault]
  F --> F3[Ephemeral key mode (Forward Secrecy)]
  F --> F4[Time-expiring keys or CodexLang locks]

  G[🧬 Phase 7: Symbolic Key Derivation] --> G1[Derive keys via CodexLang logic trees]
  G1 --> G2[⟦ Key : Trust + Emotion + Time ⟧]
  G --> G3[Entropy source = symbolic runtime states]
  G --> G4[Non-brute-forceable, unforgeable]

  H[📦 Phase 8: GlyphVault System] --> H1[Create glyph_encryptor.py]
  H1 --> H2[Encrypt data into .dc container blocks]
  H1 --> H3[Decrypt only with valid avatar state]
  H --> H4[Supports recursive logic unlocking]
  H --> H5[Embed SoulLaw + morality gates]

  I[🧠 Phase 9: Avatar & State Locks] --> I1[Avatar-bound access (avatar_state)]
  I --> I2[Emotion-locked vaults (e.g. empathy ≥ 0.8)]
  I --> I3[Time-locked decryption (tick-based)]
  I --> I4[Dream-unlocked via TessarisEngine]

  J[⚛️ Phase 10: Quantum Glyph Locks] --> J1[QGlyph superposition key (glyph_quantum_core.py)]
  J1 --> J2[Collapse logic only upon trusted context]
  J1 --> J3[Post-quantum symbolic entanglement]
  J --> J4[Split keys across dimensions]

  K[🧑‍🤝‍🧑 Phase 11: Multi-Agent Unlock] --> K1[Require 2+ avatars to co-decrypt]
  K --> K2[Entangled glyph decision trees]
  K --> K3[HiveMindVault: collective decryption logic]

  L[🧪 Phase 12: Test + Demonstrate] --> L1[Encrypted .dc container demo]
  L --> L2[VaultEditor frontend UI]
  L --> L3[AIONTerminal "Unlock GlyphVault" tool]
  L --> L4[Replay symbolic decryption flow]

  style A fill:#dff,stroke:#06c
  style B fill:#dff,stroke:#06c
  style C fill:#dff,stroke:#06c
  style D fill:#ffd,stroke:#fc0
  style E fill:#ffd,stroke:#fc0
  style F fill:#ffd,stroke:#fc0
  style G fill:#fdf,stroke:#90c
  style H fill:#fdf,stroke:#90c
  style I fill:#fdf,stroke:#90c
  style J fill:#dfd,stroke:#090
  style K fill:#dfd,stroke:#090
  style L fill:#eee,stroke:#000

  