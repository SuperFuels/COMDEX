// src/components/PhotonPayBuyerPanel.tsx
import { useState } from "react";

type PhotonInvoice = {
  invoice_id: string;
  seller_account: string;
  seller_wave_addr?: string | null;
  amount_pho: string;
  fiat_symbol?: string | null;
  fiat_amount?: string | null;
  memo?: string | null;
  created_at_ms: number;
  expiry_ms: number;
};

type PhotonPayPayload = {
  version: number;
  kind: "INVOICE_POS";
  invoice: PhotonInvoice;
};

type WaveContact = {
  pho_account: string;
  wave_addr?: string | null;
  wave_number?: string | null;
  display_name?: string | null;
  avatar_url?: string | null;
};

export default function PhotonPayBuyerPanel() {
  const [raw, setRaw] = useState<string>("");
  const [payload, setPayload] = useState<PhotonPayPayload | null>(null);
  const [parseErr, setParseErr] = useState<string | null>(null);

  const [payBusy, setPayBusy] = useState<boolean>(false);
  const [payMsg, setPayMsg] = useState<string | null>(null);
  const [payErr, setPayErr] = useState<string | null>(null);

  // Wave / “To” resolution state
  const [toInput, setToInput] = useState<string>("");
  const [resolvedContact, setResolvedContact] = useState<WaveContact | null>(
    null,
  );
  const [resolving, setResolving] = useState(false);
  const [resolveErr, setResolveErr] = useState<string | null>(null);

  const buyerAccount = "pho1-demo-offline"; // dev-only buyer

  function handleLoad() {
    setParseErr(null);
    setPayload(null);
    setPayMsg(null);
    setPayErr(null);
    setResolvedContact(null);
    setResolveErr(null);

    if (!raw.trim()) {
      setParseErr("Paste a PhotonPay invoice payload first.");
      return;
    }

    try {
      const obj = JSON.parse(raw);

      if (!obj || obj.kind !== "INVOICE_POS" || !obj.invoice) {
        throw new Error("Not an INVOICE_POS payload");
      }

      const inv = obj.invoice as PhotonInvoice;

      // Pre-fill "To" with seller wave addr (if present) or seller account
      const initialTo =
        inv.seller_wave_addr ||
        inv.seller_account ||
        "";
      setToInput(initialTo);

      setPayload(obj as PhotonPayPayload);
    } catch (e: any) {
      console.error("[PhotonPayBuyerPanel] parse failed:", e);
      setParseErr(e?.message || "Failed to parse payload JSON");
    }
  }

  // --- Wave resolve helpers -------------------------------------------------

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
    setResolveErr(null);
    setPayMsg(null);
    setPayErr(null);

    const qs = buildResolveQuery(toInput);
    if (!qs) {
      setResolveErr(
        "Enter a Wave address, Wave number, or PHO account first.",
      );
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
      console.error("[PhotonPayBuyerPanel] resolve failed:", e);
      setResolveErr(e?.message || "Failed to resolve Wave address/number");
    } finally {
      setResolving(false);
    }
  }

  // --- Pay ------------------------------------------------------------------

  async function handlePay() {
    if (!payload?.invoice) return;

    const inv = payload.invoice;

    setPayBusy(true);
    setPayMsg(null);
    setPayErr(null);

    try {
      // Decide destination account:
      //  1) resolved pho_account (if any)
      //  2) best-effort inline resolve
      //  3) invoice.seller_account
      //  4) raw toInput as PHO account
      let destAccount: string | undefined = resolvedContact?.pho_account;

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
            // ignore, we'll fall back
          }
        }
      }

      if (!destAccount) {
        destAccount = inv.seller_account || toInput.trim();
      }

      // 1) actually send PHO over mesh
      const resp = await fetch("/api/mesh/local_send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_account: buyerAccount,
          to_account: destAccount,
          amount_pho: inv.amount_pho,
        }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      await resp.json(); // we don't need body details yet

      // 2) fire-and-forget dev receipt record (ignore failures)
      try {
        await fetch("/api/photon_pay/dev/receipts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            from_account: buyerAccount,
            channel: "mesh",
            invoice: inv,
          }),
        });
      } catch (e) {
        console.warn("[PhotonPayBuyerPanel] dev receipt record failed:", e);
      }

      const label =
        resolvedContact?.display_name ||
        resolvedContact?.pho_account ||
        destAccount;

      setPayMsg(
        `Paid ${inv.amount_pho} PHO → ${label} for "${
          inv.memo || "invoice"
        }" (mesh)`,
      );
    } catch (e: any) {
      console.error("[PhotonPayBuyerPanel] pay failed:", e);
      setPayErr(e?.message || "Payment failed");
    } finally {
      setPayBusy(false);
    }
  }

  const invoice = payload?.invoice;
  const nowMs = Date.now();
  const isExpired =
    invoice && typeof invoice.expiry_ms === "number"
      ? nowMs > invoice.expiry_ms
      : false;

  const payDisabled =
    !invoice || payBusy || isExpired || !buyerAccount;

  const resolvedLabel = resolvedContact
    ? resolvedContact.display_name
      ? `${resolvedContact.display_name} • ${resolvedContact.pho_account}`
      : resolvedContact.pho_account
    : null;

  return (
    <div
      style={{
        maxWidth: 640,
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
            Photon Pay – Buyer (dev)
          </div>
          <div
            style={{
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            Paste a PhotonPay invoice payload (from POS or curl), resolve the
            destination, then pay over mesh.
          </div>
        </div>
      </header>

      {/* Paste area */}
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
          1. Paste PhotonPay payload (JSON)
        </div>

        <textarea
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder='Paste output of /api/photon_pay/dev/demo_invoice or POS payload here…'
          rows={8}
          style={{
            width: "100%",
            padding: "8px 10px",
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            fontFamily: "monospace",
            fontSize: 11,
            resize: "vertical",
          }}
        />

        <button
          type="button"
          onClick={handleLoad}
          style={{
            alignSelf: "flex-start",
            padding: "6px 14px",
            borderRadius: 999,
            border: "1px solid #0f172a",
            background: "#0f172a",
            color: "#f9fafb",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Load invoice
        </button>

        {parseErr && (
          <div
            style={{
              fontSize: 11,
              color: "#b91c1c",
            }}
          >
            {parseErr}
          </div>
        )}
      </section>

      {/* Loaded invoice + pay button */}
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
            fontWeight: 600,
            color: "#0f172a",
          }}
        >
          2. Review, resolve & pay
        </div>

        {!invoice ? (
          <div
            style={{
              fontSize: 11,
              color: "#9ca3af",
            }}
          >
            No invoice loaded yet.
          </div>
        ) : (
          <>
            {/* Invoice summary */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 16,
                fontSize: 11,
                color: "#4b5563",
              }}
            >
              <div>
                <div style={{ color: "#6b7280" }}>Invoice ID</div>
                <div>{invoice.invoice_id}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Seller account</div>
                <div>{invoice.seller_account}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Amount (PHO)</div>
                <div>{invoice.amount_pho}</div>
              </div>
              {invoice.memo && (
                <div>
                  <div style={{ color: "#6b7280" }}>Memo</div>
                  <div>{invoice.memo}</div>
                </div>
              )}
              <div>
                <div style={{ color: "#6b7280" }}>Expires</div>
                <div>
                  {new Date(invoice.expiry_ms).toLocaleString()}{" "}
                  {isExpired && (
                    <span style={{ color: "#b91c1c" }}>(expired)</span>
                  )}
                </div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Buyer (dev)</div>
                <div>{buyerAccount}</div>
              </div>
            </div>

            {/* To: Wave / PHO destination */}
            <div style={{ marginTop: 8 }}>
              <div
                style={{
                  fontSize: 11,
                  color: "#6b7280",
                  marginBottom: 4,
                }}
              >
                To (Wave address / Wave number / PHO)
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "center",
                  marginBottom: 4,
                }}
              >
                <input
                  type="text"
                  value={toInput}
                  onChange={(e) => {
                    setToInput(e.target.value);
                    setResolvedContact(null);
                    setResolveErr(null);
                  }}
                  placeholder={
                    invoice.seller_wave_addr ||
                    "e.g. cafe@glyph.local or +wave-44-1000-0001"
                  }
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
                    cursor:
                      resolving || !toInput.trim() ? "default" : "pointer",
                    opacity: resolving || !toInput.trim() ? 0.6 : 1,
                  }}
                >
                  {resolving ? "Resolving…" : "Resolve"}
                </button>
              </div>

              {resolvedLabel && (
                <div
                  style={{
                    fontSize: 11,
                    color: "#15803d",
                  }}
                >
                  Resolved: {resolvedLabel}
                </div>
              )}

              {resolveErr && (
                <div
                  style={{
                    fontSize: 11,
                    color: "#b91c1c",
                  }}
                >
                  {resolveErr}
                </div>
              )}
            </div>

            {/* Pay button + status */}
            <button
              type="button"
              onClick={handlePay}
              disabled={payDisabled}
              style={{
                marginTop: 8,
                alignSelf: "flex-start",
                padding: "8px 18px",
                borderRadius: 999,
                border: "1px solid #0f172a",
                background: "#0f172a",
                color: "#f9fafb",
                fontSize: 13,
                fontWeight: 600,
                cursor: payDisabled ? "default" : "pointer",
                opacity: payDisabled ? 0.6 : 1,
              }}
            >
              {isExpired
                ? "Invoice expired"
                : payBusy
                ? "Paying…"
                : "Pay over mesh"}
            </button>

            {payMsg && (
              <div
                style={{
                  fontSize: 11,
                  color: "#15803d",
                  marginTop: 4,
                }}
              >
                {payMsg}
              </div>
            )}
            {payErr && (
              <div
                style={{
                  fontSize: 11,
                  color: "#b91c1c",
                  marginTop: 4,
                }}
              >
                {payErr}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}