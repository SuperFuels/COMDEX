import React, { useEffect, useState } from "react";

type Block = any;
type Tx = any;

async function postJson(url: string, body: any) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || `HTTP ${res.status} ${res.statusText}`);
  }
  return res.json().catch(() => ({}));
}

export default function ChainSimLedgerPanel() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [txs, setTxs] = useState<Tx[]>([]);
  const [address, setAddress] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    try {
      setBusy(true);
      setErr(null);

      const blocksUrl = `/api/chain_sim/dev/blocks?limit=20&offset=0`;
      const txsQs = new URLSearchParams();
      txsQs.set("limit", "20");
      txsQs.set("offset", "0");
      if (address.trim()) txsQs.set("address", address.trim());
      const txsUrl = `/api/chain_sim/dev/txs?${txsQs.toString()}`;

      const [bRes, tRes] = await Promise.all([fetch(blocksUrl), fetch(txsUrl)]);

      if (!bRes.ok) throw new Error(await bRes.text());
      if (!tRes.ok) throw new Error(await tRes.text());

      const bJson = await bRes.json();
      const tJson = await tRes.json();

      setBlocks(bJson.blocks || bJson?.data?.blocks || []);
      setTxs(tJson.txs || tJson?.data?.txs || []);
    } catch (e: any) {
      setErr(e?.message || "Failed to load chain sim ledger");
      setBlocks([]);
      setTxs([]);
    } finally {
      setBusy(false);
    }
  }

  async function seedDemoTxs() {
    try {
      setSeeding(true);
      setErr(null);

      // short deterministic-ish suffix so repeated clicks create new accounts
      const tag = Date.now().toString(16).slice(-6);
      const alice = `pho1-devtools-alice-${tag}`;
      const bob = `pho1-devtools-bob-${tag}`;

      // 1) mint 1000 PHO to alice (dev mint authority is enforced server-side)
      await postJson("/api/chain_sim/dev/mint", {
        denom: "PHO",
        to: alice,
        amount: "1000",
      });

      // 2) transfer 100 PHO from alice to bob
      await postJson("/api/chain_sim/dev/transfer", {
        denom: "PHO",
        from_addr: alice,
        to: bob,
        amount: "100",
      });

      // 3) burn 50 PHO from alice
      await postJson("/api/chain_sim/dev/burn", {
        denom: "PHO",
        from_addr: alice,
        amount: "50",
      });

      // convenience: auto-filter to alice so you see what just happened
      setAddress(alice);

      // refresh list views
      await refresh();
    } catch (e: any) {
      setErr(e?.message || "Failed to seed demo txs");
    } finally {
      setSeeding(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section
      style={{
        borderRadius: 16,
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#0f172a" }}>
          Chain Sim Ledger (dev)
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            type="button"
            onClick={seedDemoTxs}
            disabled={busy || seeding}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: seeding ? "#e5e7eb" : "#0f172a",
              color: seeding ? "#6b7280" : "#f9fafb",
              fontSize: 11,
              cursor: busy || seeding ? "default" : "pointer",
              opacity: busy || seeding ? 0.8 : 1,
            }}
          >
            {seeding ? "Seeding…" : "Seed demo txs"}
          </button>

          <button
            type="button"
            onClick={refresh}
            disabled={busy || seeding}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: busy || seeding ? "default" : "pointer",
              opacity: busy || seeding ? 0.7 : 1,
            }}
          >
            {busy ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Filter txs by address (optional)"
          style={{
            flex: 1,
            minWidth: 220,
            padding: "6px 10px",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            fontSize: 11,
          }}
        />
        <button
          type="button"
          onClick={refresh}
          disabled={busy || seeding}
          style={{
            padding: "6px 12px",
            borderRadius: 999,
            border: "1px solid #0f172a",
            background: "#0f172a",
            color: "#f9fafb",
            fontSize: 11,
            fontWeight: 600,
            cursor: busy || seeding ? "default" : "pointer",
            whiteSpace: "nowrap",
            opacity: busy || seeding ? 0.7 : 1,
          }}
        >
          Apply
        </button>
      </div>

      {err && <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {/* Blocks */}
        <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, background: "#fff", padding: 8, overflow: "auto" }}>
          <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>Blocks</div>
          {blocks.length === 0 ? (
            <div style={{ fontSize: 11, color: "#9ca3af" }}>No blocks yet.</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "2px 4px" }}>Height</th>
                  <th style={{ padding: "2px 4px" }}>Txs</th>
                  <th style={{ padding: "2px 4px" }}>Time</th>
                </tr>
              </thead>
              <tbody>
                {blocks.map((b: any, idx: number) => (
                  <tr key={b.height ?? idx}>
                    <td style={{ padding: "2px 4px" }}><code>{b.height ?? "—"}</code></td>
                    <td style={{ padding: "2px 4px" }}>{Array.isArray(b.txs) ? b.txs.length : (b.num_txs ?? "—")}</td>
                    <td style={{ padding: "2px 4px" }}>
                      {b.created_at_ms ? new Date(b.created_at_ms).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Txs */}
        <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, background: "#fff", padding: 8, overflow: "auto" }}>
          <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>Txs</div>
          {txs.length === 0 ? (
            <div style={{ fontSize: 11, color: "#9ca3af" }}>No txs yet.</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "2px 4px" }}>Tx</th>
                  <th style={{ padding: "2px 4px" }}>Type</th>
                  <th style={{ padding: "2px 4px" }}>From</th>
                  <th style={{ padding: "2px 4px" }}>Nonce</th>
                  <th style={{ padding: "2px 4px" }}>Block</th>
                </tr>
              </thead>
              <tbody>
                {txs.map((t: any, idx: number) => (
                  <tr key={t.tx_id ?? idx}>
                    <td style={{ padding: "2px 4px" }}><code>{String(t.tx_id ?? "").slice(0, 8)}…</code></td>
                    <td style={{ padding: "2px 4px" }}><code>{t.tx_type ?? "—"}</code></td>
                    <td style={{ padding: "2px 4px" }}><code>{String(t.from_addr ?? "").slice(0, 12)}…</code></td>
                    <td style={{ padding: "2px 4px" }}><code>{t.nonce ?? "—"}</code></td>
                    <td style={{ padding: "2px 4px" }}><code>{t.block_height ?? "—"}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}