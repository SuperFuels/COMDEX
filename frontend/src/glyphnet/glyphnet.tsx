import dynamic from "next/dynamic";

const GlyphNetClient = dynamic(() => import("@glyphnet/NextGlyphnetApp"), {
  ssr: false,
});

export default function GlyphNetPage() {
  return <GlyphNetClient />;
}