import dynamic from "next/dynamic";
import Head from "next/head";

const AIONTerminal = dynamic(() => import("@/components/AIONTerminal"), { ssr: false });

export default function AIONDashboard() {
  return (
    <>
      <Head>
        <title>AION Dashboard</title>
      </Head>
      <main className="min-h-screen bg-black text-white p-4">
        <h1 className="text-2xl font-bold mb-4">👩‍💻 AION Dashboard</h1>
        <AIONTerminal />
      </main>
    </>
  );
}