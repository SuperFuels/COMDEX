import dynamic from "next/dynamic";

const AIONTerminal = dynamic(() => import("@/components/AIONTerminal"), {
  ssr: false,
});

export default function AIONDashboard() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">🧠 Talk to AION</h1>
      <AIONTerminal />
    </div>
  );
}
