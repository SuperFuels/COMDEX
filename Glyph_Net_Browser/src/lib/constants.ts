// Default realm + helpers for GlyphNet addresses
export const DEFAULT_REALM = "wave.tp";

// Public hub topic (good default for inbox/outbox testing)
export const DEFAULT_TOPIC = `ucs://${DEFAULT_REALM}/ucs_hub`;

// Build a per-user inbox topic, e.g., ucs://wave.tp/nova/inbox
export const inboxTopic = (handle: string) =>
  `ucs://${DEFAULT_REALM}/${handle}/inbox`;