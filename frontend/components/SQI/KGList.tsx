"use client";
import React, { useEffect, useState } from "react";

export default function KGList() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch("/api/sqi/kg/nodes?kind=DRIFT_REPORT");
      const data = await res.json();
      setNodes(data.nodes || []);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <div className="text-sm text-gray-500">Loading KG…</div>;
  if (err) return <div className="text-sm text-red-600">Error: {err}</div>;

  return (
    <div className="space-y-2">
      <div className="text-sm font-semibold">Knowledge Graph — DRIFT Reports</div>
      {nodes.length === 0 ? (
        <div className="text-sm text-gray-500">No nodes yet.</div>
      ) : (
        <ul className="space-y-2">
          {nodes.map((n) => (
            <li key={n.id} className="border rounded p-2 bg-gray-50">
              <div className="text-sm"><b>{n.id}</b></div>
              <div className="text-xs">status: {n.props?.status} • total_weight: {n.props?.total_weight}</div>
              <div className="text-xs text-gray-600">{n.props?.source_path}</div>
            </li>
          ))}
        </ul>
      )}
      <button className="px-3 py-1 border rounded" onClick={load}>Refresh</button>
    </div>
  );
}