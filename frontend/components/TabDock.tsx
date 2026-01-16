// frontend/components/TabDock.tsx
"use client";

import { useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/router";

export type TabDef = {
  key: string;
  label: string;
  href: string; // route path, e.g. "/glyph"
};

export default function TabDock({
  tabs,
  activeKey,
  className = "",
  maxWidth = 520, // “~2.5 tabs visible” feel
}: {
  tabs: readonly TabDef[];
  activeKey: string;
  className?: string;
  maxWidth?: number;
}) {
  const router = useRouter();
  const stripRef = useRef<HTMLDivElement | null>(null);

  const activeIdx = useMemo(
    () => Math.max(0, tabs.findIndex((t) => t.key === activeKey)),
    [tabs, activeKey],
  );

  const go = (idx: number) => {
    const t = tabs[idx];
    if (!t) return;
    // avoid push if already there
    if (router.asPath !== t.href) router.push(t.href);
  };

  // ✅ Swipe between tabs (mobile) — ignores mostly-vertical gestures
  useEffect(() => {
    let touchStartX = 0;
    let touchEndX = 0;
    let touchStartY = 0;
    let touchEndY = 0;

    const handleTouchStart = (e: TouchEvent) => {
      touchStartX = e.targetTouches[0].clientX;
      touchStartY = e.targetTouches[0].clientY;
      touchEndX = touchStartX;
      touchEndY = touchStartY;
    };

    const handleTouchMove = (e: TouchEvent) => {
      touchEndX = e.targetTouches[0].clientX;
      touchEndY = e.targetTouches[0].clientY;
    };

    const handleTouchEnd = () => {
      const dx = touchStartX - touchEndX;
      const dy = touchStartY - touchEndY;

      // don't hijack page scroll
      if (Math.abs(dy) > Math.abs(dx)) return;

      if (dx > 70 && activeIdx < tabs.length - 1) {
        go(activeIdx + 1); // Swipe Left -> Next Tab
      } else if (dx < -70 && activeIdx > 0) {
        go(activeIdx - 1); // Swipe Right -> Prev Tab
      }
    };

    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchmove", handleTouchMove, { passive: true });
    window.addEventListener("touchend", handleTouchEnd);

    return () => {
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
    };
  }, [activeIdx, tabs]); // activeIdx updates when route changes

  // ✅ Keep active tab pill visible (click OR swipe)
  useEffect(() => {
    const el = stripRef.current;
    if (!el) return;

    const btn = el.querySelector<HTMLElement>(`[data-tabkey="${activeKey}"]`);
    if (!btn) return;

    btn.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }, [activeKey]);

  return (
    <nav className={`mb-16 sticky top-4 z-50 flex justify-center ${className}`}>
      <div className="relative">
        {/* Left scroll button */}
        <button
          type="button"
          onClick={() => stripRef.current?.scrollBy({ left: -260, behavior: "smooth" })}
          className="hidden md:flex absolute left-[-14px] top-1/2 -translate-y-1/2 w-10 h-10 items-center justify-center rounded-full
                     bg-white/90 border border-gray-200 shadow-sm backdrop-blur-md hover:shadow-md transition"
          aria-label="Scroll tabs left"
        >
          <span className="text-gray-500 text-lg">‹</span>
        </button>

        {/* Right scroll button */}
        <button
          type="button"
          onClick={() => stripRef.current?.scrollBy({ left: 260, behavior: "smooth" })}
          className="hidden md:flex absolute right-[-14px] top-1/2 -translate-y-1/2 w-10 h-10 items-center justify-center rounded-full
                     bg-white/90 border border-gray-200 shadow-sm backdrop-blur-md hover:shadow-md transition"
          aria-label="Scroll tabs right"
        >
          <span className="text-gray-500 text-lg">›</span>
        </button>

        {/* Scroll container */}
        <div
          ref={stripRef}
          className="p-1 bg-white/70 backdrop-blur-md border border-gray-200 rounded-full shadow-sm
                     flex gap-1 overflow-x-auto no-scrollbar scroll-smooth"
          style={{
            maxWidth: `min(${maxWidth}px, 90vw)`,
            WebkitOverflowScrolling: "touch",
          }}
        >
          {tabs.map((t) => (
            <button
              key={t.key}
              data-tabkey={t.key}
              onClick={() => router.push(t.href)}
              className={`shrink-0 px-10 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${
                activeKey === t.key
                  ? "bg-[#0071e3] text-white shadow-md"
                  : "text-gray-500 hover:text-black"
              }`}
              aria-current={activeKey === t.key ? "page" : undefined}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Subtle fade edges */}
        <div className="pointer-events-none absolute left-0 top-0 h-full w-10 rounded-l-full bg-gradient-to-r from-[#f5f5f7] to-transparent" />
        <div className="pointer-events-none absolute right-0 top-0 h-full w-10 rounded-r-full bg-gradient-to-l from-[#f5f5f7] to-transparent" />
      </div>
    </nav>
  );
}