import { useEffect, useState } from "react";

type RadioHealth = {
  profile?: string;
  active?: { MTU?: number; RATE_HZ?: number };
  rfQueue?: number;
  rfOutbox?: number;
};

export function useRadioHealth(pollMs = 4000) {
  const [radio, setRadio] = useState<RadioHealth | null>(null);

  useEffect(() => {
    let stop = false;
    let t: any;
    // Allow overriding the base in localStorage; fallback to local radio-node
    const base =
      localStorage.getItem("gnet:radioNodeBase") || "http://127.0.0.1:8787";

    const tick = async () => {
      try {
        const r = await fetch(`${base}/health`, { cache: "no-store" });
        if (r.ok) {
          const j = await r.json();
          if (!stop) {
            setRadio({
              profile: j.profile,
              active: j.active,
              rfQueue: j.rfQueue,
              rfOutbox: j.rfOutbox,
            });
          }
        }
      } catch {
        if (!stop) setRadio(null); // offline
      }
      if (!stop) t = setTimeout(tick, pollMs);
    };

    tick();
    return () => {
      stop = true;
      if (t) clearTimeout(t);
    };
  }, [pollMs]);

  return radio;
}