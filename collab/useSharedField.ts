// collab/useSharedField.ts
import { useEffect, useMemo, useRef, useState } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";
import { nanoid } from "nanoid";
import type { BeamRec, LinkRec, NodeRec, Presence } from "./types";

// --- helpers ---
const WS_URL = process.env.NEXT_PUBLIC_COLLAB_WS || "ws://localhost:1234";

function ensureMaps(doc: Y.Doc) {
  const graph = doc.getMap("graph");
  if (!graph.get("nodes")) graph.set("nodes", new Y.Map());
  if (!graph.get("links")) graph.set("links", new Y.Map());
  if (!graph.get("beams")) graph.set("beams", new Y.Map());
  return {
    nodesMap: graph.get("nodes") as Y.Map<Y.Map<any>>,
    linksMap: graph.get("links") as Y.Map<Y.Map<any>>,
    beamsMap: graph.get("beams") as Y.Map<Y.Map<any>>,
  };
}

function mapToArray<T = any>(m: Y.Map<Y.Map<any>>): T[] {
  const out: T[] = [];
  m.forEach((ymap) => {
    const o: any = {};
    ymap.forEach((v, k) => (o[k] = v));
    out.push(o);
  });
  return out;
}

export function useSharedField(containerId: string) {
  const providerRef = useRef<WebsocketProvider | null>(null);
  const docRef = useRef<Y.Doc | null>(null);

  const [nodes, setNodes] = useState<NodeRec[]>([]);
  const [links, setLinks] = useState<LinkRec[]>([]);
  const [beams, setBeams] = useState<BeamRec[]>([]);
  const [others, setOthers] = useState<Presence[]>([]);
  const [me, setMe] = useState<Presence>(() => ({
    id: nanoid(8),
    name: `user-${Math.floor(Math.random() * 999)}`,
    color: `hsl(${Math.floor(Math.random() * 360)}, 70%, 55%)`,
    role: "editor",
  }));

  // connect
  useEffect(() => {
    const doc = new Y.Doc();
    docRef.current = doc;

    const room = containerId || "default";
    const provider = new WebsocketProvider(`${WS_URL}?room=${encodeURIComponent(room)}`, room, doc, {
      connect: true,
    });
    providerRef.current = provider;

    const { nodesMap, linksMap, beamsMap } = ensureMaps(doc);

    const pushState = () => {
      setNodes(mapToArray<NodeRec>(nodesMap));
      setLinks(mapToArray<LinkRec>(linksMap));
      setBeams(mapToArray<BeamRec>(beamsMap));
    };

    // initial + observers
    pushState();
    const obs = () => pushState();
    nodesMap.observeDeep(obs);
    linksMap.observeDeep(obs);
    beamsMap.observeDeep(obs);

    // presence (awareness)
    const aw = provider.awareness;
    aw.setLocalState({ user: me });
    const onAwareness = () => {
      const arr: Presence[] = [];
      aw.getStates().forEach((s: any) => s?.user && arr.push(s.user));
      setOthers(arr.filter((p) => p.id !== me.id));
    };
    aw.on("change", onAwareness);
    onAwareness();

    return () => {
      nodesMap.unobserveDeep(obs);
      linksMap.unobserveDeep(obs);
      beamsMap.unobserveDeep(obs);
      aw.off("change", onAwareness);
      provider.destroy();
      doc.destroy();
      providerRef.current = null;
      docRef.current = null;
    };
  }, [containerId, me.id]); // re-connect when container changes

  // mutation helpers (CRDT-safe)
  const applyOp = useMemo(() => {
    const get = () => {
      const doc = docRef.current!;
      return ensureMaps(doc);
    };

    return {
      addNode(input: Partial<NodeRec>) {
        const id = input.id || nanoid(10);
        const { nodesMap } = get();
        const y = new Y.Map();
        Object.entries({ ...input, id }).forEach(([k, v]) => y.set(k, v as any));
        nodesMap.set(id, y);
        return id;
      },
      updateNode(id: string, patch: Partial<NodeRec>) {
        const { nodesMap } = get();
        const y = nodesMap.get(id);
        if (!y) return;
        Object.entries(patch).forEach(([k, v]) => y.set(k, v as any));
      },
      removeNode(id: string) {
        const { nodesMap } = get();
        nodesMap.delete(id);
      },

      addLink(input: Partial<LinkRec>) {
        const id = input.id || nanoid(10);
        const { linksMap } = get();
        const y = new Y.Map();
        Object.entries({ ...input, id }).forEach(([k, v]) => y.set(k, v as any));
        linksMap.set(id, y);
        return id;
      },
      updateLink(id: string, patch: Partial<LinkRec>) {
        const { linksMap } = get();
        const y = linksMap.get(id);
        if (!y) return;
        Object.entries(patch).forEach(([k, v]) => y.set(k, v as any));
      },
      removeLink(id: string) {
        const { linksMap } = get();
        linksMap.delete(id);
      },

      addBeam(input: Partial<BeamRec>) {
        const id = input.id || nanoid(10);
        const { beamsMap } = get();
        const y = new Y.Map();
        Object.entries({ ...input, id }).forEach(([k, v]) => y.set(k, v as any));
        beamsMap.set(id, y);
        return id;
      },
      updateBeam(id: string, patch: Partial<BeamRec>) {
        const { beamsMap } = get();
        const y = beamsMap.get(id);
        if (!y) return;
        Object.entries(patch).forEach(([k, v]) => y.set(k, v as any));
      },
      removeBeam(id: string) {
        const { beamsMap } = get();
        beamsMap.delete(id);
      },

      // presence
      setCursor(x: number, y: number) {
        const p = { ...me, cursor: [x, y] as [number, number] };
        setMe(p);
        providerRef.current?.awareness?.setLocalStateField("user", p);
      },
      setSelection(ids: string[]) {
        const p = { ...me, selectionGlyphIds: ids };
        setMe(p);
        providerRef.current?.awareness?.setLocalStateField("user", p);
      },
      setViewport(center: [number, number, number], zoom: number) {
        const p = { ...me, viewport: { center, zoom } };
        setMe(p);
        providerRef.current?.awareness?.setLocalStateField("user", p);
      },
    };
  }, [me, containerId]);

  return { nodes, links, beams, applyOp, me, others };
}