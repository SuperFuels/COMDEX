// =====================================================
//  frontend/pages/sci/SciPanelHost.tsx
// =====================================================
"use client";

import { useMemo, useState, useEffect } from "react";
import { useRouter } from "next/router"; // pages/ router is correct here

import { getPanel, listPanels } from "@/lib/sci/panel_registry";
import "@/lib/sci/register_atomsheet";
import "@/lib/sci/register_sqs";
import "@/lib/sci/register_goals";
import "@/lib/sci/register_memory";
import "@/lib/sci/register_editor";

import type { PanelTypeId as PanelType } from "@/lib/sci/panel_registry";

type Tab = {
  tabId: string;
  type: PanelType;
  title: string;
  props: Record<string, any>;
};

type SciPanelHostProps = {
  wsUrl?: string;
  /** Optional shared container id from IDE (QFC + panels) */
  containerId?: string;
  initialTabs?: Tab[];
};

function shortId() {
  return Math.random().toString(36).slice(2, 8);
}

function mkContainerId(scope: PanelType): string {
  const t = new Date().toISOString().replace(/[-:.TZ]/g, "");
  const rand = Math.floor(Math.random() * 1000);
  return `sci:${scope}:${t}_${rand}`;
}

export default function SciPanelHost(props: SciPanelHostProps) {
  const router = useRouter();

  const [tabs, setTabs] = useState<Tab[]>(props.initialTabs || []);
  const [activeId, setActiveId] = useState<string>(tabs[0]?.tabId || "");
  const [fileToOpen, setFileToOpen] = useState<string>("");

  // restore tabs on first mount if no initialTabs provided
  useEffect(() => {
    if (props.initialTabs?.length) return;
    const raw =
      typeof window !== "undefined" ? localStorage.getItem("sci.tabs.v1") : null;
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as Tab[];
        setTabs(parsed);
        if (parsed[0]) setActiveId(parsed[0].tabId);
      } catch {
        /* ignore */
      }
    }
  }, [props.initialTabs]);

  // persist tabs whenever they change
  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem("sci.tabs.v1", JSON.stringify(tabs));
  }, [tabs]);

  const active = useMemo(
    () => tabs.find((t) => t.tabId === activeId) || tabs[0],
    [tabs, activeId]
  );

  function openTab(
    type: PanelType,
    title?: string,
    extra?: Record<string, any>
  ) {
    const pr = getPanel(type);
    if (!pr) return;
    const tabId = shortId();

    const fromExtra =
      typeof extra?.containerId === "string" && extra.containerId.trim().length
        ? extra.containerId.trim()
        : undefined;

    const containerId =
      (fromExtra as string | undefined) ??
      props.containerId ??
      mkContainerId(type);

    const propsForPanel = {
      ...(pr.makeDefaultProps?.() || {}),
      ...extra,
      wsUrl: props.wsUrl,
      authToken: process.env.NEXT_PUBLIC_AUTH_TOKEN,
      containerId,
      __tabId: tabId,
    };

    const tab: Tab = { tabId, type, title: title || pr.title, props: propsForPanel };
    setTabs((t) => [...t, tab]);
    setActiveId(tabId);
  }

  function closeTab(tabId: string) {
    setTabs((t) => {
      const idx = t.findIndex((x) => x.tabId === tabId);
      const next = t.filter((x) => x.tabId !== tabId);
      if (activeId === tabId && next.length) {
        setActiveId(next[Math.max(0, idx - 1)].tabId);
      }
      return next;
    });
  }

  // Deep-link support: /sci/SciPanelHost?panel=sqs&file=...&containerId=...&title=...
  useEffect(() => {
    // only auto-open from query if there are no tabs yet
    if (tabs.length) return;
    const q = router.query;
    const panel = (q.panel as string as PanelType) || "sqs";
    const pr = getPanel(panel);
    if (!pr) return;

    const file =
      (q.file as string) || "backend/data/sheets/example_sheet.atom";

    const fromQuery =
      typeof q.containerId === "string" && q.containerId.trim().length
        ? q.containerId.trim()
        : undefined;

    const containerId =
      (fromQuery as string | undefined) ??
      props.containerId ??
      mkContainerId(panel);

    const title = (q.title as string) || pr.title;

    openTab(panel, title, { file, containerId });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router.query, tabs.length, props.containerId]);

  const PanelComponent =
    (active && getPanel(active.type)?.component) ||
    (() => <div className="p-4 text-sm text-zinc-400">no panel</div>);

  return (
    <div className="w-full h-full flex flex-col">
      {/* top bar */}
      <div className="flex items-center gap-2 p-2 border-b border-neutral-800 bg-neutral-900">
        {/* new panel menu */}
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-1 rounded-lg bg-neutral-800 border border-neutral-700 text-sm"
            onClick={() => openTab("atomsheet")}
          >
            + AtomSheet
          </button>
          <button
            className="px-3 py-1 rounded-lg bg-neutral-800 border border-neutral-700 text-sm"
            onClick={() => openTab("goals")}
          >
            + Goals
          </button>
          <button
            className="px-3 py-1 rounded-lg bg-neutral-800 border border-neutral-700 text-sm"
            onClick={() => openTab("sqs")}
          >
            + SQS
          </button>
          {/* 🧠 New Memory Panel Button */}
          <button
            className="px-3 py-1 rounded-lg bg-neutral-800 border border-neutral-700 text-sm"
            onClick={() => openTab("memory")}
          >
            + Memory
          </button>
        </div>

        {/* quick open by file path (opens SQS panel) */}
        <div className="ml-3 flex items-center gap-2">
          <input
            value={fileToOpen}
            onChange={(e) => setFileToOpen(e.target.value)}
            placeholder="backend/data/sheets/example_sheet.atom"
            className="px-2 py-1 rounded bg-neutral-800 border border-neutral-700 text-xs text-zinc-200 w-[360px]"
          />
          <button
            className="px-2 py-1 rounded bg-neutral-800 border border-neutral-700 text-xs"
            onClick={() => {
              if (!fileToOpen.trim()) return;
              openTab("sqs", undefined, { file: fileToOpen.trim() });
              setFileToOpen("");
            }}
          >
            Open
          </button>
        </div>

        <div className="ml-4 text-xs text-zinc-500 truncate max-w-[30%]">
          Panels: {listPanels().map((p) => p.id).join(", ")}
        </div>

        {/* tabs */}
        <div className="ml-auto flex items-center gap-1 overflow-x-auto">
          {tabs.map((t) => (
            <div
              key={t.tabId}
              onClick={() => setActiveId(t.tabId)}
              className={[
                "px-3 py-1 rounded-lg border text-sm cursor-pointer select-none",
                activeId === t.tabId
                  ? "bg-neutral-700 border-neutral-600"
                  : "bg-neutral-900 border-neutral-800 hover:bg-neutral-800",
              ].join(" ")}
              title={t.props?.containerId}
            >
              <span>{t.title}</span>
              <button
                className="ml-2 text-zinc-400 hover:text-zinc-200"
                onClick={(e) => {
                  e.stopPropagation();
                  closeTab(t.tabId);
                }}
                aria-label="Close tab"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* active panel */}
      <div className="flex-1 min-h-0">
        {active ? (
          <PanelComponent {...active.props} />
        ) : (
          <div className="p-6 text-sm text-zinc-500">
            Open a panel to start.
          </div>
        )}
      </div>
    </div>
  );
}