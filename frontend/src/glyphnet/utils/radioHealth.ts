import { radioBase } from "@glyphnet/utils/transport";
export type RadioHealth = { profile: string; active: { MTU: number; RATE_HZ: number }; rfQueue: number; rfOutbox: number; ok: boolean };
export async function getRadioHealth(): Promise<RadioHealth | null> {
  try {
    const r = await fetch(`${radioBase()}/health`, { cache: "no-store" });
    return await r.json();
  } catch { return null; }
}