// frontend/lib/containers.ts
export const RADIO_BASE =
  process.env.NEXT_PUBLIC_RADIO_BASE || ""; // e.g. https://radio-node.yourdomain.com

export function slugFromEmail(email: string): string {
  const name = String(email).split("@")[0] || email;
  return name.toLowerCase().replace(/[^a-z0-9._-]/g, "-");
}

export async function ensureContainersForWA(wa: string, allowReinit = false) {
  if (!RADIO_BASE) return; // no-op in preview if not configured
  try {
    await fetch(`${RADIO_BASE}/api/containers/bootstrap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wa, allowReinit }),
    });
  } catch (e) {
    console.warn("[containers/bootstrap] failed:", e);
  }
}