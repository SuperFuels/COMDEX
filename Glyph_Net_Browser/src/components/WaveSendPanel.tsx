// src/components/WaveSendPanel.tsx
import { useState } from "react";

type WaveContact = {
  pho_account: string;
  wave_addr: string;
  wave_number: string;
  display_name: string;
  avatar_url?: string | null;
};

export default function WaveSendPanel() {
  const [fromAccount, setFromAccount] = useState<string>("pho1-demo-offline");
  const [toInput, setToInput] = useState<string>("receiver@glyph.local"); // can be wave addr / number / PHO
  const [amountPho, setAmountPho] = useState<string>("1");

  const [resolvedContact, setResolvedContact] = useState<WaveContact | null>(
    null,
  );
  const [resolving, setResolving] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);

  const [sending, setSending] = useState(false);
  const [sendMsg, setSendMsg] = useState<string | null>(null);
  const [sendErr, setSendErr] = useState<string | null>(null);

  // Infer which query param to use from the input shape
  function buildResolveQuery(input: string): string {
    const trimmed = input.trim();
    const params = new URLSearchParams();

    if (!trimmed) return "";

    if (trimmed.includes("@")) {
      params.set("wave_addr", trimmed);
    } else if (trimmed.startsWith("+wave-")) {
      params.set("wave_number", trimmed);
    } else {
      params.set("pho_account", trimmed);
    }

    return params.toString();
  }

  async function handleResolve() {
    setResolvedContact(null);
    setResolveError(null);
    setSendMsg(null);
    setSendErr(null);

    const qs = buildResolveQuery(toInput);
    if (!qs) {
      setResolveError("Enter a Wave address, Wave number, or PHO account first.");
      return;
    }

    setResolving(true);

    try {
      const resp = await fetch(`/api/wave/dev/resolve?${qs}`);
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      const contact: WaveContact = data.contact;

      setResolvedContact(contact);
    } catch (e: any) {
      console.error("[WaveSendPanel] resolve failed:", e);
      setResolveError(e?.message || "Failed to resolve Wave address/number");
    } finally {
      setResolving(false);
    }
  }

  async function handleSend() {
    setSending(true);
    setSendMsg(null);
    setSendErr(null);

    try {
      if (!amountPho || Number(amountPho) <= 0) {
        throw new Error("Enter a positive amount.");
      }

      let destAccount = resolvedContact?.pho_account;

      // If user hasn't resolved yet, try a best-effort inline resolve.
      if (!destAccount) {
        const qs = buildResolveQuery(toInput);
        if (qs) {
          try {
            const resp = await fetch(`/api/wave/dev/resolve?${qs}`);
            if (resp.ok) {
              const data = await resp.json();
              destAccount = data.contact?.pho_account || destAccount;
            }
          } catch {
            // ignore, we'll fall back to raw input
          }
        }
      }

      if (!destAccount) {
        // final fallback: treat toInput as a raw PHO account
        destAccount = toInput.trim();
      }

      const body = {
        from_account: fromAccount.trim(),
        to_account: destAccount.trim(),
        amount_pho: amountPho.trim(),
      };

      const resp = await fetch("/api/mesh/local_send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      await resp.json(); // we don't need specific details yet

      const label =
        resolvedContact?.display_name || resolvedContact?.pho_account || destAccount;

      setSendMsg(
        `Sent ${amountPho} PHO → ${label} (${destAccount}) over mesh.`,
      );
    } catch (e: any) {
      console.error("[WaveSendPanel] send failed:", e);
      setSendErr(e?.message || "Mesh send failed");
    } finally {
      setSending(false);
    }
  }

  const resolvedLabel = resolvedContact
    ? `${resolvedContact.display_name} • ${resolvedContact.pho_account}`
    : null;

  return (
    <div
      style={{
        maxWidth: 520,
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: "#0f172a",
            }}
          >
            Photon Pay – P2P Wave send (dev)
          </div>
          <div
            style={{
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            Type a Wave address / Wave number / PHO account, resolve, then send
            PHO over mesh.
          </div>
        </div>
      </header>

      {/* From / To / Amount */}
      <section
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <div
          style={{
            fontSize: 12,
            color: "#6b7280",
          }}
        >
          From account (PHO)
        </div>
        <input
          type="text"
          value={fromAccount}
          onChange={(e) => setFromAccount(e.target.value)}
          style={{
            padding: "7px 12px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            fontSize: 13,
          }}
        />

        <div
          style={{
            marginTop: 8,
            fontSize: 12,
            color: "#6b7280",
          }}
        >
          To (Wave address / Wave number / PHO)
        </div>
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <input
            type="text"
            value={toInput}
            onChange={(e) => {
              setToInput(e.target.value);
              setResolvedContact(null);
              setResolveError(null);
            }}
            placeholder="e.g. cafe@glyph.local or +wave-44-1000-0001"
            style={{
              flex: 1,
              padding: "7px 12px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 13,
            }}
          />
          <button
            type="button"
            onClick={handleResolve}
            disabled={resolving || !toInput.trim()}
            style={{
              padding: "7px 14px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: "#0f172a",
              color: "#f9fafb",
              fontSize: 12,
              fontWeight: 600,
              cursor: resolving || !toInput.trim() ? "default" : "pointer",
              opacity: resolving || !toInput.trim() ? 0.6 : 1,
            }}
          >
            {resolving ? "Resolving…" : "Resolve"}
          </button>
        </div>

        {resolvedLabel && (
          <div
            style={{
              marginTop: 4,
              fontSize: 11,
              color: "#15803d",
            }}
          >
            Resolved: {resolvedLabel}
          </div>
        )}
        {resolveError && (
          <div
            style={{
              marginTop: 4,
              fontSize: 11,
              color: "#b91c1c",
            }}
          >
            {resolveError}
          </div>
        )}

        <div
          style={{
            marginTop: 12,
            fontSize: 12,
            color: "#6b7280",
          }}
        >
          Amount (PHO)
        </div>
        <input
          type="number"
          inputMode="decimal"
          value={amountPho}
          onChange={(e) => setAmountPho(e.target.value)}
          style={{
            maxWidth: 120,
            padding: "7px 10px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            fontSize: 14,
            textAlign: "right",
          }}
        />

        <button
          type="button"
          onClick={handleSend}
          disabled={sending || !amountPho || Number(amountPho) <= 0}
          style={{
            marginTop: 12,
            alignSelf: "flex-start",
            padding: "8px 18px",
            borderRadius: 999,
            border: "1px solid #0f172a",
            background: "#0f172a",
            color: "#f9fafb",
            fontSize: 13,
            fontWeight: 600,
            cursor:
              sending || !amountPho || Number(amountPho) <= 0
                ? "default"
                : "pointer",
            opacity:
              sending || !amountPho || Number(amountPho) <= 0
                ? 0.6
                : 1,
          }}
        >
          {sending ? "Sending…" : "Send over mesh"}
        </button>

        {sendMsg && (
          <div
            style={{
              marginTop: 4,
              fontSize: 11,
              color: "#15803d",
            }}
          >
            {sendMsg}
          </div>
        )}
        {sendErr && (
          <div
            style={{
              marginTop: 4,
              fontSize: 11,
              color: "#b91c1c",
            }}
          >
            {sendErr}
          </div>
        )}
      </section>
    </div>
  );
}