import { useState } from "react";

export default function AIONTerminal() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResponse("");

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/aion/prompt`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ prompt }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        setResponse(`❌ AION error: ${data.detail || "Unknown error"}`);
      } else {
        setResponse(data.reply);
      }
    } catch (err) {
      setResponse("❌ AION error: Backend unreachable.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 max-w-xl mx-auto bg-gray-900 text-white rounded-xl shadow-xl">
      <h2 className="text-xl font-bold mb-2">🧠 AION Terminal</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <input
          type="text"
          className="p-2 rounded bg-gray-800 text-white focus:outline-none"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask AION anything..."
        />
        <button
          type="submit"
          className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded"
          disabled={loading}
        >
          {loading ? "Thinking..." : "Ask AION"}
        </button>
      </form>

      {response && (
        <div className="mt-4 p-3 bg-gray-800 rounded">
          <strong>💬 AION:</strong>
          <p className="mt-1 whitespace-pre-line">{response}</p>
        </div>
      )}
    </div>
  );
}