import dynamic from "next/dynamic";
import type { NextPage } from "next";

// Client-only mount: prevents Next export/prerender from evaluating router-dependent code.
const AiClient = dynamic(
  () =>
    import("../src/glyphnet/NextGlyphnetApp").then((m: any) => m.default ?? m.NextGlyphnetApp),
  {
    ssr: false,
    loading: () => (
      <div style={{ padding: 24, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" }}>
        Loading Aion…
      </div>
    ),
  }
);

const AiPage: NextPage = () => {
  return <AiClient />;
};

export default AiPage;