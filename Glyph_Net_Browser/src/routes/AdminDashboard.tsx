// src/routes/AdminDashboard.tsx
// Dev-only admin dashboard:
//   • GMA reserves + equity snapshot (+ reserve ops)
//   • Photon Pay recurring mandates list + cancel controls.

import { useEffect, useState } from "react";

type ReserveRow = {
  asset_id: string;
  quantity: string;
  price_pho: string;
  value_pho: string;
};

type MintBurnEvent = {
  kind: "MINT" | "BURN";
  amount_pho: string;
  reason?: string | null;
  created_at_ms: number;
};

type GmaSnapshot = {
  photon_supply_pho: string;
  tesseract_supply: string;
  total_reserves_pho: string;
  offline_credit_exposure_pho: string;
  offline_credit_soft_cap_ratio: string;
  max_offline_credit_soft_cap: string;
  equity_pho: string;
  reserves: Record<string, ReserveRow>;
  mint_burn_log?: MintBurnEvent[];
};

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

type BondSeries = {
  series_id: string;
  label: string;
  coupon_bps: number;
  maturity_ms: number;
  created_at_ms: number;
  total_issued_pho: string;
  total_outstanding_pho: string;
};

type BondPosition = {
  position_id: string;
  series_id: string;
  account: string;
  principal_pho: string;
  created_at_ms: number;
};

