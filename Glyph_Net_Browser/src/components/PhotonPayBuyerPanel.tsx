// src/components/PhotonPayBuyerPanel.tsx
import { useState } from "react";
import { QrReader } from "react-qr-reader";
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

type DevPhotonReceipt = {
  receipt_id: string;
  from_account: string;
  to_account: string;
  amount_pho: string;
  memo?: string | null;
  channel: string;
  invoice_id?: string | null;
  created_at_ms: number;
};

export default function PhotonPayBuyerPanel() {
  const [raw, setRaw] = useState<string>("");
  const [payload, setPayload] = useState<PhotonPayPayload | null>(null);
  const [parseErr, setParseErr] = useState<string | null>(null);
  const [payChannel, setPayChannel] = useState<"mesh" | "net">("mesh");

  const [payBusy, setPayBusy] = useState<boolean>(false);
  const [payMsg, setPayMsg] = useState<string | null>(null);
  const [payErr, setPayErr] = useState<string | null>(null);
  const [lastReceipt, setLastReceipt] = useState<DevPhotonReceipt | null>(null);

  const [glyphString, setGlyphString] = useState("");
  const [scannerOpen, setScannerOpen] = useState(false);
  const [hasScanned, setHasScanned] = useState(false);

  // Wave / “To” resolution state
  const [toInput, setToInput] = useState<string>("");
  const [resolvedContact, setResolvedContact] = useState<WaveContact | null>(
    null,
  );
  const [resolving, setResolving] = useState(false);
  const [resolveErr, setResolveErr] = useState<string | null>(null);

  const buyerAccount = "pho1-demo-offline"; // dev-only buyer

  async function loadInvoiceFromString(src: string) {
    setParseErr(null);
    setPayMsg(null);
    setPayErr(null);
    setLastReceipt(null);

    const trimmed = src.trim();
    if (!trimmed) {
      setParseErr("Paste an invoice JSON or glyph string first.");
      return;
    }

    // 1) Try direct JSON
    try {
      const obj = JSON.parse(trimmed);
      if (!obj || obj.kind !== "INVOICE_POS" || !obj.invoice) {
        throw new Error("Not an INVOICE_POS payload");
      }

      const inv = obj.invoice as PhotonInvoice;
      const initialTo =
        inv.seller_wave_addr ||
        inv.seller_account ||
        "";
      setToInput(initialTo);
      setPayload(obj as PhotonPayPayload);
      return;
    } catch {
      // fall through to base64 / glyph decode
    }

    // 2) If it’s base64-encoded JSON (e.g. from a QR scanner)
    try {
      const decoded = atob(trimmed);
      const obj = JSON.parse(decoded);
      if (!obj || obj.kind !== "INVOICE_POS" || !obj.invoice) {
        throw new Error("Not an INVOICE_POS payload");
      }

      const inv = obj.invoice as PhotonInvoice;
      const initialTo =
        inv.seller_wave_addr ||
        inv.seller_account ||
        "";
      setToInput(initialTo);
      setPayload(obj as PhotonPayPayload);
      return;
    } catch (e: any) {
      console.error("[PhotonPayBuyer] decode failed:", e);
      setParseErr(
        e?.message || "Failed to decode invoice from string/QR",
      );
    }
  }

  function handleLoad() {
    void loadInvoiceFromString(raw);
  }

  async function handleLoadFromGlyph() {
    setParseErr(null);

    const src = glyphString.trim();
    if (!src) {
      setParseErr("Paste a QR / glyph string first.");
      return;
    }

    let decoded = src;

    // Very simple dev stub:
    //  - if it already looks like JSON, use as-is
    //  - otherwise, try base64 → JSON
    if (!(src.startsWith("{") || src.startsWith("["))) {
      try {
        decoded = atob(src);
      } catch {
        decoded = src;
      }
    }

    // Mirror into the main textarea so you can see the JSON
    setRaw(decoded);

    await loadInvoiceFromString(decoded);
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

  // --- Shared pay helper (mesh / NET) --------------------------------------

  async function payInvoice(channel: "mesh" | "net") {
    if (!payload?.invoice) return;

    const inv = payload.invoice;

    setPayBusy(true);
    setPayMsg(null);
    setPayErr(null);
    setLastReceipt(null);

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

      const baseBody = {
        from_account: buyerAccount,
        to_account: destAccount,
        amount_pho: inv.amount_pho,
        memo: inv.memo || undefined,
      };

      if (channel === "net") {
        // 🔵 Online: move PHO via wallet engine
        const resp = await fetch("/api/wallet/dev/transfer", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(baseBody),
        });
        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(txt || `HTTP ${resp.status}`);
        }
        await resp.json().catch(() => undefined);
      } else {
        // 🌐 Mesh / offline: local mesh send
        const resp = await fetch("/api/mesh/local_send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(baseBody),
        });
        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(txt || `HTTP ${resp.status}`);
        }
        await resp.json().catch(() => undefined);
      }

      // 📜 Log Photon Pay receipt (same engine as docs)
      let receipt: DevPhotonReceipt | null = null;
      try {
        const rRes = await fetch("/api/photon_pay/dev/receipts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            from_account: buyerAccount,
            channel, // "mesh" or "net"
            invoice: inv,
            to_account: destAccount,
            amount_pho: inv.amount_pho,
            memo: inv.memo || undefined,
          }),
        });
        if (rRes.ok) {
          const rJson = await rRes.json();
          receipt = rJson.receipt as DevPhotonReceipt;
          setLastReceipt(receipt);
        }
      } catch (e) {
        console.warn("[PhotonPayBuyerPanel] dev receipt record failed:", e);
      }

      const label =
        resolvedContact?.display_name ||
        resolvedContact?.pho_account ||
        destAccount;

      const chLabel = channel === "net" ? "NET" : "mesh";
      const baseMsg = `Paid ${inv.amount_pho} PHO → ${label} for "${
        inv.memo || "invoice"
      }" (${chLabel})`;

      if (receipt) {
        setPayMsg(`${baseMsg} · receipt: ${receipt.receipt_id}`);
      } else {
        setPayMsg(baseMsg);
      }
    } catch (e: any) {
      console.error("[PhotonPayBuyerPanel] pay failed:", e);
      setPayErr(e?.message || "Payment failed");
    } finally {
      setPayBusy(false);
    }
  }

  async function handlePay() {
    await payInvoice(payChannel);
  }

  // --- Derived state + UI ---------------------------------------------------

  const invoice = payload?.invoice;
  const nowMs = Date.now();
  const isExpired =
    invoice && typeof invoice.expiry_ms === "number"
      ? nowMs > invoice.expiry_ms
      : false;

  const selfPayWarning =
    invoice && invoice.seller_account === buyerAccount;

  const payDisabled =
    !invoice || payBusy || isExpired || !buyerAccount || selfPayWarning;

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
            destination, then pay over mesh or NET.
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
          onChange={(e) => {
            setRaw(e.target.value);
            setParseErr(null);
            setPayErr(null);
            setPayMsg(null);
          }}
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

        {/* QR / glyph string stub */}
        <div
          style={{
            marginTop: 6,
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
            alignItems: "center",
          }}
        >
          <input
            type="text"
            value={glyphString}
            onChange={(e) => setGlyphString(e.target.value)}
            placeholder="Paste QR / glyph string (base64 or JSON)…"
            style={{
              flex: 1,
              minWidth: 220,
              padding: "4px 8px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 11,
            }}
          />
          <button
            type="button"
            onClick={handleLoadFromGlyph}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: "#0f172a",
              color: "#f9fafb",
              fontSize: 11,
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            Decode &amp; load
          </button>

          {/* NEW: Scan QR button */}
          <button
            type="button"
            onClick={() => {
              setScannerOpen(true);
              setHasScanned(false);
              setParseErr(null);
            }}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              color: "#111827",
              fontSize: 11,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            Scan QR
          </button>
        </div>

        {/* NEW: Inline QR scanner */}
        {scannerOpen && (
          <div
            style={{
              marginTop: 8,
              padding: 8,
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
            }}
          >
            <div
              style={{
                fontSize: 11,
                color: "#6b7280",
                marginBottom: 4,
              }}
            >
              Point your camera at a PhotonPay invoice QR. We’ll decode it into
              the JSON box above.
            </div>

            <div
              style={{
                width: "100%",
                maxWidth: 260,
                margin: "0 auto",
                borderRadius: 12,
                overflow: "hidden",
              }}
            >
              <QrReader
                constraints={{ facingMode: "environment" }}
                onResult={async (result: any, error: any) => {
                  if (!result || hasScanned) return;
                  const text = result?.text || result?.getText?.();
                  if (!text) return;

                  setHasScanned(true);
                  setScannerOpen(false);

                  // Mirror into glyph string + textarea for visibility
                  setGlyphString(text);
                  setRaw(text);

                  await loadInvoiceFromString(text);
                }}
                containerStyle={{ width: "100%" }}
                videoStyle={{ width: "100%" }}
              />
            </div>

            <button
              type="button"
              onClick={() => setScannerOpen(false)}
              style={{
                marginTop: 8,
                padding: "4px 10px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                background: "#ffffff",
                fontSize: 11,
                cursor: "pointer",
              }}
            >
              Close scanner
            </button>
          </div>
        )}

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

            {selfPayWarning && (
              <div
                style={{
                  fontSize: 11,
                  color: "#b91c1c",
                  marginTop: 4,
                }}
              >
                Warning: buyer and seller accounts are the same
                ({buyerAccount}). This is usually not what you want.
              </div>
            )}

            {/* Channel selector: online vs mesh */}
            <div
              style={{
                marginTop: 6,
                display: "flex",
                gap: 12,
                fontSize: 11,
                color: "#4b5563",
              }}
            >
              <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <input
                  type="radio"
                  checked={payChannel === "net"}
                  onChange={() => setPayChannel("net")}
                  disabled={isExpired}
                />
                Online (wallet / net)
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <input
                  type="radio"
                  checked={payChannel === "mesh"}
                  onChange={() => setPayChannel("mesh")}
                  disabled={isExpired}
                />
                Offline mesh
              </label>
            </div>
          

            {/* Pay button + status */}
            <div
              style={{
                marginTop: 8,
                display: "flex",
                gap: 8,
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              <button
                type="button"
                onClick={handlePay}
                disabled={payDisabled}
                style={{
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
                  : payChannel === "net"
                  ? "Pay online (wallet)"
                  : "Pay over mesh"}
              </button>
            </div>

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

            {lastReceipt && (
              <div
                style={{
                  fontSize: 10,
                  color: "#6b7280",
                  marginTop: 4,
                }}
              >
                Latest receipt:{" "}
                <code>{lastReceipt.receipt_id}</code> ·{" "}
                {lastReceipt.amount_pho} PHO → {lastReceipt.to_account} (
                {lastReceipt.channel})
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}