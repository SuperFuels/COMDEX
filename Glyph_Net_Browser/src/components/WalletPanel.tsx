// src/components/WalletPanel.tsx
import { useEffect, useState } from "react";

type Balances = {
  pho: string;                  // displayed PHO (after mesh + safety buffer)
  pho_global?: string;          // raw on-chain PHO (optional)
  tess: string;
  bonds: string;
  mesh_offline_limit_pho?: string;
  mesh_pending_pho?: string;
  pho_spendable_local?: string; // NEW: offline spendable (mesh + credit - buffer)
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

  const [balances, setBalances] = useState<Balances>({
    pho: "0.00",
    tess: "0.00",
    bonds: "0.00",
  });
  const [offlineLimit, setOfflineLimit] = useState<string>("25.0");
  const [meshPending, setMeshPending] = useState<string>("0.00");
  const [meshStateErr, setMeshStateErr] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // dev mesh send controls
  const [meshTo, setMeshTo] = useState<string>("pho1receiver");
  const [meshAmount, setMeshAmount] = useState<string>("1");
  const [meshBusy, setMeshBusy] = useState<boolean>(false);
  const [meshMsg, setMeshMsg] = useState<string | null>(null);
  const [meshErr, setMeshErr] = useState<string | null>(null);

    // mesh debug inspector (dev)
  const [debugAccount, setDebugAccount] = useState<string>("pho1receiver");
  const [debugView, setDebugView] = useState<any | null>(null);
  const [debugBusy, setDebugBusy] = useState(false);
  const [debugErr, setDebugErr] = useState<string | null>(null);

  const [meshLog, setMeshLog] = useState<MeshTxEntry[]>([]);

  // NEW: mesh state health
  const [meshStateStatus, setMeshStateStatus] = useState<"idle" | "ok" | "error">("idle");
  const [meshStateError, setMeshStateError] = useState<string | null>(null);

  // small helper so we can re-use after mesh sends
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
        pho: b.pho ?? "0.00",
        pho_global: b.pho_global ?? b.pho ?? "0.00",
        tess: b.tess ?? "0.00",
        bonds: b.bonds ?? "0.00",
        mesh_offline_limit_pho: b.mesh_offline_limit_pho ?? "25.0",
        mesh_pending_pho: b.mesh_pending_pho ?? "0.00",
        pho_spendable_local: b.pho_spendable_local ?? b.pho ?? "0.00",
      });
      setOfflineLimit(b.mesh_offline_limit_pho ?? "25.0");
      setMeshPending(b.mesh_pending_pho ?? "0.00");

      // --- mesh local_state for activity log + precise pending ---
      setMeshStateStatus("idle");
      setMeshStateError(null);

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

          setMeshStateStatus("ok");
        } else {
          setMeshStateStatus("error");
          setMeshStateError(
            `Mesh state unavailable (HTTP ${resp2.status})`
          );
          setMeshLog([]);
        }
      } catch (e) {
        console.warn("[WalletPanel] mesh local_state fetch failed:", e);
        setMeshStateStatus("error");
        setMeshStateError("Mesh state unavailable (radio/runtime offline?)");
        setMeshLog([]);
      }
    } catch (e) {
      console.warn("[WalletPanel] using local demo balances:", e);
      setPhoAccount("pho1-demo-offline");
      setBalances({
        pho: "123.45",
        pho_global: "123.45",
        tess: "42.00",
        bonds: "3.00",
        mesh_offline_limit_pho: "25.0",
        mesh_pending_pho: "0.00",
        pho_spendable_local: "123.45",
      });
      setOfflineLimit("25.0");
      setMeshPending("0.00");
      setMeshLog([]);
      setMeshStateStatus("error");
      setMeshStateError("Mesh state unavailable (wallet fetch failed)");
    } finally {
      setLoading(false);
    }
  }

  // initial bootstrap
  useEffect(() => {
    if (typeof window === "undefined") return;

    const wa =
      localStorage.getItem("gnet:ownerWa") ??
      localStorage.getItem("gnet:wa") ??
      null;

    setOwnerWa(wa);
    void refreshWalletBalances(wa);
  }, []);

  async function handleMeshDebugLookup() {
    const acct = (debugAccount || "").trim();
    if (!acct) return;

    setDebugBusy(true);
    setDebugErr(null);

    try {
      const resp = await fetch(
        `/api/mesh/local_state/${encodeURIComponent(acct)}`
      );
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setDebugView(data);
    } catch (e: any) {
      console.error("[WalletPanel] mesh debug lookup failed:", e);
      setDebugErr(e?.message || "Failed to fetch mesh state.");
      setDebugView(null);
    } finally {
      setDebugBusy(false);
    }
  }

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

      await resp.json(); // we don't actually need the body right now

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

  const meshDisabled =
    meshBusy || !phoAccount || meshStateStatus === "error";

  const offlineSpendable =
    balances.pho_spendable_local ?? balances.pho ?? "0.00";

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
          {offlineSpendable && (
            <div
              style={{
                marginTop: 2,
                fontSize: 10,
                color: "#6b7280",
              }}
            >
              Offline spendable now:{" "}
              <strong>{offlineSpendable} PHO</strong>{" "}
              <span style={{ color: "#9ca3af" }}>
                (mesh credit + local balance − safety buffer)
              </span>
            </div>
          )}
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
      {/* Recurring payments (dev) */}
      <RecurringPaymentsCard />

      {/* Swap strip – visual only */}
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
            disabled={meshDisabled}
            style={{
              padding: "8px 16px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: "#0f172a",
              color: "#f9fafb",
              fontSize: 13,
              fontWeight: 600,
              cursor: meshDisabled ? "default" : "pointer",
              whiteSpace: "nowrap",
              opacity: meshDisabled ? 0.6 : 1,
            }}
          >
            {meshBusy ? "Sending…" : "Send over mesh"}
          </button>
        </div>

        {!phoAccount && (
          <div
            style={{
              fontSize: 11,
              color: "#9ca3af",
              marginTop: 2,
            }}
          >
            Mesh send disabled until PHO account is ready.
          </div>
        )}

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

      {/* PhotonPay receipts (dev) */}
      {phoAccount && <WalletReceiptsCard account={phoAccount} />}

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

        {meshStateError ? (
          <div
            style={{
              fontSize: 11,
              color: "#b91c1c",
            }}
          >
            {meshStateError}
          </div>
        ) : meshLog.length === 0 ? (
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
                .slice(-8)
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

      {/* Mesh local_state inspector (dev) */}
      <section
        style={{
          marginTop: 10,
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
          <span>Mesh local_state inspector (dev)</span>
          <span style={{ fontSize: 11, color: "#9ca3af" }}>
            Reads <code>/api/mesh/local_state/&lt;account&gt;</code>
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
          <input
            type="text"
            value={debugAccount}
            onChange={(e) => setDebugAccount(e.target.value)}
            placeholder="pho1receiver"
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
            onClick={handleMeshDebugLookup}
            disabled={debugBusy || !debugAccount.trim()}
            style={{
              padding: "8px 16px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: "#0f172a",
              color: "#f9fafb",
              fontSize: 13,
              fontWeight: 600,
              cursor:
                debugBusy || !debugAccount.trim() ? "default" : "pointer",
              whiteSpace: "nowrap",
              opacity: debugBusy || !debugAccount.trim() ? 0.6 : 1,
            }}
          >
            {debugBusy ? "Fetching…" : "Fetch state"}
          </button>
        </div>

        {debugErr && (
          <div
            style={{
              fontSize: 11,
              color: "#b91c1c",
              marginTop: 2,
            }}
          >
            {debugErr}
          </div>
        )}

        {debugView && !debugErr && (
          <div
            style={{
              marginTop: 4,
              padding: 8,
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              color: "#374151",
            }}
          >
            <div style={{ marginBottom: 4 }}>
              <strong>Account:</strong> {debugView.account}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
              <div>
                <div style={{ color: "#6b7280" }}>Global PHO</div>
                <div>{debugView.local_balance?.global_confirmed_pho}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Local Δ (net)</div>
                <div>{debugView.local_balance?.local_net_delta_pho}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Offline limit</div>
                <div>{debugView.local_balance?.offline_credit_limit_pho}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Mesh pending</div>
                <div>{debugView.mesh_pending_pho}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Log entries</div>
                <div>{debugView.tx_log?.entries?.length ?? 0}</div>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

// ───────────────────────────────────────────────
// Dev-only: Recurring payments card
// ───────────────────────────────────────────────

// ───────────────────────────────────────────────
// Dev-only: Photon Pay recurring payments
// ───────────────────────────────────────────────

type DevMandate = {
  instr_id: string;
  from_account: string;
  to_account: string;
  amount_pho: string;
  memo?: string | null;
  frequency: string;
  next_due_ms: number;
  created_at_ms: number;
  last_run_at_ms: number | null;
  total_runs: number;
  max_runs: number | null;
  active: boolean;
};

function RecurringPaymentsCard() {
  const [items, setItems] = useState<DevMandate[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // dev-only payer account for now
  const payerAccount = "pho1-demo-offline";

  const load = () => {
    setLoading(true);
    fetch(
      `/api/photon_pay/dev/recurring?from_account=${encodeURIComponent(
        payerAccount,
      )}`,
    )
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((j) => {
        const list = (j?.recurring || []) as DevMandate[];
        setItems(list);
        setErr(null);
      })
      .catch(async (e) => {
        const txt = typeof e?.text === "function" ? await e.text() : "";
        setItems([]);
        setErr(txt || "Failed to load recurring mandates");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  return (
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
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "#0f172a",
          }}
        >
          Recurring payments (dev)
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            fontSize: 11,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {err && <div style={{ fontSize: 12, color: "#b91c1c" }}>{err}</div>}

      {items.length === 0 && !err ? (
        <div style={{ fontSize: 12, color: "#9ca3af" }}>
          No recurring payments yet for <code>{payerAccount}</code>.
        </div>
      ) : null}

      {items.length > 0 && (
        <ul
          style={{
            listStyle: "none",
            padding: 0,
            margin: 0,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {items.map((m) => {
            const nextRun =
              m.next_due_ms && m.next_due_ms > 0
                ? new Date(m.next_due_ms).toLocaleDateString()
                : "-";

            return (
              <li
                key={m.instr_id}
                style={{
                  padding: 8,
                  borderRadius: 10,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  fontSize: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <div>
                  <div>
                    <strong>{m.amount_pho} PHO</strong>{" "}
                    <span style={{ color: "#6b7280" }}>
                      → {m.to_account}
                    </span>
                  </div>
                  {m.memo && (
                    <div style={{ color: "#6b7280", fontSize: 11 }}>
                      {m.memo}
                    </div>
                  )}
                  <div style={{ color: "#9ca3af", fontSize: 11 }}>
                    {m.frequency} • next {nextRun}
                  </div>
                </div>
                <div
                  style={{
                    alignSelf: "center",
                    fontSize: 11,
                    color: m.active ? "#16a34a" : "#9ca3af",
                  }}
                >
                  {m.active ? "Active" : "Inactive"}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

// ───────────────────────────────────────────────
// Dev-only: Recent Photon Pay receipts for wallet
// ───────────────────────────────────────────────

// ───────────────────────────────────────────────
// Dev-only: Recent Photon Pay receipts for wallet
// ───────────────────────────────────────────────

type DevReceipt = {
  receipt_id: string;
  from_account: string;
  to_account: string;
  amount_pho: string;
  memo?: string | null;
  channel: string;
  invoice_id?: string | null;
  created_at_ms: number;
};

function WalletReceiptsCard({ account }: { account: string }) {
  const [items, setItems] = useState<DevReceipt[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [refundBusyId, setRefundBusyId] = useState<string | null>(null);

  const load = () => {
    if (!account) return;
    setLoading(true);
    setErr(null);

    fetch(`/api/wallet/dev/receipts?account=${encodeURIComponent(account)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((j) => {
        const list = (j?.receipts || []) as DevReceipt[];
        list.sort(
          (a, b) => (b.created_at_ms || 0) - (a.created_at_ms || 0)
        );
        setItems(list.slice(0, 10)); // last 10
      })
      .catch(async (e) => {
        const txt = typeof e?.text === "function" ? await e.text() : "";
        setErr(txt || "Failed to load receipts");
        setItems([]);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [account]);

  const handleRefund = async (r: DevReceipt) => {
    setRefundBusyId(r.receipt_id);
    setErr(null);

    try {
      // Synthetic refund invoice
      const refundInvoice = {
        invoice_id: r.invoice_id || `refund_${r.receipt_id}`,
        seller_account: r.from_account, // original payer
        seller_wave_addr: null,
        amount_pho: r.amount_pho,
        fiat_symbol: null,
        fiat_amount: null,
        memo: r.memo ? `Refund: ${r.memo}` : "Refund",
        created_at_ms: Date.now(),
        expiry_ms: Date.now() + 5 * 60 * 1000,
      };

      const resp = await fetch("/api/photon_pay/dev/receipts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          from_account: r.to_account, // merchant sending refund
          channel: r.channel || "mesh",
          invoice: refundInvoice,
        }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      await resp.json();
      load(); // reload receipts
    } catch (e: any) {
      console.error("[WalletReceiptsCard] refund failed:", e);
      setErr(e?.message || "Refund failed");
    } finally {
      setRefundBusyId(null);
    }
  };

  // Running net PHO for this wallet (oldest → newest)
  const netById: Record<string, number> = {};
  {
    let running = 0;
    const ordered = [...items].sort(
      (a, b) => (a.created_at_ms || 0) - (b.created_at_ms || 0),
    );
    for (const r of ordered) {
      const amt = Number(r.amount_pho || "0") || 0;
      const isOutgoing = r.from_account === account;
      running += isOutgoing ? -amt : amt;
      netById[r.receipt_id] = running;
    }
  }

  return (
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
          alignItems: "baseline",
        }}
      >
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "#0f172a",
          }}
        >
          Recent PhotonPay receipts (dev)
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          style={{
            padding: "4px 10px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            fontSize: 11,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {err && (
        <div
          style={{
            fontSize: 11,
            color: "#b91c1c",
          }}
        >
          {err}
        </div>
      )}

      {!err && items.length === 0 && (
        <div
          style={{
            fontSize: 11,
            color: "#9ca3af",
          }}
        >
          No PhotonPay receipts yet for <code>{account}</code>.
        </div>
      )}

      {items.length > 0 && (
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 11,
            marginTop: 4,
          }}
        >
          <thead>
            <tr
              style={{
                borderBottom: "1px solid #e5e7eb",
                color: "#6b7280",
                textAlign: "left",
              }}
            >
              <th style={{ padding: "4px 0" }}>Time</th>
              <th style={{ padding: "4px 0" }}>Direction</th>
              <th style={{ padding: "4px 0" }}>Type</th>
              <th style={{ padding: "4px 0" }}>Counterparty</th>
              <th style={{ padding: "4px 0" }}>Amount</th>
              <th style={{ padding: "4px 0" }}>Net (PHO)</th>
              <th style={{ padding: "4px 0" }}>Memo</th>
              <th style={{ padding: "4px 0" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => {
              const isOutgoing = r.from_account === account;
              const direction = isOutgoing ? "Paid" : "Received";
              const counterparty = isOutgoing ? r.to_account : r.from_account;
              const t = r.created_at_ms
                ? new Date(r.created_at_ms).toLocaleString()
                : "—";

              const receiptType =
                (r.memo && r.memo.startsWith("Refund:")) ||
                (r.invoice_id && r.invoice_id.startsWith("refund_"))
                  ? "Refund"
                  : "Payment";

              const typeBg = receiptType === "Refund" ? "#fef2f2" : "#ecfdf5";
              const typeBorder =
                receiptType === "Refund" ? "#fecaca" : "#bbf7d0";
              const typeColor =
                receiptType === "Refund" ? "#b91c1c" : "#15803d";

              const net = netById[r.receipt_id] ?? 0;

              return (
                <tr key={r.receipt_id}>
                  <td style={{ padding: "3px 0", color: "#4b5563" }}>{t}</td>
                  <td style={{ padding: "3px 0", color: "#111827" }}>
                    {direction}
                  </td>
                  <td style={{ padding: "3px 0" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 6px",
                        borderRadius: 999,
                        border: `1px solid ${typeBorder}`,
                        background: typeBg,
                        fontSize: 10,
                        color: typeColor,
                      }}
                    >
                      {receiptType}
                    </span>
                  </td>
                  <td style={{ padding: "3px 0", color: "#4b5563" }}>
                    {counterparty}
                  </td>
                  <td style={{ padding: "3px 0", color: "#111827" }}>
                    {r.amount_pho} PHO
                  </td>
                  <td style={{ padding: "3px 0", color: "#111827" }}>
                    {net.toFixed(2)} PHO
                  </td>
                  <td style={{ padding: "3px 0", color: "#6b7280" }}>
                    {r.memo || "—"}
                  </td>
                  <td style={{ padding: "3px 0" }}>
                    {isOutgoing ? (
                      <button
                        type="button"
                        onClick={() => handleRefund(r)}
                        disabled={refundBusyId === r.receipt_id}
                        style={{
                          padding: "4px 10px",
                          borderRadius: 999,
                          border: "1px solid #dc2626",
                          background: "#fee2e2",
                          fontSize: 11,
                          color: "#b91c1c",
                          cursor:
                            refundBusyId === r.receipt_id
                              ? "default"
                              : "pointer",
                          opacity:
                            refundBusyId === r.receipt_id ? 0.6 : 1,
                        }}
                      >
                        {refundBusyId === r.receipt_id
                          ? "Refunding…"
                          : "Refund"}
                      </button>
                    ) : (
                      <span
                        style={{ fontSize: 11, color: "#9ca3af" }}
                      >
                        —
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}

// ───────────────────────────────────────────────
// Small balance cards (TESS / Bonds / Pending)
// ───────────────────────────────────────────────

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

