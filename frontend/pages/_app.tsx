import "@/lib/api";
import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { Inter } from "next/font/google";
import { useEffect } from "react";
import { useRouter } from "next/router";
import dynamic from "next/dynamic";
import "katex/dist/katex.min.css";

// Client-only wrappers (prevents SSR/prerender crashes)
const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });
const HUDOverlay = dynamic(() => import("@/components/HUD/HUDOverlay"), { ssr: false });

const inter = Inter({ subsets: ["latin"], display: "swap" });

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();

  // Hide legacy navbar on GlyphNet (GlyphNet mounts its own navbar)
  const hideNavbar =
    router.asPath.startsWith("/glyphnet") ||
    router.pathname.startsWith("/glyphnet");

  useEffect(() => {
    console.log("🔍 NEXT_PUBLIC_API_URL =", process.env.NEXT_PUBLIC_API_URL);
    if (typeof window !== "undefined" && localStorage.getItem("token")) {
      localStorage.removeItem("manualDisconnect");
    }
  }, []);

  return (
    <div className={`${inter.className} flex min-h-screen bg-bg-page text-text-primary`}>
      <HUDOverlay />

      <div className="flex-1 flex flex-col">
        {!hideNavbar && <Navbar />}

        <main className="flex-1 overflow-auto relative">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  );
}