import dynamic from "next/dynamic";

const GlyphNetClient = dynamic(() => import("@glyphnet/NextGlyphNet"), {
  ssr: false,
});

export default function GlyphNetPage() {
  return <GlyphNetClient />;
}