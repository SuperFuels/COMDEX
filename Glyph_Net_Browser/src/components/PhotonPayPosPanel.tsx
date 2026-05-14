// src/components/PhotonPayPosPanel.tsx
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

export default function PhotonPayPosPanel() {
  const [amount, setAmount] = useState<string>("5.00");
  const [memo, setMemo] = useState<string>("Coffee");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<PhotonPayPayload | null>(null);

  async function handleGenerate() {
    if (!amount || Number(amount) <= 0) {
      setError("Enter a valid amount.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Dev-only endpoint.
      // Right now the backend demo returns a fixed invoice (5 PHO / Coffee).
      // Later we can extend it to accept amount/memo as params or POST body.
      const resp = await fetch("/api/photon_pay/dev/demo_invoice");
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const data: PhotonPayPayload = await resp.json();
      setPayload(data);
    } catch (e: any) {
      console.error("[PhotonPayPosPanel] generate invoice failed:", e);
      setError(e?.message || "Failed to generate invoice");
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }

  const invoice = payload?.invoice;

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
            Photon Pay – POS (dev)
          </div>
          <div
            style={{
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            Type an amount + memo, generate a Photon invoice payload.
          </div>
        </div>
      </header>

      {/* POS keypad-ish row */}
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
          New charge
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <div
            style={{
              fontSize: 20,
              fontWeight: 500,
              color: "#111827",
            }}
          >
            PHO
          </div>
          <input
            type="number"
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
            style={{
              flex: 1,
              maxWidth: 140,
              padding: "7px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 16,
              textAlign: "right",
            }}
          />
        </div>

        <input
          type="text"
          value={memo}
          onChange={(e) => setMemo(e.target.value)}
          placeholder="Memo (e.g. Coffee)"
          style={{
            marginTop: 4,
            padding: "7px 12px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            fontSize: 13,
          }}
        />

        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading || !amount || Number(amount) <= 0}
          style={{
            marginTop: 4,
            alignSelf: "flex-start",
            padding: "8px 16px",
            borderRadius: 999,
            border: "1px solid #0f172a",
            background: "#0f172a",
            color: "#f9fafb",
            fontSize: 13,
            fontWeight: 600,
            cursor:
              loading || !amount || Number(amount) <= 0 ? "default" : "pointer",
            opacity:
              loading || !amount || Number(amount) <= 0 ? 0.6 : 1,
          }}
        >
          {loading ? "Generating…" : "Generate invoice"}
        </button>

        {error && (
          <div
            style={{
              fontSize: 11,
              color: "#b91c1c",
            }}
          >
            {error}
          </div>
        )}
      </section>

      {/* Generated invoice + glyph placeholder */}
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
          Generated invoice
        </div>

        {!invoice ? (
          <div
            style={{
              fontSize: 11,
              color: "#9ca3af",
            }}
          >
            No invoice yet. Enter an amount and click{" "}
            <strong>Generate invoice</strong>.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 12,
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
                  {new Date(invoice.expiry_ms).toLocaleString()}
                </div>
              </div>
            </div>

            {/* Glyph / QR placeholder */}
            <div
              style={{
                marginTop: 8,
                padding: 12,
                borderRadius: 12,
                border: "1px dashed #d1d5db",
                background: "#f9fafb",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: 120,
              }}
            >
              <div
                style={{
                  textAlign: "center",
                  fontSize: 11,
                  color: "#6b7280",
                }}
              >
                <div
                  style={{
                    fontSize: 24,
                    marginBottom: 4,
                  }}
                >
                  ▢
                </div>
                <div>GlyphCode / QR preview (coming later)</div>
                <div style={{ marginTop: 2, fontSize: 10, color: "#9ca3af" }}>
                  Will encode <code>PhotonPayPayload</code> for buyers to scan.
                </div>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}