// /workspaces/COMDEX/frontend/pages/_app.tsx
import "@/lib/api";
import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { Inter } from "next/font/google";
import { useEffect } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/router";
import "katex/dist/katex.min.css";

// Client-only wrappers (prevents SSR/prerender crashes)
const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });
const HUDOverlay = dynamic(() => import("@/components/HUD/HUDOverlay"), { ssr: false });

const inter = Inter({ subsets: ["latin"], display: "swap" });

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const immersive = router.pathname.startsWith("/glyphnet") || router.pathname.startsWith("/pilot/mobile");

  useEffect(() => {
    console.log("🔍 NEXT_PUBLIC_API_URL =", process.env.NEXT_PUBLIC_API_URL);

    if (localStorage.getItem("token")) {
      localStorage.removeItem("manualDisconnect");
    }
  }, []);

  return (
    <div className={`${inter.className} flex min-h-screen bg-bg-page text-text-primary`}>
      {!immersive && <HUDOverlay />}

      <div className="flex-1 flex flex-col">
        {!immersive && <Navbar />}

        {/* NOTE: removed overflow-auto to restore normal page scrolling */}
        <main className="flex-1 relative">
          <Component {...pageProps} />
        </main>
      </div>
    </div>
  );
}