export default function AdminDashboard() {
  // ── GMA state
  const [snapshot, setSnapshot] = useState<GmaSnapshot | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [opAssetId, setOpAssetId] = useState<string>("USD_BANK_X");
  const [opAmount, setOpAmount] = useState<string>("1000");
  const [opBusy, setOpBusy] = useState<boolean>(false);
  const [opMsg, setOpMsg] = useState<string | null>(null);

  // ── Recurring mandates
  const [mandates, setMandates] = useState<DevMandate[]>([]);
  const [mandatesErr, setMandatesErr] = useState<string | null>(null);
  const [busyCancel, setBusyCancel] = useState<string | null>(null);

  // ── PhotonPay receipts (dev)
  const [receipts, setReceipts] = useState<DevReceipt[]>([]);
  const [receiptsErr, setReceiptsErr] = useState<string | null>(null);
  const [receiptsLoading, setReceiptsLoading] = useState<boolean>(false);

  // ── PhotonPay POS invoice (dev)
  const [posAmount, setPosAmount] = useState<string>("5.0");
  const [posMemo, setPosMemo] = useState<string>("Coffee");
  const [posSeller, setPosSeller] = useState<string>("pho1-demo-merchant");
  const [posBusy, setPosBusy] = useState<boolean>(false);
  const [posErr, setPosErr] = useState<string | null>(null);
  const [posInvoice, setPosInvoice] = useState<any | null>(null);

  // ── Glyph Bonds (dev)
  const [bondSeries, setBondSeries] = useState<BondSeries[]>([]);
  const [bondPositions, setBondPositions] = useState<BondPosition[]>([]);
  const [bondsErr, setBondsErr] = useState<string | null>(null);
  const [bondsLoading, setBondsLoading] = useState<boolean>(false);

  const [newSeriesLabel, setNewSeriesLabel] = useState<string>("Demo bond series");
  const [newSeriesCouponBps, setNewSeriesCouponBps] = useState<string>("500"); // 5.00%
  const [newSeriesTermDays, setNewSeriesTermDays] = useState<string>("365");

  const [issueSeriesId, setIssueSeriesId] = useState<string>("");
  const [issueAmountPho, setIssueAmountPho] = useState<string>("100.0");
  const [issueBusy, setIssueBusy] = useState<boolean>(false);

  const BOND_DEV_ACCOUNT = "pho1-demo-offline";

  async function handleMakePosInvoice() {
    if (!posSeller.trim() || !posAmount.trim()) {
      setPosErr("Enter seller + amount.");
      return;
    }

    setPosErr(null);
    setPosInvoice(null);
    setPosBusy(true);

    try {
      const resp = await fetch("/api/photon_pay/dev/make_invoice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          seller_account: posSeller.trim(),
          amount_pho: posAmount.trim(),
          memo: posMemo.trim() || null,
        }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setPosInvoice(data);
    } catch (e: any) {
      console.error("[AdminDashboard] make POS invoice failed:", e);
      setPosErr(e?.message || "Failed to generate invoice");
    } finally {
      setPosBusy(false);
    }
  }

  // ────────────────────────────────────────────
  // GMA snapshot
  // ────────────────────────────────────────────

  async function fetchSnapshot() {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/gma/state/dev_snapshot");
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }
      const data: GmaSnapshot = await resp.json();
      setSnapshot(data);

      // Default assetId to first reserve if present
      const keys = Object.keys(data.reserves || {});
      if (keys.length > 0 && !keys.includes(opAssetId)) {
        setOpAssetId(keys[0]);
      }
    } catch (e: any) {
      console.error("[AdminDashboard] fetch snapshot failed:", e);
      setError(e?.message || "Failed to load GMA snapshot");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSnapshot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runReserveOp(kind: "deposit" | "redemption") {
    if (!opAmount || Number(opAmount) <= 0) {
      setOpMsg("Enter a positive amount.");
      return;
    }
    if (!opAssetId) {
      setOpMsg("Select a reserve asset.");
      return;
    }

    setOpBusy(true);
    setOpMsg(null);

    const path =
      kind === "deposit"
        ? "/api/gma/state/dev_reserve_deposit"
        : "/api/gma/state/dev_reserve_redemption";

    try {
      const resp = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_id: opAssetId,
          amount_pho: opAmount,
        }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const data: GmaSnapshot = await resp.json();
      setSnapshot(data);

      setOpMsg(
        kind === "deposit"
          ? `Deposited ${opAmount} PHO worth into ${opAssetId} reserves.`
          : `Redeemed ${opAmount} PHO from ${opAssetId} reserves.`,
      );
    } catch (e: any) {
      console.error("[AdminDashboard] reserve op failed:", e);
      setOpMsg(e?.message || "Reserve operation failed");
    } finally {
      setOpBusy(false);
    }
  }

  const reservesArray: ReserveRow[] = snapshot
    ? Object.values(snapshot.reserves || {})
    : [];

  // ────────────────────────────────────────────
  // Recurring mandates
  // ────────────────────────────────────────────

  const refreshMandates = () => {
    fetch("/api/photon_pay/dev/recurring")
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((j) => {
        const list = (j?.recurring || []) as DevMandate[];
        setMandates(list);
        setMandatesErr(null);
      })
      .catch(async (e) => {
        const txt = typeof e?.text === "function" ? await e.text() : "";
        setMandates([]);
        setMandatesErr(txt || "Failed to load mandates");
      });
  };

  const refreshReceipts = () => {
    setReceiptsLoading(true);
    fetch("/api/photon_pay/dev/receipts")
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((j) => {
        const list = (j?.receipts || []) as DevReceipt[];
        list.sort(
          (a, b) => (b.created_at_ms || 0) - (a.created_at_ms || 0)
        );
        setReceipts(list.slice(0, 20));
        setReceiptsErr(null);
      })
      .catch(async (e) => {
        const txt = typeof e?.text === "function" ? await e.text() : "";
        setReceipts([]);
        setReceiptsErr(txt || "Failed to load receipts");
      })
      .finally(() => setReceiptsLoading(false));
  };

  const refreshBonds = () => {
    setBondsLoading(true);
    setBondsErr(null);

    Promise.all([
      fetch("/api/glyph_bonds/dev/series"),
      fetch(`/api/glyph_bonds/dev/positions?account=${encodeURIComponent(BOND_DEV_ACCOUNT)}`),
    ])
      .then(async ([seriesResp, posResp]) => {
        if (!seriesResp.ok) {
          throw new Error(await seriesResp.text());
        }
        if (!posResp.ok) {
          throw new Error(await posResp.text());
        }
        const seriesJson = await seriesResp.json();
        const posJson = await posResp.json();

        const seriesList = (seriesJson?.series || []) as BondSeries[];
        const posList = (posJson?.positions || []) as BondPosition[];

        // sort series by created time (newest first)
        seriesList.sort((a, b) => (b.created_at_ms || 0) - (a.created_at_ms || 0));
        // sort positions by created time (newest first)
        posList.sort((a, b) => (b.created_at_ms || 0) - (a.created_at_ms || 0));

        setBondSeries(seriesList);
        setBondPositions(posList);

        // default issueSeriesId to first series if not set
        if (!issueSeriesId && seriesList.length > 0) {
          setIssueSeriesId(seriesList[0].series_id);
        }
      })
      .catch((e: any) => {
        console.error("[AdminDashboard] refresh bonds failed:", e);
        setBondsErr(e?.message || "Failed to load bond series/positions");
        setBondSeries([]);
        setBondPositions([]);
      })
      .finally(() => setBondsLoading(false));
  };

  async function handleCreateSeries() {
    if (!newSeriesLabel.trim()) {
      setBondsErr("Enter a series label.");
      return;
    }
    if (!newSeriesCouponBps.trim()) {
      setBondsErr("Enter coupon (bps).");
      return;
    }
    if (!newSeriesTermDays.trim()) {
      setBondsErr("Enter term in days.");
      return;
    }

    setBondsErr(null);
    try {
      const resp = await fetch("/api/glyph_bonds/dev/series", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label: newSeriesLabel.trim(),
          coupon_bps: Number(newSeriesCouponBps),
          term_days: Number(newSeriesTermDays),
        }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      await resp.json();
      refreshBonds();
    } catch (e: any) {
      console.error("[AdminDashboard] create bond series failed:", e);
      setBondsErr(e?.message || "Failed to create bond series");
    }
  }

  async function handleIssueToDev() {
    if (!issueSeriesId) {
      setBondsErr("Select a series to issue.");
      return;
    }
    if (!issueAmountPho || Number(issueAmountPho) <= 0) {
      setBondsErr("Enter a positive principal amount.");
      return;
    }

    setIssueBusy(true);
    setBondsErr(null);

    try {
      const resp = await fetch("/api/glyph_bonds/dev/issue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          series_id: issueSeriesId,
          account: BOND_DEV_ACCOUNT,
          principal_pho: issueAmountPho,
        }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      await resp.json();
      refreshBonds();
    } catch (e: any) {
      console.error("[AdminDashboard] issue bond failed:", e);
      setBondsErr(e?.message || "Failed to issue bonds to dev account");
    } finally {
      setIssueBusy(false);
    }
  }

  useEffect(() => {
    refreshMandates();
    refreshReceipts();
    refreshBonds();
  }, []);

  const handleCancel = async (m: DevMandate) => {
    setBusyCancel(m.instr_id);
    try {
      const resp = await fetch(
        `/api/photon_pay/dev/recurring/${m.instr_id}/cancel`,
        { method: "POST" },
      );
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }
      await resp.json();
      refreshMandates();
    } catch (e: any) {
      console.error("[AdminDashboard] cancel recurring failed:", e);
      setMandatesErr(e?.message || "Failed to cancel recurring instruction");
    } finally {
      setBusyCancel(null);
    }
  };

  return (
    <div
      style={{
        maxWidth: 1100,
        margin: "0 auto",
        paddingTop: 24,
        paddingBottom: 48,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      {/* ── Header ───────────────────────────── */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 4,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: 22,
              fontWeight: 600,
              color: "#0f172a",
            }}
          >
            Admin dashboard (dev)
          </h1>
          <p
            style={{
              margin: 0,
              marginTop: 4,
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            GMA balance sheet snapshot + Photon Pay controls + room for more
            system health cards.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchSnapshot}
          disabled={loading}
          style={{
            padding: "6px 14px",
            borderRadius: 999,
            border: "1px solid #0f172a",
            background: "#0f172a",
            color: "#f9fafb",
            fontSize: 12,
            fontWeight: 600,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Refreshing…" : "Refresh GMA"}
        </button>
      </header>

      {error && (
        <div
          style={{
            marginBottom: 4,
            padding: 8,
            borderRadius: 8,
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#b91c1c",
            fontSize: 12,
          }}
        >
          {error}
        </div>
      )}

      {/* ── GMA card ─────────────────────────── */}
      <section
        style={{
          borderRadius: 18,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 20,
        }}
      >
        <h2
          style={{
            margin: 0,
            fontSize: 14,
            fontWeight: 600,
            color: "#111827",
          }}
        >
          GMA – Reserves &amp; Equity
        </h2>
        <p
          style={{
            margin: 0,
            marginTop: 4,
            fontSize: 11,
            color: "#6b7280",
          }}
        >
          Dev view of the GMAState model (PHO terms).
        </p>

        {snapshot ? (
          <>
            {/* Top metrics row */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 24,
                marginTop: 16,
                fontSize: 11,
                color: "#374151",
              }}
            >
              <div>
                <div style={{ color: "#6b7280" }}>PHO supply</div>
                <div>{snapshot.photon_supply_pho} PHO</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Total reserves</div>
                <div>{snapshot.total_reserves_pho} PHO</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Equity</div>
                <div>{snapshot.equity_pho} PHO</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Offline credit exposure</div>
                <div>{snapshot.offline_credit_exposure_pho} PHO</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Offline soft cap</div>
                <div>
                  {snapshot.max_offline_credit_soft_cap} PHO (
                  {snapshot.offline_credit_soft_cap_ratio})
                </div>
              </div>
            </div>

            {/* Reserve positions table */}
            <div style={{ marginTop: 20 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#111827",
                  marginBottom: 6,
                }}
              >
                Reserve positions
              </div>
              {reservesArray.length === 0 ? (
                <div
                  style={{
                    fontSize: 11,
                    color: "#9ca3af",
                  }}
                >
                  No reserves configured.
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
                    <tr
                      style={{
                        borderBottom: "1px solid #e5e7eb",
                        color: "#6b7280",
                        textAlign: "left",
                      }}
                    >
                      <th style={{ padding: "4px 0" }}>Asset</th>
                      <th style={{ padding: "4px 0" }}>Quantity</th>
                      <th style={{ padding: "4px 0" }}>Price (PHO)</th>
                      <th style={{ padding: "4px 0" }}>Value (PHO)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reservesArray.map((r) => (
                      <tr
                        key={r.asset_id}
                        style={{ borderTop: "1px solid #f3f4f6" }}
                      >
                        <td style={{ padding: "4px 0" }}>{r.asset_id}</td>
                        <td style={{ padding: "4px 0" }}>{r.quantity}</td>
                        <td style={{ padding: "4px 0" }}>{r.price_pho}</td>
                        <td style={{ padding: "4px 0" }}>{r.value_pho}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Reserve operations (dev-only) */}
            <div
              style={{
                marginTop: 20,
                paddingTop: 12,
                borderTop: "1px dashed #e5e7eb",
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#111827",
                  marginBottom: 6,
                }}
              >
                Reserve ops (dev)
              </div>
              <p
                style={{
                  margin: 0,
                  marginBottom: 8,
                  fontSize: 11,
                  color: "#6b7280",
                }}
              >
                Simulate custodian deposits / redemptions against the GMA dev
                model. This mutates the in-memory state used by this browser
                session only.
              </p>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                  alignItems: "center",
                  marginBottom: 4,
                }}
              >
                <select
                  value={opAssetId}
                  onChange={(e) => setOpAssetId(e.target.value)}
                  style={{
                    padding: "4px 8px",
                    borderRadius: 999,
                    border: "1px solid #e5e7eb",
                    fontSize: 11,
                  }}
                >
                  {reservesArray.map((r) => (
                    <option key={r.asset_id} value={r.asset_id}>
                      {r.asset_id}
                    </option>
                  ))}
                </select>

                <input
                  type="number"
                  inputMode="decimal"
                  value={opAmount}
                  onChange={(e) => setOpAmount(e.target.value)}
                  style={{
                    width: 120,
                    padding: "4px 8px",
                    borderRadius: 999,
                    border: "1px solid #e5e7eb",
                    fontSize: 11,
                    textAlign: "right",
                  }}
                  placeholder="Amount PHO"
                />

                <button
                  type="button"
                  disabled={opBusy}
                  onClick={() => runReserveOp("deposit")}
                  style={{
                    padding: "5px 10px",
                    borderRadius: 999,
                    border: "1px solid #047857",
                    background: "#047857",
                    color: "#ecfdf5",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: opBusy ? "default" : "pointer",
                    opacity: opBusy ? 0.7 : 1,
                  }}
                >
                  Deposit to reserves
                </button>

                <button
                  type="button"
                  disabled={opBusy}
                  onClick={() => runReserveOp("redemption")}
                  style={{
                    padding: "5px 10px",
                    borderRadius: 999,
                    border: "1px solid #b91c1c",
                    background: "#b91c1c",
                    color: "#fef2f2",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: opBusy ? "default" : "pointer",
                    opacity: opBusy ? 0.7 : 1,
                  }}
                >
                  Redeem / burn
                </button>
              </div>

              {opMsg && (
                <div
                  style={{
                    marginTop: 4,
                    fontSize: 11,
                    color: "#374151",
                  }}
                >
                  {opMsg}
                </div>
              )}

              {/* PHO supply changes (dev log) */}
              <div
                style={{
                  marginTop: 20,
                  paddingTop: 12,
                  borderTop: "1px dashed #e5e7eb",
                }}
              >
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: "#111827",
                    marginBottom: 6,
                  }}
                >
                  PHO mint / burn log (dev)
                </div>

                {!snapshot.mint_burn_log ||
                snapshot.mint_burn_log.length === 0 ? (
                  <div
                    style={{
                      fontSize: 11,
                      color: "#9ca3af",
                    }}
                  >
                    No mint/burn events yet in this dev session.
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
                      <tr
                        style={{
                          borderBottom: "1px solid #e5e7eb",
                          color: "#6b7280",
                          textAlign: "left",
                        }}
                      >
                        <th style={{ padding: "4px 0" }}>Time</th>
                        <th style={{ padding: "4px 0" }}>Kind</th>
                        <th style={{ padding: "4px 0" }}>Amount (PHO)</th>
                        <th style={{ padding: "4px 0" }}>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...(snapshot.mint_burn_log || [])]
                        .slice(-10)
                        .reverse()
                        .map((ev: any) => {
                          const t = ev.created_at_ms
                            ? new Date(ev.created_at_ms).toLocaleString()
                            : "—";
                          const isMint = ev.kind === "MINT";

                          return (
                            <tr key={`${ev.created_at_ms}-${ev.reason || ""}`}>
                              <td
                                style={{
                                  padding: "3px 0",
                                  color: "#4b5563",
                                }}
                              >
                                {t}
                              </td>
                              <td
                                style={{
                                  padding: "3px 0",
                                  color: isMint ? "#16a34a" : "#b91c1c",
                                }}
                              >
                                {ev.kind}
                              </td>
                              <td
                                style={{
                                  padding: "3px 0",
                                  color: "#111827",
                                }}
                              >
                                {ev.amount_pho}
                              </td>
                              <td
                                style={{
                                  padding: "3px 0",
                                  color: "#6b7280",
                                }}
                              >
                                {ev.reason || "—"}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </>
        ) : (
          !loading && (
            <div
              style={{
                marginTop: 12,
                fontSize: 11,
                color: "#9ca3af",
              }}
            >
              No snapshot yet. Click <strong>Refresh GMA</strong>.
            </div>
          )
        )}
      </section>

      {/* ── Recurring mandates table ──────────── */}
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
            Photon Pay – Recurring instructions (dev)
          </div>
          <button
            type="button"
            onClick={refreshMandates}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            Refresh
          </button>
        </div>

        {mandatesErr && (
          <div style={{ fontSize: 12, color: "#b91c1c" }}>{mandatesErr}</div>
        )}

        {mandates.length === 0 && !mandatesErr ? (
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            No recurring instructions yet.
          </div>
        ) : null}

        {mandates.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 12,
              }}
            >
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "6px 4px" }}>Created</th>
                  <th style={{ padding: "6px 4px" }}>Payer</th>
                  <th style={{ padding: "6px 4px" }}>Payee</th>
                  <th style={{ padding: "6px 4px" }}>Amount</th>
                  <th style={{ padding: "6px 4px" }}>Frequency</th>
                  <th style={{ padding: "6px 4px" }}>Next due</th>
                  <th style={{ padding: "6px 4px" }}>Status</th>
                  <th style={{ padding: "6px 4px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {mandates.map((m) => {
                  const created = m.created_at_ms
                    ? new Date(m.created_at_ms).toLocaleString()
                    : "—";
                  const nextDue = m.next_due_ms
                    ? new Date(m.next_due_ms).toLocaleString()
                    : "—";

                  return (
                    <tr key={m.instr_id}>
                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        {created}
                      </td>
                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        <code>{m.from_account}</code>
                      </td>
                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        <code>{m.to_account}</code>
                      </td>
                      <td style={{ padding: "4px 4px", color: "#111827" }}>
                        {m.amount_pho} PHO
                      </td>
                      <td style={{ padding: "4px 4px", color: "#6b7280" }}>
                        {m.frequency}
                      </td>
                      <td style={{ padding: "4px 4px", color: "#6b7280" }}>
                        {nextDue}
                      </td>
                      <td
                        style={{
                          padding: "4px 4px",
                          color: m.active ? "#16a34a" : "#9ca3af",
                          fontSize: 11,
                        }}
                      >
                        {m.active ? "Active" : "Cancelled"}
                      </td>
                      <td style={{ padding: "4px 4px" }}>
                        {m.active ? (
                          <button
                            type="button"
                            disabled={busyCancel === m.instr_id}
                            onClick={() => handleCancel(m)}
                            style={{
                              padding: "4px 10px",
                              borderRadius: 999,
                              border: "1px solid #b91c1c",
                              background: "#fef2f2",
                              fontSize: 11,
                              color: "#b91c1c",
                              cursor:
                                busyCancel === m.instr_id
                                  ? "default"
                                  : "pointer",
                              opacity: busyCancel === m.instr_id ? 0.6 : 1,
                            }}
                          >
                            {busyCancel === m.instr_id ? "Cancelling…" : "Cancel"}
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
          </div>
        )}
      </section>

      {/* Glyph Bonds (dev) */}
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
            Glyph Bonds (dev)
          </div>
          <button
            type="button"
            onClick={refreshBonds}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            {bondsLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        <p
          style={{
            margin: 0,
            fontSize: 11,
            color: "#6b7280",
          }}
        >
          Dev-only view of GlyphBond series and positions. Uses an in-memory
          model and a single hard-coded account ({BOND_DEV_ACCOUNT}) for
          positions.
        </p>

        {bondsErr && (
          <div
            style={{
              fontSize: 11,
              color: "#b91c1c",
            }}
          >
            {bondsErr}
          </div>
        )}

        {/* Series table */}
        <div>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#111827",
              marginBottom: 6,
            }}
          >
            Bond series
          </div>

          {bondSeries.length === 0 ? (
            <div
              style={{
                fontSize: 11,
                color: "#9ca3af",
              }}
            >
              No bond series yet. Create one below.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 11,
                }}
              >
                <thead>
                  <tr
                    style={{
                      textAlign: "left",
                      color: "#6b7280",
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    <th style={{ padding: "4px 4px" }}>Series</th>
                    <th style={{ padding: "4px 4px" }}>Label</th>
                    <th style={{ padding: "4px 4px" }}>Coupon</th>
                    <th style={{ padding: "4px 4px" }}>Maturity</th>
                    <th style={{ padding: "4px 4px" }}>Issued (PHO)</th>
                    <th style={{ padding: "4px 4px" }}>Outstanding (PHO)</th>
                  </tr>
                </thead>
                <tbody>
                  {bondSeries.map((s) => {
                    const couponPct = (s.coupon_bps || 0) / 100;
                    const mat = s.maturity_ms
                      ? new Date(s.maturity_ms).toLocaleDateString()
                      : "—";
                    return (
                      <tr key={s.series_id}>
                        <td
                          style={{
                            padding: "4px 4px",
                            color: "#4b5563",
                            fontFamily: "monospace",
                          }}
                        >
                          {s.series_id}
                        </td>
                        <td style={{ padding: "4px 4px", color: "#111827" }}>
                          {s.label}
                        </td>
                        <td style={{ padding: "4px 4px", color: "#111827" }}>
                          {couponPct.toFixed(2)}%
                        </td>
                        <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                          {mat}
                        </td>
                        <td style={{ padding: "4px 4px", color: "#111827" }}>
                          {s.total_issued_pho}
                        </td>
                        <td style={{ padding: "4px 4px", color: "#111827" }}>
                          {s.total_outstanding_pho}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Create series form */}
        <div
          style={{
            marginTop: 10,
            paddingTop: 10,
            borderTop: "1px dashed #e5e7eb",
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#111827",
              marginBottom: 6,
            }}
          >
            Create bond series (dev)
          </div>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              alignItems: "center",
            }}
          >
            <input
              type="text"
              value={newSeriesLabel}
              onChange={(e) => setNewSeriesLabel(e.target.value)}
              placeholder="Label"
              style={{
                flex: 1,
                minWidth: 140,
                padding: "5px 9px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                fontSize: 11,
              }}
            />
            <input
              type="number"
              inputMode="numeric"
              value={newSeriesCouponBps}
              onChange={(e) => setNewSeriesCouponBps(e.target.value)}
              placeholder="Coupon (bps)"
              style={{
                width: 120,
                padding: "5px 9px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                fontSize: 11,
                textAlign: "right",
              }}
            />
            <input
              type="number"
              inputMode="numeric"
              value={newSeriesTermDays}
              onChange={(e) => setNewSeriesTermDays(e.target.value)}
              placeholder="Term (days)"
              style={{
                width: 120,
                padding: "5px 9px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                fontSize: 11,
                textAlign: "right",
              }}
            />
            <button
              type="button"
              onClick={handleCreateSeries}
              style={{
                padding: "6px 12px",
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
              Create series
            </button>
          </div>
        </div>

        {/* Positions for dev account */}
        <div
          style={{
            marginTop: 12,
            paddingTop: 10,
            borderTop: "1px dashed #e5e7eb",
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#111827",
              marginBottom: 6,
            }}
          >
            Positions for {BOND_DEV_ACCOUNT}
          </div>

          {bondPositions.length === 0 ? (
            <div
              style={{
                fontSize: 11,
                color: "#9ca3af",
              }}
            >
              No bond positions yet for this dev account.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 11,
                }}
              >
                <thead>
                  <tr
                    style={{
                      textAlign: "left",
                      color: "#6b7280",
                      borderBottom: "1px solid #e5e7eb",
                    }}
                  >
                    <th style={{ padding: "4px 4px" }}>Time</th>
                    <th style={{ padding: "4px 4px" }}>Series</th>
                    <th style={{ padding: "4px 4px" }}>Principal (PHO)</th>
                  </tr>
                </thead>
                <tbody>
                  {bondPositions.map((p) => {
                    const t = p.created_at_ms
                      ? new Date(p.created_at_ms).toLocaleString()
                      : "—";
                    return (
                      <tr key={p.position_id}>
                        <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                          {t}
                        </td>
                        <td
                          style={{
                            padding: "4px 4px",
                            color: "#4b5563",
                            fontFamily: "monospace",
                          }}
                        >
                          {p.series_id}
                        </td>
                        <td style={{ padding: "4px 4px", color: "#111827" }}>
                          {p.principal_pho}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Issue helper */}
          <div
            style={{
              marginTop: 8,
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              alignItems: "center",
            }}
          >
            <select
              value={issueSeriesId}
              onChange={(e) => setIssueSeriesId(e.target.value)}
              style={{
                padding: "4px 8px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                fontSize: 11,
                minWidth: 180,
              }}
            >
              {bondSeries.length === 0 ? (
                <option value="">No series</option>
              ) : (
                bondSeries.map((s) => (
                  <option key={s.series_id} value={s.series_id}>
                    {s.label} ({s.series_id})
                  </option>
                ))
              )}
            </select>
            <input
              type="number"
              inputMode="decimal"
              value={issueAmountPho}
              onChange={(e) => setIssueAmountPho(e.target.value)}
              placeholder="Principal PHO"
              style={{
                width: 130,
                padding: "5px 9px",
                borderRadius: 999,
                border: "1px solid #e5e7eb",
                fontSize: 11,
                textAlign: "right",
              }}
            />
            <button
              type="button"
              disabled={issueBusy || bondSeries.length === 0}
              onClick={handleIssueToDev}
              style={{
                padding: "6px 12px",
                borderRadius: 999,
                border: "1px solid #047857",
                background: "#047857",
                color: "#ecfdf5",
                fontSize: 11,
                fontWeight: 600,
                cursor:
                  issueBusy || bondSeries.length === 0 ? "default" : "pointer",
                opacity: issueBusy || bondSeries.length === 0 ? 0.7 : 1,
                whiteSpace: "nowrap",
              }}
            >
              {issueBusy
                ? "Issuing…"
                : `Issue to ${BOND_DEV_ACCOUNT}`}
            </button>
          </div>
        </div>
      </section>

      {/* Photon Pay – POS keypad (dev) */}
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
            Photon Pay – POS keypad (dev)
          </div>
        </div>

        <p
          style={{
            margin: 0,
            fontSize: 11,
            color: "#6b7280",
          }}
        >
          Generate a demo POS invoice for a merchant account. Later this will
          feed into QR / glyph scan-to-pay flows.
        </p>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            alignItems: "center",
          }}
        >
          <input
            type="text"
            value={posSeller}
            onChange={(e) => setPosSeller(e.target.value)}
            placeholder="Seller account (PHO)"
            style={{
              flex: 1,
              minWidth: 160,
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 12,
            }}
          />

          <input
            type="number"
            inputMode="decimal"
            value={posAmount}
            onChange={(e) => setPosAmount(e.target.value)}
            placeholder="Amount PHO"
            style={{
              width: 110,
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 12,
              textAlign: "right",
            }}
          />

          <input
            type="text"
            value={posMemo}
            onChange={(e) => setPosMemo(e.target.value)}
            placeholder="Memo (optional)"
            style={{
              flex: 1,
              minWidth: 160,
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 12,
            }}
          />

          <button
            type="button"
            onClick={handleMakePosInvoice}
            disabled={posBusy}
            style={{
              padding: "7px 14px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: "#0f172a",
              color: "#f9fafb",
              fontSize: 12,
              fontWeight: 600,
              cursor: posBusy ? "default" : "pointer",
              opacity: posBusy ? 0.6 : 1,
              whiteSpace: "nowrap",
            }}
          >
            {posBusy ? "Generating…" : "Generate invoice"}
          </button>
        </div>

        {posErr && (
          <div
            style={{
              fontSize: 11,
              color: "#b91c1c",
            }}
          >
            {posErr}
          </div>
        )}

        {posInvoice && (
          <div
            style={{
              marginTop: 6,
              padding: 8,
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              color: "#374151",
            }}
          >
            <div style={{ marginBottom: 4 }}>
              <strong>Invoice ID:</strong>{" "}
              {posInvoice.invoice?.invoice_id || "—"}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
              <div>
                <div style={{ color: "#6b7280" }}>Seller</div>
                <div>{posInvoice.invoice?.seller_account}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Amount</div>
                <div>{posInvoice.invoice?.amount_pho} PHO</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Memo</div>
                <div>{posInvoice.invoice?.memo || "—"}</div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Created</div>
                <div>
                  {posInvoice.invoice?.created_at_ms
                    ? new Date(
                        posInvoice.invoice.created_at_ms,
                      ).toLocaleString()
                    : "—"}
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: 8,
                padding: 8,
                borderRadius: 12,
                border: "1px dashed #d1d5db",
                background: "#ffffff",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontSize: 10,
                  color: "#9ca3af",
                  marginBottom: 4,
                }}
              >
                QR / glyph placeholder
              </div>
              <div
                style={{
                  width: 80,
                  height: 80,
                  margin: "0 auto",
                  borderRadius: 12,
                  border: "1px dashed #e5e7eb",
                  background:
                    "repeating-linear-gradient(45deg, #f9fafb, #f9fafb 4px, #e5e7eb 4px, #e5e7eb 8px)",
                }}
              />
            </div>
          </div>
        )}
      </section>

      {/* Photon Pay – Recent receipts (dev) */}
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
            Photon Pay – Recent receipts (dev)
          </div>
          <button
            type="button"
            onClick={refreshReceipts}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            {receiptsLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {receiptsErr && (
          <div style={{ fontSize: 12, color: "#b91c1c" }}>{receiptsErr}</div>
        )}

        {!receiptsErr && receipts.length === 0 && (
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            No PhotonPay receipts yet.
          </div>
        )}

        {receipts.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 12,
              }}
            >
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "6px 4px" }}>Time</th>
                  <th style={{ padding: "6px 4px" }}>From</th>
                  <th style={{ padding: "6px 4px" }}>To</th>
                  <th style={{ padding: "6px 4px" }}>Amount</th>
                  <th style={{ padding: "6px 4px" }}>Channel</th>
                  <th style={{ padding: "6px 4px" }}>Memo</th>
                </tr>
              </thead>
              <tbody>
                {receipts.map((r) => {
                  const t = r.created_at_ms
                    ? new Date(r.created_at_ms).toLocaleString()
                    : "—";
                  return (
                    <tr key={r.receipt_id}>
                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        {t}
                      </td>
                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        <code>{r.from_account}</code>
                      </td>
                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        <code>{r.to_account}</code>
                      </td>
                      <td style={{ padding: "4px 4px", color: "#111827" }}>
                        {r.amount_pho} PHO
                      </td>
                      <td style={{ padding: "4px 4px", color: "#6b7280" }}>
                        {r.channel}
                      </td>
                      <td style={{ padding: "4px 4px", color: "#6b7280" }}>
                        {r.memo || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}