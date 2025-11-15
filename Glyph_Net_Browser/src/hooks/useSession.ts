import { useEffect, useState, useCallback } from "react";

export type Session = { slug: string; wa: string } | null;

export function useSession(pollMs = 4000) {
  const [session, setSession] = useState<Session>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch("/api/session/me", { credentials: "include" });
      const j = await r.json().catch(() => ({}));
      setSession(j?.session ?? null);
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try { await fetch("/api/session/logout", { method: "POST" }); } catch {}
    setSession(null);
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, pollMs);
    return () => clearInterval(t);
  }, [refresh, pollMs]);

  return { session, loading, refresh, logout };
}