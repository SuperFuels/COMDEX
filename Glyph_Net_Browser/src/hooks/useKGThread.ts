// src/hooks/useKGThread.ts
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type KG = "personal" | "work";

export type KGItem = {
  id: string;
  ts: number;
  kg: KG;
  thread_id: string;
  topic_wa: string | null;
  type: "message" | "file" | "call" | "ptt_session";
  kind?: string | null;
  size?: number | null;
  sha256?: string | null;
  payload: any; // already parsed JSON from the API
};

export type ThreadAggregates = {
  call_summaries: Array<{
    call_id: string;
    started_ts: number | null;
    connected_ts: number | null;
    ended_ts: number | null;
    status: string | null;
    secs: number | null;
  }>;
  ptt_total_ms: number;
  ptt_sessions: number;
  attachments: number;
};

type ThreadResp = {
  ok: true;
  items: KGItem[];
  aggregates: ThreadAggregates;
  next_cursor: string | null;
};

export function useKGThread(opts: {
  kg: KG;
  topicWa: string;
  pageSize?: number;
}) {
  const { kg, topicWa, pageSize = 50 } = opts;
  const [items, setItems] = useState<KGItem[]>([]);
  const [aggregates, setAggregates] = useState<ThreadAggregates>({
    call_summaries: [],
    ptt_total_ms: 0,
    ptt_sessions: 0,
    attachments: 0,
  });
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setErr] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setItems([]);
    setAggregates({ call_summaries: [], ptt_total_ms: 0, ptt_sessions: 0, attachments: 0 });
    setNextCursor(null);
    setErr(null);
  }, []);

  const load = useCallback(async (cursor?: string | null) => {
    if (loading) return;
    setLoading(true);
    setErr(null);
    const ac = new AbortController();
    abortRef.current = ac;
    const qs = new URLSearchParams({
      kg,
      topic_wa: topicWa,
      limit: String(pageSize),
    });
    if (cursor) qs.set("after", cursor);

    try {
      const r = await fetch(`/api/kg/view/thread?${qs.toString()}`, { signal: ac.signal });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data: ThreadResp = await r.json();

      // Always present aggregates per backend contract
      setAggregates(data.aggregates);
      setItems((prev) => (cursor ? [...prev, ...data.items] : data.items));
      setNextCursor(data.next_cursor);
    } catch (e: any) {
      if (e.name !== "AbortError") setErr(e?.message || "fetch_failed");
    } finally {
      setLoading(false);
    }
  }, [kg, topicWa, pageSize, loading]);

  // (Re)load when kg/topic changes
  useEffect(() => {
    reset();
    load(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kg, topicWa]);

  const hasMore = useMemo(() => Boolean(nextCursor), [nextCursor]);
  const loadMore = useCallback(() => hasMore && load(nextCursor), [hasMore, load, nextCursor]);

  return { items, aggregates, loading, error, hasMore, loadMore, reload: () => load(null) };
}