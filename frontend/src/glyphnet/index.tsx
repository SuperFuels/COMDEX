import dynamic from "next/dynamic";
const GlyphnetApp = dynamic(() => import("./NextGlyphnetApp"), { ssr: false });
export default function GlyphnetPage() {
  return <GlyphnetApp />;
}