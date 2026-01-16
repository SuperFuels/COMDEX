"use client";

import React, { useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";

type Item = { label: string; path: string; emoji?: string };

export default function GlyphNetSidebar({
  isOpen,
  onOpen,
  onClose,
  items,
  onGo,
}: {
  isOpen: boolean;
  onOpen: () => void;
  onClose: () => void;
  items: Item[];
  onGo: (path: string) => void;
}) {
  const sidebarRef = useRef<HTMLDivElement>(null);

  const toggle = () => {
    if (isOpen) onClose();
    else onOpen();
  };

  // Close when clicking outside the sidebar
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (!isOpen) return;
      const el = sidebarRef.current;
      if (!el) return;
      if (el.contains(e.target as Node)) return;
      onClose();
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  // Close on hash route change
  useEffect(() => {
    const h = () => isOpen && onClose();
    window.addEventListener("hashchange", h);
    return () => window.removeEventListener("hashchange", h);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Backdrop (only when open) */}
      <div
        className={[
          "fixed inset-0 z-[70] bg-black/40 transition-opacity",
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
        ].join(" ")}
        onClick={onClose}
      />

      {/* ✅ SINGLE sidebar that expands (no separate panel) */}
      <aside
        ref={sidebarRef}
        aria-label="GlyphNet sidebar"
        className={[
          "fixed left-0 top-0 z-[80] h-screen",
          "border-r border-border bg-background",
          "transition-[width] duration-200 ease-out",
          "overflow-hidden", // important so closed state stays thin
          isOpen ? "w-80" : "w-14",
        ].join(" ")}
      >
        <div className="flex h-full flex-col">
          {/* Top: G button row (always aligned with menu content) */}
          <div className="flex items-center justify-between px-2 py-3">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggle();
              }}
              className="h-11 w-11 rounded-xl bg-transparent grid place-items-center hover:bg-button-light/40 dark:hover:bg-button-dark/40"
              aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
              title={isOpen ? "Close sidebar" : "Open sidebar"}
            >
              {/* ✅ increase G size ~40% */}
              <Image src="/G.svg" alt="G" width={40} height={40} />
            </button>

            {/* Right-side close only visible when open */}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              className={[
                "h-11 w-11 rounded-xl bg-transparent grid place-items-center",
                "hover:bg-button-light/40 dark:hover:bg-button-dark/40",
                isOpen ? "opacity-100" : "opacity-0 pointer-events-none",
                "transition-opacity duration-150",
              ].join(" ")}
              aria-label="Close sidebar"
              title="Close"
            >
              ✕
            </button>
          </div>

          {/* Divider (only when open) */}
          <div className={isOpen ? "border-b border-border" : ""} />

          {/* Content */}
          <nav className="flex-1 overflow-y-auto px-2 py-4">
            {/* When closed: show compact icon stack */}
            {!isOpen && (
              <div className="flex flex-col items-center gap-2">
                {/* Home */}
                <Link
                  href="/"
                  className="h-11 w-11 rounded-xl grid place-items-center hover:bg-button-light/40 dark:hover:bg-button-dark/40"
                  title="Back to Site Home"
                >
                  🟢
                </Link>

                {/* Quick items */}
                {items.map((it) => (
                  <button
                    key={it.path}
                    onClick={() => onGo(it.path)}
                    className="h-11 w-11 rounded-xl grid place-items-center hover:bg-button-light/40 dark:hover:bg-button-dark/40"
                    title={it.label}
                  >
                    <span className="text-lg leading-none">{it.emoji ?? "•"}</span>
                  </button>
                ))}
              </div>
            )}

            {/* When open: full menu */}
            {isOpen && (
              <div className="px-2 space-y-6">
                <div className="flex flex-col gap-2">
                  <Link
                    href="/"
                    className="block py-3 px-3 rounded-lg bg-transparent hover:bg-button-light/40 dark:hover:bg-button-dark/40 font-medium"
                  >
                    🟢 Back to Site Home
                  </Link>

                  <button
                    onClick={() => onGo("/devtools")}
                    className="text-left py-3 px-3 rounded-lg bg-transparent hover:bg-button-light/40 dark:hover:bg-button-dark/40 font-medium"
                  >
                    🛠️ DevTools
                  </button>
                </div>

                <section>
                  <div className="mb-2 px-1 text-xs uppercase tracking-wide text-text/60">
                    GlyphNet Pages
                  </div>

                  <div className="flex flex-col">
                    {items.map((it) => (
                      <button
                        key={it.path}
                        onClick={() => onGo(it.path)}
                        className="flex items-center gap-3 py-3 px-3 rounded-lg hover:bg-button-light/40 dark:hover:bg-button-dark/40 text-sm text-left"
                      >
                        <span className="w-6 text-center">{it.emoji ?? "•"}</span>
                        <span>{it.label}</span>
                      </button>
                    ))}
                  </div>
                </section>
              </div>
            )}
          </nav>

          {/* Footer */}
          <div className="border-t border-border px-4 py-4 text-xs text-text/60">
            {isOpen ? "© Tessaris" : "©"}
          </div>
        </div>
      </aside>
    </>
  );
}