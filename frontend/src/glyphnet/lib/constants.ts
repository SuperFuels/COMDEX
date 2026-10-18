// src/lib/constants.ts

// Default realm + helpers for GlyphNet addresses
export const DEFAULT_REALM = "wave.tp";

// Public hub topic (good default for inbox/outbox testing)
export const DEFAULT_TOPIC = `ucs://${DEFAULT_REALM}/ucs_hub`;

// Build a per-user inbox topic, e.g., ucs://wave.tp/nova/inbox
export const inboxTopic = (handle: string) =>
  `ucs://${DEFAULT_REALM}/${handle}/inbox`;

// Deterministic development fallback only. Authenticated owner identity is
// supplied by the backend session or the in-memory device identity and must
// never be restored from browser storage.
export const OWNER_WA = "dev@wave.tp";
