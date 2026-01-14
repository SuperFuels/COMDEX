// src/lib/constants.ts

// Default realm + helpers for GlyphNet addresses
export const DEFAULT_REALM = "wave.tp";

// Public hub topic (good default for inbox/outbox testing)
export const DEFAULT_TOPIC = `ucs://${DEFAULT_REALM}/ucs_hub`;

// Build a per-user inbox topic, e.g., ucs://wave.tp/nova/inbox
export const inboxTopic = (handle: string) =>
  `ucs://${DEFAULT_REALM}/${handle}/inbox`;

// Deterministic dev owner WA (used by KG emitters, visits, etc.)
export const OWNER_WA: string =
  (typeof window !== "undefined" &&
    (window.localStorage?.getItem("gnet:ownerWa") ||
      window.localStorage?.getItem("gnet:wa") ||   // fallback to old key
      "").trim()) ||
  "dev@wave.tp"; // final fallback for dev