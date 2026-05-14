import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export type VisitItem = {
  id: string;
  kg: string;
  topic_wa: string | null;
  thread_id: string | null;
  type: "visit";
  kind: "page" | "dwell" | string | null;
  ts: number;
  uri?: string | null;
  href?: string | null;
  host?: string | null;
  title?: string | null;
  referrer?: string | null;
  duration_s?: number | null;
  origin_id?: string | null;
};

type VisitsResponse = {
  ok: boolean;
  items: VisitItem[];
  next_cursor: string | null;
};

export function useVisitHistory(opts: {
  kg: "personal" | "work";
  topicWa?: string;
  threadId?: string;
  pageSize?: number;
}) {
  const { kg, topicWa, threadId, pageSize = 50 } = opts;

  const [items, setItems] = useState<VisitItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const seenIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    setItems([]);
    setNextCursor(null);
    setError(null);
    seenIdsRef.current = new Set();
  }, [kg, topicWa, threadId, pageSize]);

  const buildUrl = useCallback(
    (after?: string | null) => {
      const qs = new URLSearchParams();
      qs.set("kg", kg);
      if (threadId) qs.set("thread_id", threadId);
      else if (topicWa) qs.set("topic_wa", topicWa);
      qs.set("limit", String(pageSize));
      if (after) qs.set("after", after);
      return `/api/kg/view/visits?${qs.toString()}`;
    },
    [kg, topicWa, threadId, pageSize]
  );

  const loadMore = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(buildUrl(nextCursor));
      const data = (await res.json()) as VisitsResponse;
      if (!data.ok) throw new Error("visits request failed");

      const deduped: VisitItem[] = [];
      for (const v of data.items || []) {
        if (!seenIdsRef.current.has(v.id)) {
          seenIdsRef.current.add(v.id);
          deduped.push(v);
        }
      }
      setItems((prev) => [...prev, ...deduped]);
      setNextCursor(data.next_cursor);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [buildUrl, nextCursor, loading]);

  const hasMore = useMemo(() => !!nextCursor, [nextCursor]);
  const refresh = useCallback(async () => {
    setItems([]);
    seenIdsRef.current = new Set();
    setNextCursor(null);
    await loadMore();
  }, [loadMore]);

  return { items, loadMore, hasMore, loading, error, refresh, nextCursor };
}