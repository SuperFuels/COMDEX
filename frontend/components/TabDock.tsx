// frontend/components/TabDock.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";

export type TabDef = {
  key: string;
  label: string;
  href: string; // e.g. "/glyph"
};

function classNames(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

export default function TabDock({
  tabs,
  activeKey,
  className = "",
}: {
  tabs: readonly TabDef[];
  activeKey: string;
  className?: string;
}) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [canL, setCanL] = useState(false);
  const [canR, setCanR] = useState(false);

  const activeIdx = useMemo(() => {
    const idx = tabs.findIndex((t) => t.key === activeKey);
    return idx >= 0 ? idx : 0;
  }, [tabs, activeKey]);

  const updateEdges = () => {
    const el = scrollerRef.current;
    if (!el) return;
    const max = el.scrollWidth - el.clientWidth;
    setCanL(el.scrollLeft > 2);
    setCanR(el.scrollLeft < max - 2);
  };

  const nudge = (dir: -1 | 1) => {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.max(220, el.clientWidth * 0.6), behavior: "smooth" });
  };

  // keep active tab centered-ish
  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const chip = el.querySelector<HTMLElement>(`a[data-tabkey="${activeKey}"]`);
    if (!chip) return;

    const left = chip.offsetLeft - (el.clientWidth - chip.clientWidth) / 2;
    el.scrollTo({ left: Math.max(0, left), behavior: "smooth" });
  }, [activeKey]);

  // edges + resize
  useEffect(() => {
    updateEdges();
    const el = scrollerRef.current;
    if (!el) return;

    const onScroll = () => updateEdges();
    const onResize = () => updateEdges();

    el.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);

    requestAnimationFrame(updateEdges);
    return () => {
      el.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
    };
  }, [tabs.length]);

  // ✅ Swipe between tabs (mobile) — only when gesture starts on the dock
  useEffect(() => {
    let sx = 0,
      sy = 0,
      ex = 0,
      ey = 0;

    const startedOnDock = (target: EventTarget | null) => {
      const node = target as Node | null;
      const root = scrollerRef.current;
      if (!node || !root) return false;
      return root.contains(node);
    };

    const isFormEl = (el: EventTarget | null) => {
      const node = el as HTMLElement | null;
      if (!node) return false;
      const tag = node.tagName?.toLowerCase();
      return tag === "input" || tag === "textarea" || tag === "select" || node.isContentEditable;
    };

    const onStart = (e: TouchEvent) => {
      if (isFormEl(e.target)) return;
      if (!startedOnDock(e.target)) return;

      sx = e.targetTouches[0].clientX;
      sy = e.targetTouches[0].clientY;
      ex = sx;
      ey = sy;
    };

    const onMove = (e: TouchEvent) => {
      if (isFormEl(e.target)) return;
      if (!startedOnDock(e.target)) return;

      ex = e.targetTouches[0].clientX;
      ey = e.targetTouches[0].clientY;
    };

    const onEnd = () => {
      const dx = sx - ex;
      const dy = sy - ey;

      // don't hijack vertical scrolling
      if (Math.abs(dy) > Math.abs(dx)) return;
      if (Math.abs(dx) < 70) return;

      // swipe left => next tab, swipe right => prev tab
      const next = Math.min(tabs.length - 1, activeIdx + 1);
      const prev = Math.max(0, activeIdx - 1);

      if (dx > 0 && next !== activeIdx) window.location.href = tabs[next].href;
      if (dx < 0 && prev !== activeIdx) window.location.href = tabs[prev].href;
    };

    window.addEventListener("touchstart", onStart, { passive: true });
    window.addEventListener("touchmove", onMove, { passive: true });
    window.addEventListener("touchend", onEnd);

    return () => {
      window.removeEventListener("touchstart", onStart);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onEnd);
    };
  }, [activeIdx, tabs]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <nav className={classNames("sticky top-2 z-50 flex justify-center", className)}>
      {/* ✅ fit-content wrapper so the pill doesn't span the whole navbar */}
      <div className="relative w-fit max-w-[calc(100vw-16px)]">
        {/* Left arrow (desktop only) */}
        <button
          type="button"
          onClick={() => nudge(-1)}
          aria-label="Scroll tabs left"
          className={classNames(
            "hidden md:grid place-items-center",
            "absolute left-[-34px] top-1/2 -translate-y-1/2 h-8 w-8 rounded-full",
            "bg-white/90 border border-gray-200 shadow-sm backdrop-blur-md hover:shadow-md transition",
            canL ? "opacity-100" : "opacity-30 pointer-events-none"
          )}
        >
          <span className="text-gray-500 text-lg leading-none">‹</span>
        </button>

        {/* Right arrow (desktop only) */}
        <button
          type="button"
          onClick={() => nudge(1)}
          aria-label="Scroll tabs right"
          className={classNames(
            "hidden md:grid place-items-center",
            "absolute right-[-34px] top-1/2 -translate-y-1/2 h-8 w-8 rounded-full",
            "bg-white/90 border border-gray-200 shadow-sm backdrop-blur-md hover:shadow-md transition",
            canR ? "opacity-100" : "opacity-30 pointer-events-none"
          )}
        >
          <span className="text-gray-500 text-lg leading-none">›</span>
        </button>

        {/* ✅ Scroller: capsule only slightly wider than tabs */}
        <div
          ref={scrollerRef}
          className={classNames(
            "max-w-[calc(100vw-16px)] md:max-w-[min(980px,calc(100vw-120px))]",
            "overflow-x-auto overflow-y-hidden no-scrollbar",
            "bg-white/70 backdrop-blur-2xl border border-gray-200",
            "rounded-full shadow-lg shadow-gray-200/50",
            "px-2 py-2"
          )}
        >
          <div className="inline-flex items-center gap-2">
            {tabs.map((t) => {
              const isActive = t.key === activeKey;

              return (
                <Link
                  key={t.key}
                  href={t.href}
                  data-tabkey={t.key}
                  className={classNames(
                    "relative shrink-0 whitespace-nowrap rounded-full border transition-all duration-200 ease-out",
                    "px-3 py-1.5 md:px-4 md:py-2",
                    "text-xs md:text-sm font-semibold",
                    isActive
                      ? "bg-[#0071e3] text-white border-[#0071e3] shadow-sm"
                      : "bg-white/60 border-transparent text-gray-600 hover:text-gray-900 hover:bg-white"
                  )}
                  aria-current={isActive ? "page" : undefined}
                >
                  {t.label}
                  {isActive && <span className="absolute inset-0 rounded-full bg-blue-400/20 animate-pulse -z-10" />}
                </Link>
              );
            })}
          </div>
        </div>

        {/* mobile hint */}
        <div className="md:hidden mt-1 text-[10px] text-slate-400 text-center select-none">swipe tabs →</div>

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