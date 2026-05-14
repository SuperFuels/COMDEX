"use client";

import React, { useEffect, useMemo, useRef } from "react";
import Image from "next/image";
import Link from "next/link";

type Item = { label: string; path: string; emoji?: string }; // emoji ignored now (we use line icons)

// ---------- simple line icons (currentColor) ----------
function Icon({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={["h-5 w-5", className].join(" ")}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

const I = {
  Home: () => (
    <Icon>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5.5 10.5V21h13V10.5" />
    </Icon>
  ),
  Tools: () => (
    <Icon>
      <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2 2-2.4-.6-.6-2.4 2-2Z" />
    </Icon>
  ),
  Ledger: () => (
    <Icon>
      <rect x="5" y="4" width="14" height="16" rx="2" />
      <path d="M8 8h8M8 12h8M8 16h6" />
    </Icon>
  ),
  QfcHud: () => (
    <Icon>
      <path d="M12 3v3" />
      <path d="M6.5 6.5 8.6 8.6" />
      <path d="M3 12h3" />
      <path d="M6.5 17.5 8.6 15.4" />
      <path d="M12 18v3" />
      <path d="M17.5 17.5 15.4 15.4" />
      <path d="M18 12h3" />
      <path d="M17.5 6.5 15.4 8.6" />
      <circle cx="12" cy="12" r="3.2" />
    </Icon>
  ),
  QfcBio: () => (
    <Icon>
      <path d="M8 3c2.5 2.5 6 2.5 8 0" />
      <path d="M8 21c2.5-2.5 6-2.5 8 0" />
      <path d="M9 6c3 3 3 9 0 12" />
      <path d="M15 6c-3 3-3 9 0 12" />
    </Icon>
  ),
  Chat: () => (
    <Icon>
      <path d="M4 5h16v11H7l-3 3V5Z" />
      <path d="M8 9h8M8 12h6" />
    </Icon>
  ),
  X: () => (
    <Icon className="h-6 w-6">
      <path d="M6 6l12 12M18 6 6 18" />
    </Icon>
  ),
};

// Map by route label (fallback icon)
function iconFor(label: string) {
  const k = label.toLowerCase();
  if (k.includes("devtools") || k.includes("dev tools")) return <I.Tools />;
  if (k.includes("ledger")) return <I.Ledger />;
  if (k.includes("qfc hud")) return <I.QfcHud />;
  if (k.includes("qfc bio")) return <I.QfcBio />;
  if (k.includes("chat")) return <I.Chat />;
  return <I.Tools />;
}

// ---------- component ----------
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

  // Theme colors for sidebar only (don’t rely on --border which you set to white in dark mode)
  const shell = useMemo(
    () => ({
      // light: bg white + border #4a4a4a + icons/text #4a4a4a
      // dark: bg #4a4a4a + border #4a4a4a + icons/text white
      base: [
        "fixed left-0 top-0 z-[80] h-screen overflow-hidden",
        "transition-[width] duration-200 ease-out",
        isOpen ? "w-80" : "w-14",
        "bg-white text-[#4a4a4a] border-r border-[#4a4a4a]",
        "dark:bg-[#4a4a4a] dark:text-white dark:border-[#4a4a4a]",
      ].join(" "),
      hover: "hover:bg-black/5 dark:hover:bg-white/10",
    }),
    [isOpen],
  );

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

      {/* ✅ Single expanding sidebar */}
      <aside ref={sidebarRef} aria-label="GlyphNet sidebar" className={shell.base}>
        <div className="flex h-full flex-col">
          {/* Top row: G button always visible */}
          <div className="flex items-center justify-between px-1.5 py-2">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                toggle();
              }}
              className={[
                "ui-icon-btn",
                "h-11 w-11 min-w-[44px] min-h-[44px]", // ✅ ensure it never collapses away
                "rounded-xl grid place-items-center",
                shell.hover,
              ].join(" ")}
              aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
              title={isOpen ? "Close sidebar" : "Open sidebar"}
            >
              {/* ✅ slightly smaller than before so it never gets clipped in w-14 */}
              <Image src="/G.svg" alt="G" width={34} height={34} priority />
            </button>

            {/* Close icon only when open */}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              className={[
                "ui-icon-btn",
                "h-11 w-11 rounded-xl grid place-items-center",
                shell.hover,
                isOpen ? "opacity-100" : "opacity-0 pointer-events-none",
                "transition-opacity duration-150",
              ].join(" ")}
              aria-label="Close sidebar"
              title="Close"
            >
              <I.X />
            </button>
          </div>

          {/* Divider only when open */}
          <div className={isOpen ? "border-b border-[#4a4a4a] dark:border-[#4a4a4a]" : ""} />

          {/* Content */}
          <nav className="flex-1 overflow-y-auto px-2 py-3">
            {/* Collapsed: icon stack */}
            {!isOpen && (
              <div className="flex flex-col items-center gap-2">
                <Link
                  href="/"
                  className={[
                    "ui-icon-btn",
                    "h-11 w-11 rounded-xl grid place-items-center",
                    shell.hover,
                  ].join(" ")}
                  title="Back to Site Home"
                >
                  <span className="text-current">
                    <I.Home />
                  </span>
                </Link>

                {items.map((it) => (
                  <button
                    key={it.path}
                    type="button"
                    onClick={() => onGo(it.path)}
                    className={[
                      "ui-icon-btn",
                      "h-11 w-11 rounded-xl grid place-items-center",
                      shell.hover,
                    ].join(" ")}
                    title={it.label}
                  >
                    {iconFor(it.label)}
                  </button>
                ))}
              </div>
            )}

            {/* Expanded: full menu aligned under the G */}
            {isOpen && (
              <div className="px-2 space-y-6">
                <div className="flex flex-col gap-2 pt-1">
                  <Link
                    href="/"
                    className={[
                      "ui-icon-btn",
                      "flex items-center gap-3 rounded-lg px-3 py-3",
                      shell.hover,
                      "text-sm font-medium",
                    ].join(" ")}
                  >
                    <I.Home />
                    <span>Back to Site Home</span>
                  </Link>

                  <button
                    type="button"
                    onClick={() => onGo("/devtools")}
                    className={[
                      "ui-icon-btn",
                      "flex items-center gap-3 rounded-lg px-3 py-3",
                      shell.hover,
                      "text-sm font-medium text-left",
                    ].join(" ")}
                  >
                    <I.Tools />
                    <span>DevTools</span>
                  </button>
                </div>

                <section>
                  <div className="mb-2 px-1 text-xs uppercase tracking-wide opacity-70">
                    GlyphNet Pages
                  </div>

                  <div className="flex flex-col">
                    {items.map((it) => (
                      <button
                        key={it.path}
                        type="button"
                        onClick={() => onGo(it.path)}
                        className={[
                          "ui-icon-btn",
                          "flex items-center gap-3 rounded-lg px-3 py-3",
                          shell.hover,
                          "text-sm text-left",
                        ].join(" ")}
                      >
                        {iconFor(it.label)}
                        <span>{it.label}</span>
                      </button>
                    ))}
                  </div>
                </section>
              </div>
            )}
          </nav>

          {/* Footer */}
          <div className="border-t border-[#4a4a4a] dark:border-[#4a4a4a] px-4 py-3 text-xs opacity-70">
            {isOpen ? "© Tessaris" : "©"}
          </div>
        </div>
      </aside>
    </>
  );
}