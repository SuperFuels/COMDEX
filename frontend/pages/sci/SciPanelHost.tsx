import * as React from "react";
import { useMemo, useRef, useState } from "react";
import { getPanel, listPanels, registerPanel } from "./panels/panel_registry";

type Tab = {
  tabId: string;
  type: "atomsheet" | "sqs";
  title: string;
  props: Record<string, any>;
};

function shortId() {
  return Math.random().toString(36).slice(2, 8);
}

function mkContainerId(type: string, sid?: string) {
  return `sci:${type}:${sid || shortId()}`;
}

export default function SciPanelHost(props: {
  wsUrl?: string;
  initialTabs?: Tab[];
}) {
  const [tabs, setTabs] = useState<Tab[]>(
    props.initialTabs || []
  );
  const [activeId, setActiveId] = useState<string>(tabs[0]?.tabId || "");

  // persist/restore (optional)
  React.useEffect(() => {
    const raw = localStorage.getItem("sci.tabs.v1");
    if (raw && !props.initialTabs) {
      try {
        const parsed = JSON.parse(raw) as Tab[];
        setTabs(parsed);
        if (parsed[0]) setActiveId(parsed[0].tabId);
      } catch {}
    }
  }, []);
  React.useEffect(() => {
    localStorage.setItem("sci.tabs.v1", JSON.stringify(tabs));
  }, [tabs]);

  const active = useMemo(() => tabs.find(t => t.tabId === activeId) || tabs[0], [tabs, activeId]);

  function openTab(type: "atomsheet" | "sqs", title?: string, extra?: Record<string, any>) {
    const pr = getPanel(type);
    if (!pr) return;
    const tabId = shortId();
    const props = {
      ...(pr.makeDefaultProps?.() || {}),
      ...extra,
      wsUrl: props.wsUrl,
      containerId: mkContainerId(type),
      __tabId: tabId,
    };
    const tab: Tab = { tabId, type, title: title || pr.title, props };
    setTabs(t => [...t, tab]);
    setActiveId(tabId);
  }

  function closeTab(tabId: string) {
    setTabs(t => {
      const idx = t.findIndex(x => x.tabId === tabId);
      const next = t.filter(x => x.tabId !== tabId);
      if (activeId === tabId && next.length) {
        setActiveId(next[Math.max(0, idx - 1)].tabId);
      }
      return next;
    });
  }

  const PanelComponent =
    (active && getPanel(active.type)?.component) || (() => <div className="p-4 text-sm text-zinc-400">no panel</div>);

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
            onClick={() => openTab("sqs")}
          >
            + SQS
          </button>
        </div>

        <div className="ml-4 text-xs text-zinc-500">
          Panels: {listPanels().map(p => p.id).join(", ")}
        </div>

        {/* tabs */}
        <div className="ml-auto flex items-center gap-1 overflow-x-auto">
          {tabs.map(t => (
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
                onClick={(e) => { e.stopPropagation(); closeTab(t.tabId); }}
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
        {active ? <PanelComponent {...active.props} /> : (
          <div className="p-6 text-sm text-zinc-500">Open a panel to start.</div>
        )}
      </div>
    </div>
  );
}