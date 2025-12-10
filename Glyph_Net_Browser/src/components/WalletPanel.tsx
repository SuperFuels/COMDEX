import { useEffect, useState } from "react";

type Balances = {
  pho: string;                 // displayed PHO (after mesh + safety buffer)
  pho_global?: string;         // raw on-chain PHO (optional)
  tess: string;
  bonds: string;
  mesh_offline_limit_pho?: string;
  mesh_pending_pho?: string;
};

type MeshTxEntry = {
  mesh_tx_id?: string;
  cluster_id?: string;
  from_account: string;
  to_account: string;
  amount_pho: string;
  created_at_ms?: number;
  prev_local_seq?: number;
  sender_device_id?: string;
  sender_signature?: string;
};

export default function WalletPanel() {
  const [ownerWa, setOwnerWa] = useState<string | null>(null);
  const [phoAccount, setPhoAccount] = useState<string>("pho1-demo-offline");
  const [meshLog, setMeshLog] = useState<MeshTxEntry[]>([]);

  const [balances, setBalances] = useState<Balances>({
    pho: "0.00",
    tess: "0.00",
    bonds: "0.00",
  });
  const [offlineLimit, setOfflineLimit] = useState<string>("25.0");
  const [meshPending, setMeshPending] = useState<string>("0.00");
  const [loading, setLoading] = useState<boolean>(true);

  // dev mesh send controls
  const [meshTo, setMeshTo] = useState<string>("pho1receiver");
  const [meshAmount, setMeshAmount] = useState<string>("1");
  const [meshBusy, setMeshBusy] = useState<boolean>(false);
  const [meshMsg, setMeshMsg] = useState<string | null>(null);
  const [meshErr, setMeshErr] = useState<string | null>(null);

  // small helper so we can re-use after mesh sends
  async function refreshWalletBalances(waOverride?: string | null) {
    if (typeof window === "undefined") return;

    const headerWa =
      waOverride ??
      ownerWa ??
      localStorage.getItem("gnet:ownerWa") ??
      localStorage.getItem("gnet:wa") ??
      null;

    setLoading(true);

    try {
      // --- primary wallet summary ---
      const resp = await fetch("/api/wallet/balances", {
        headers: headerWa ? { "X-Owner-WA": headerWa } : {},
      });
      const data = await resp.json();

      const wa = data.owner_wa ?? headerWa ?? null;
      setOwnerWa(wa);

      const acct: string = data.pho_account || "pho1-demo-offline";
      setPhoAccount(acct);

      const b = data.balances || {};
      setBalances({
        // displayed PHO (global – pending – buffer)
        pho: b.pho ?? "0.00",
        // raw on-chain PHO (if backend exposes it)
        pho_global: b.pho_global ?? b.pho ?? "0.00",
        tess: b.tess ?? "0.00",
        bonds: b.bonds ?? "0.00",
      });
      setOfflineLimit(b.mesh_offline_limit_pho ?? "25.0");
      setMeshPending(b.mesh_pending_pho ?? "0.00");

      // --- mesh local_state for activity log + precise pending ---
      try {
        const resp2 = await fetch(
          `/api/mesh/local_state/${encodeURIComponent(acct)}`
        );
        if (resp2.ok) {
          const view = await resp2.json();
          const entries: MeshTxEntry[] =
            (view.tx_log && view.tx_log.entries) || [];
          setMeshLog(entries);

          if (view.mesh_pending_pho != null) {
            setMeshPending(String(view.mesh_pending_pho));
          }
        }
      } catch (e) {
        console.warn("[WalletPanel] mesh local_state fetch failed:", e);
      }
    } catch (e) {
      console.warn("[WalletPanel] using local demo balances:", e);
      setPhoAccount("pho1-demo-offline");
      setBalances({
        pho: "123.45",
        pho_global: "123.45",
        tess: "42.00",
        bonds: "3.00",
      });
      setOfflineLimit("25.0");
      setMeshPending("0.00");
      setMeshLog([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (typeof window === "undefined") return;

    const wa =
      localStorage.getItem("gnet:ownerWa") ||
      localStorage.getItem("gnet:wa") ||
      null;

    setOwnerWa(wa);
    void refreshWalletBalances(wa);
  }, []);

  async function handleMeshSend() {
    if (!phoAccount) return;
    if (!meshAmount || Number(meshAmount) <= 0) return;

    setMeshBusy(true);
    setMeshMsg(null);
    setMeshErr(null);

    try {
      const resp = await fetch("/api/mesh/local_send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_account: phoAccount,
          to_account: meshTo || "pho1receiver",
          amount_pho: meshAmount,
        }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      await resp.json(); // data is there if you want it later

      const to = meshTo || "pho1receiver";
      const amount = meshAmount;

      // success message
      setMeshMsg(`Sent ${amount} PHO → ${to} (local mesh)`);
      setMeshErr(null);

      // re-pull wallet view so PHO + mesh pending + log update
      await refreshWalletBalances(ownerWa);

      // 🔔 notify rest of app (TopBar) to refresh wallet summary
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("glyphnet:wallet:updated"));
      }
    } catch (e: any) {
      console.error("[WalletPanel] mesh send failed:", e);
      setMeshErr(e?.message || "Mesh send failed");
      setMeshMsg(null);
    } finally {
      setMeshBusy(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        maxWidth: 960,
      }}
    >
      {/* Header */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
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
            Wallet
          </div>
          <div
            style={{
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            PHO / TESS / Bonds balances and offline mesh credit.
          </div>
        </div>

        {ownerWa && (
          <div
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              fontSize: 11,
              color: "#4b5563",
              maxWidth: 260,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={ownerWa}
          >
            WA: <code>{ownerWa}</code>
          </div>
        )}
      </header>

      {/* Top row: PHO + Mesh credit */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1.4fr)",
          gap: 12,
        }}
      >
        {/* PHO balance card */}
        <div
          style={{
            borderRadius: 16,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            padding: 12,
          }}
        >
          <div
            style={{
              fontSize: 12,
              color: "#6b7280",
              marginBottom: 4,
            }}
          >
            PHO Balance
          </div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              color: "#0f172a",
            }}
          >
            {loading ? "…" : `${balances.pho} PHO`}
          </div>
          <div
            style={{
              marginTop: 4,
              fontSize: 11,
              color: "#9ca3af",
            }}
          >
            Account: <code>{phoAccount}</code>
          </div>
          <div
            style={{
              marginTop: 4,
              fontSize: 10,
              color: "#9ca3af",
            }}
          >
            Displayed PHO ≈ on-chain PHO − mesh pending − 1 PHO safety buffer.
          </div>
        </div>

        {/* Offline mesh credit card */}
        <div
          style={{
            borderRadius: 16,
            border: "1px solid #dbeafe",
            background: "#eff6ff",
            padding: 12,
          }}
        >
          <div
            style={{
              fontSize: 12,
              color: "#1d4ed8",
              marginBottom: 4,
            }}
          >
            Offline Mesh Credit
          </div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 600,
              color: "#1e3a8a",
            }}
          >
            {offlineLimit} PHO
          </div>
          <div
            style={{
              marginTop: 4,
              fontSize: 11,
              color: "#1d4ed8",
            }}
          >
            Available for local radio / BLE payments when the chain is offline.
          </div>
        </div>
      </section>

      {/* Secondary balances */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        <SmallBalanceCard
          label="TESS (Governance)"
          value={balances.tess}
          code="TESS"
          hint="Staking + governance power."
        />
        <SmallBalanceCard
          label="Glyph Bonds"
          value={balances.bonds}
          code="GBOND"
          hint="On-chain bond positions."
        />
        <SmallBalanceCard
          label="Mesh Pending"
          value={meshPending}
          code="PHO"
          hint="Local-only mesh tx awaiting reconciliation."
          tone="warning"
        />
      </section>

      {/* Swap strip – visual only, inspired by website navbar */}
      <section
        style={{
          marginTop: 4,
          borderRadius: 16,
          border: "1px dashed #e5e7eb",
          background: "#f9fafb",
          padding: 10,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "#6b7280",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>Swap (coming soon)</span>
          <span style={{ fontSize: 10, color: "#9ca3af" }}>
            PHO ↔ other assets via on-chain AMM
          </span>
        </div>

        <div
          style={{
            display: "flex",
            gap: 6,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <input
            type="number"
            inputMode="decimal"
            placeholder="0"
            disabled
            style={{
              width: 80,
              padding: "4px 6px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              fontSize: 12,
              background: "#f3f4f6",
            }}
          />
          <button
            type="button"
            disabled
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "4px 8px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              fontSize: 12,
              cursor: "default",
            }}
          >
            <span>PHO</span>
          </button>
          <span
            style={{
              fontSize: 16,
              color: "#9ca3af",
            }}
          >
            →
          </span>
          <input
            type="number"
            inputMode="decimal"
            placeholder="0"
            disabled
            style={{
              width: 80,
              padding: "4px 6px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              fontSize: 12,
              background: "#f3f4f6",
            }}
          />
          <button
            type="button"
            disabled
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "4px 8px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              fontSize: 12,
              cursor: "default",
            }}
          >
            <span>TESS</span>
          </button>
          <button
            type="button"
            disabled
            style={{
              marginLeft: "auto",
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: "#0f172a",
              color: "#e5e7eb",
              fontSize: 11,
              fontWeight: 500,
              cursor: "default",
              opacity: 0.5,
            }}
          >
            Swap soon
          </button>
        </div>
      </section>

      {/* Mesh payment dev box */}
      <section
        style={{
          marginTop: 8,
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 10,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 12,
            color: "#6b7280",
          }}
        >
          <span>Mesh payment (dev only)</span>
          <span style={{ fontSize: 11, color: "#9ca3af" }}>
            Uses <code>/api/mesh/local_send</code> +{" "}
            <code>/api/mesh/local_state</code>
          </span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 2,
          }}
        >
          {/* To-address */}
          <input
            type="text"
            value={meshTo}
            onChange={(e) => setMeshTo(e.target.value)}
            placeholder="pho1receiver"
            style={{
              flex: 1,
              padding: "7px 12px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 13,
            }}
          />

          {/* Amount */}
          <input
            type="number"
            inputMode="decimal"
            value={meshAmount}
            onChange={(e) => setMeshAmount(e.target.value)}
            style={{
              width: 70,
              padding: "7px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 13,
              textAlign: "center",
            }}
          />

          {/* Send button */}
          <button
            type="button"
            onClick={handleMeshSend}
            disabled={meshBusy}
            style={{
              padding: "8px 16px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: "#0f172a",
              color: "#f9fafb",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
              opacity: meshBusy ? 0.6 : 1,
            }}
          >
            {meshBusy ? "Sending…" : "Send over mesh"}
          </button>
        </div>

        {meshMsg && (
          <div
            style={{
              fontSize: 11,
              color: "#15803d",
              marginTop: 2,
            }}
          >
            {meshMsg}
          </div>
        )}
        {meshErr && (
          <div
            style={{
              fontSize: 11,
              color: "#b91c1c",
              marginTop: 2,
            }}
          >
            {meshErr}
          </div>
        )}
      </section>

      {/* Mesh activity log */}
      <section
        style={{
          marginTop: 10,
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 10,
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "#0f172a",
            marginBottom: 4,
          }}
        >
          Mesh activity (local)
        </div>
        <div
          style={{
            fontSize: 11,
            color: "#9ca3af",
            marginBottom: 6,
          }}
        >
          Last few offline mesh transfers recorded on this device.
        </div>

        {meshLog.length === 0 ? (
          <div
            style={{
              fontSize: 11,
              color: "#9ca3af",
            }}
          >
            No mesh activity yet.
          </div>
        ) : (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 11,
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: "left",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5e7eb",
                    fontWeight: 500,
                    color: "#6b7280",
                  }}
                >
                  Time
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5e7eb",
                    fontWeight: 500,
                    color: "#6b7280",
                  }}
                >
                  Direction
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: "4px 0",
                    borderBottom: "1px solid #e5e7eb",
                    fontWeight: 500,
                    color: "#6b7280",
                  }}
                >
                  Counterparty
                </th>
              </tr>
            </thead>
            <tbody>
              {meshLog
                .slice(-8) // last 8 entries
                .reverse()
                .map((tx) => {
                  const isOutgoing = tx.from_account === phoAccount;
                  const direction = isOutgoing ? "Sent" : "Received";
                  const counterparty = isOutgoing
                    ? tx.to_account
                    : tx.from_account;
                  const t = tx.created_at_ms
                    ? new Date(tx.created_at_ms).toLocaleString()
                    : "—";

                  return (
                    <tr
                      key={
                        tx.mesh_tx_id ||
                        `${tx.created_at_ms}-${tx.prev_local_seq}`
                      }
                    >
                      <td style={{ padding: "3px 0", color: "#4b5563" }}>
                        {t}
                      </td>
                      <td style={{ padding: "3px 0", color: "#111827" }}>
                        {direction} <strong>{tx.amount_pho} PHO</strong>
                      </td>
                      <td style={{ padding: "3px 0", color: "#4b5563" }}>
                        {counterparty}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

type SmallBalanceProps = {
  label: string;
  value: string;
  code: string;
  hint?: string;
  tone?: "default" | "warning";
};

function SmallBalanceCard({
  label,
  value,
  code,
  hint,
  tone = "default",
}: SmallBalanceProps) {
  const bg = tone === "warning" ? "#fffbeb" : "#ffffff";
  const border = tone === "warning" ? "#fef3c7" : "#e5e7eb";

  return (
    <div
      style={{
        borderRadius: 12,
        border: `1px solid ${border}`,
        background: bg,
        padding: 10,
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: "#6b7280",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: "#111827",
        }}
      >
        {value}{" "}
        <span style={{ fontSize: 12, color: "#6b7280" }}>{code}</span>
      </div>
      {hint && (
        <div
          style={{
            marginTop: 4,
            fontSize: 10,
            color: "#9ca3af",
          }}
        >
          {hint}
        </div>
      )}
    </div>
  );
}