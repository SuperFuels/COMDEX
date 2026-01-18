// frontend/components/TabDock.tsx
"use client";

import { useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/router";

export type TabDef = {
  key: string;
  label: string;
  href: string; // e.g. "/glyph"
};

export default function TabDock({
  tabs,
  activeKey,
  className = "",
}: {
  tabs: readonly TabDef[];
  activeKey: string;
  className?: string;
}) {
  const router = useRouter();
  const dockRef = useRef<HTMLDivElement | null>(null);

  const activeIdx = useMemo(() => {
    const idx = tabs.findIndex((t) => t.key === activeKey);
    return idx >= 0 ? idx : 0;
  }, [tabs, activeKey]);

  const go = (idx: number) => {
    const t = tabs[idx];
    if (!t) return;
    if (router.asPath !== t.href) router.push(t.href);
  };

  const goPrev = () => {
    if (activeIdx > 0) go(activeIdx - 1);
  };

  const goNext = () => {
    if (activeIdx < tabs.length - 1) go(activeIdx + 1);
  };

  // Keep active tab centered in the dock (when it overflows)
  useEffect(() => {
    const root = dockRef.current;
    if (!root) return;

    const el = root.querySelector<HTMLButtonElement>(`button[data-tabkey="${activeKey}"]`);
    if (!el) return;

    el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [activeKey]);

  // ✅ Swipe between tabs (mobile) — ignores vertical gestures AND form elements
  // Also: if the gesture starts on the dock itself, don't hijack (lets users horizontally scroll the dock).
  useEffect(() => {
    let touchStartX = 0;
    let touchEndX = 0;
    let touchStartY = 0;
    let touchEndY = 0;

    const isFormEl = (el: EventTarget | null) => {
      const node = el as HTMLElement | null;
      if (!node) return false;
      const tag = node.tagName?.toLowerCase();
      return tag === "input" || tag === "textarea" || tag === "select" || node.isContentEditable;
    };

    const startedOnDock = (target: EventTarget | null) => {
      const node = target as Node | null;
      const root = dockRef.current;
      if (!node || !root) return false;
      return root.contains(node);
    };

    const handleTouchStart = (e: TouchEvent) => {
      if (isFormEl(e.target)) return;
      // let the dock be scrollable without switching tabs
      if (startedOnDock(e.target)) return;

      touchStartX = e.targetTouches[0].clientX;
      touchStartY = e.targetTouches[0].clientY;
      touchEndX = touchStartX;
      touchEndY = touchStartY;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (isFormEl(e.target)) return;
      if (startedOnDock(e.target)) return;

      touchEndX = e.targetTouches[0].clientX;
      touchEndY = e.targetTouches[0].clientY;
    };

    const handleTouchEnd = () => {
      const dx = touchStartX - touchEndX;
      const dy = touchStartY - touchEndY;

      // don't hijack page scroll
      if (Math.abs(dy) > Math.abs(dx)) return;
      if (Math.abs(dx) < 70) return;

      if (dx > 0 && activeIdx < tabs.length - 1) goNext();
      else if (dx < 0 && activeIdx > 0) goPrev();
    };

    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchmove", handleTouchMove, { passive: true });
    window.addEventListener("touchend", handleTouchEnd);

    return () => {
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
    };
  }, [activeIdx, tabs.length]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <nav className={`mb-16 sticky top-4 z-50 flex justify-center ${className}`}>
      <div className="relative group w-full max-w-[1400px]">
        {/* Left arrow (desktop hover) */}
        <button
          type="button"
          onClick={goPrev}
          disabled={activeIdx <= 0}
          className="hidden md:flex absolute left-0 top-1/2 -translate-y-1/2 w-10 h-10 items-center justify-center rounded-full
                     bg-white/90 border border-gray-200 shadow-sm backdrop-blur-md hover:shadow-md transition
                     opacity-0 group-hover:opacity-100 disabled:opacity-0 disabled:cursor-not-allowed z-10"
          aria-label="Previous tab"
        >
          <span className="text-gray-500 text-lg">‹</span>
        </button>

        {/* Right arrow (desktop hover) */}
        <button
          type="button"
          onClick={goNext}
          disabled={activeIdx >= tabs.length - 1}
          className="hidden md:flex absolute right-0 top-1/2 -translate-y-1/2 w-10 h-10 items-center justify-center rounded-full
                     bg-white/90 border border-gray-200 shadow-sm backdrop-blur-md hover:shadow-md transition
                     opacity-0 group-hover:opacity-100 disabled:opacity-0 disabled:cursor-not-allowed z-10"
          aria-label="Next tab"
        >
          <span className="text-gray-500 text-lg">›</span>
        </button>

        {/* Dock (scrollable) */}
        <div
          ref={dockRef}
          className="flex items-center gap-3 bg-white/70 backdrop-blur-2xl border border-gray-200 p-2 rounded-full shadow-lg shadow-gray-200/50
                     overflow-x-auto no-scrollbar px-3 md:px-14"
        >
          {tabs.map((t, index) => {
            const isActive = index === activeIdx;

            return (
              <button
                key={t.key}
                data-tabkey={t.key}
                onClick={() => go(index)}
                className={`relative whitespace-nowrap px-6 py-3 rounded-full text-sm font-semibold transition-all duration-300 ease-out ${
                  isActive
                    ? "bg-[#0071e3] text-white shadow-xl scale-[1.03] z-10"
                    : "text-gray-500 hover:text-gray-800 bg-transparent hover:bg-white/60"
                }`}
                aria-current={isActive ? "page" : undefined}
              >
                {t.label}
                {isActive && (
                  <span className="absolute inset-0 rounded-full bg-blue-400/20 animate-pulse -z-10" />
                )}
              </button>
            );
          })}
        </div>

        {/* Tailwind utility (no-scrollbar) fallback if you don't have it globally */}
        <style jsx>{`
          .no-scrollbar::-webkit-scrollbar {
            display: none;
          }
          .no-scrollbar {
            -ms-overflow-style: none;
            scrollbar-width: none;
          }
        `}</style>
      </div>
    </nav>
  );
}