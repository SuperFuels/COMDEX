import { useState, useCallback } from "react";

export default function PromptBar({
  containerId,
  onAfterAction,
}: {
  containerId: string;
  onAfterAction?: () => void;
}) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);

  async function postJSON(url: string, body: unknown) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`${r.status} ${r.statusText}${txt ? ` — ${txt}` : ""}`);
    }
    return r;
  }

  const run = useCallback(async () => {
    const t = value.trim();
    if (!t || !containerId || busy) return;

    setBusy(true);
    try {
      // ─────────────────────────────────────────
      // /wave <message> → send GIP frame
      // ─────────────────────────────────────────
      if (/^\/wave\b/i.test(t)) {
        const msg = t.replace(/^\/wave\s*/i, "") || "hello";

        const trace =
          (globalThis.crypto as Crypto)?.randomUUID?.() ||
          `${Date.now()}-${Math.random().toString(16).slice(2)}`;

        const frame = {
          hdr: {
            ver: 1,
            ts: Date.now(),
            trace,
            route: `ucs://${containerId}`,
            auth: { kid: "dev-hmac-1" },
          },
          body: { op: "wave", payload: { text: msg } },
          // sig: optional; backend may sign/verify in dev
        };

        // Prefer /api/gip/send/{id}; fall back to /api/gip/send if not available
        try {
          await postJSON(
            `/api/gip/send/${encodeURIComponent(containerId)}`,
            frame
          );
        } catch (e: any) {
          if (String(e?.message || "").startsWith("404")) {
            await postJSON(`/api/gip/send`, frame);
          } else {
            throw e;
          }
        }

        setValue("");
        onAfterAction?.();
        return;
      }

      // ─────────────────────────────────────────
      // /clear → wipe glyphs
      // ─────────────────────────────────────────
      if (/^\/clear\b/i.test(t)) {
        await postJSON(
          `/api/aion/container/save/${encodeURIComponent(containerId)}`,
          { id: containerId, type: "container", glyphs: [], meta: {} }
        );
        setValue("");
        onAfterAction?.();
        return;
      }

      // ─────────────────────────────────────────
      // /inject <text> → add one glyph (⊕)
      // ─────────────────────────────────────────
      if (/^\/inject\b/i.test(t)) {
        const text = t.replace(/^\/inject\s*/i, "") || "hello";
        await postJSON(
          `/api/aion/container/inject-glyphs/${encodeURIComponent(
            containerId
          )}`,
          {
            glyphs: [{ id: `g-${Date.now()}`, symbol: "⊕", text }],
          }
        );
        setValue("");
        onAfterAction?.();
        return;
      }

      // ─────────────────────────────────────────
      // Plain text → inject as ⊕ glyph
      // ─────────────────────────────────────────
      await postJSON(
        `/api/aion/container/inject-glyphs/${encodeURIComponent(containerId)}`,
        {
          glyphs: [{ id: `g-${Date.now()}`, symbol: "⊕", text: t }],
        }
      );
      setValue("");
      onAfterAction?.();
    } catch (e) {
      console.warn("PromptBar action failed:", e);
    } finally {
      setBusy(false);
    }
  }, [value, containerId, busy, onAfterAction]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    run();
  };

  return (
    <form onSubmit={onSubmit} style={{ display: "flex", gap: 8 }}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Type… (/wave hello, /inject hi, /clear)"
        style={{
          width: "100%",
          padding: "8px 10px",
          borderRadius: 6,
          border: "1px solid #e5e7eb",
          outline: "none",
        }}
      />
      <button
        type="submit"
        disabled={busy}
        style={{
          padding: "6px 12px",
          borderRadius: 6,
          border: "1px solid #e5e7eb",
          background: busy ? "#e2e8f0" : "#fff",
          cursor: busy ? "not-allowed" : "pointer",
        }}
      >
        {busy ? "Sending…" : "Send"}
      </button>
    </form>
  );
}