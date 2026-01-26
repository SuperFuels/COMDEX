// frontend/components/GlyphNetNavbar.tsx
"use client";

import React from "react";
import Image from "next/image";
import Link from "next/link";
import { ShellTabsBar } from "./Shell";

export default function GlyphNetNavbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-[#e5e7eb] bg-background text-text">
      <div className="px-3 sm:px-4">
        {/* Row 1: Logo only */}
        <div className="h-12 flex items-center">
          <Link href="/" className="logo-link flex items-center">
            <Image
              src="/tessaris_light_logo.svg"
              alt="Tessaris"
              width={132}
              height={40}
              priority
              className="block dark:hidden border-none"
            />
            <Image
              src="/tessaris_dark_logo.svg"
              alt="Tessaris"
              width={132}
              height={40}
              priority
              className="hidden dark:block border-none"
            />
          </Link>
        </div>

        {/* Row 2: Tabs (mobile scroll) */}
        <div className="pb-2">
          <ShellTabsBar />
        </div>
      </div>
    </header>
  );
}