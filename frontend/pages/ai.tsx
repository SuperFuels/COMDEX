// frontend/pages/ai.tsx
import dynamic from "next/dynamic";
import type { NextPage } from "next";
import Shell from "@/components/Shell";

// Client-only mount
const ProofClient = dynamic(() => import("@/tabs/Aion/AionProofOfLifeDashboard"), {
  ssr: false,
  loading: () => (
    <div style={{ padding: 24, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" }}>
      Loading AI…
    </div>
  ),
});

const AiPage: NextPage = () => {
  return (
    <Shell activeKey="ai">
      <ProofClient />
    </Shell>
  );
};

export default AiPage;