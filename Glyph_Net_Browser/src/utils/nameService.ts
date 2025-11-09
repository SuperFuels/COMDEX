// Single source of truth for WA/WN name helpers

export type GraphKey = "personal" | "work";

export function canonKG(s?: string): GraphKey {
  const v = (s || "personal").toLowerCase();
  return v === "work" ? "work" : "personal";
}

export function toWA(input: string, kg: GraphKey): string {
  // Accept already-canonical URIs
  if (input.startsWith("ucs://")) return input;
  // Accept "label@kg" too; we only need the label here
  const [labelMaybe] = input.split("@");
  const realm = "wave.tp"; // dev realm (make configurable if you like)
  return `ucs://${realm}/${labelMaybe}`;
}

/**
 * Resolve a human input ("kevin@work" or "ucs://...") to a canonical WA string,
 * and return the display label used in the UI.
 */
export async function resolveLabelToWA(
  base: string,
  kg: GraphKey,
  input: string
): Promise<{ wa: string; label: string }> {
  if (input.startsWith("ucs://")) {
    return { wa: input, label: input.replace(/^ucs:\/\/[^/]+\//, "") };
  }
  const label = input.split("@")[0];

  try {
    const r = await fetch(
      `${base}/api/name/resolve?kg=${encodeURIComponent(kg)}&label=${encodeURIComponent(label)}`
    );
    const j = await r.json();
    if (j?.wa) return { wa: j.wa, label };
  } catch {
    /* ignore; fall through to synth */
  }

  // Fallback: synthesize WA from label
  return { wa: toWA(input, kg), label };
}