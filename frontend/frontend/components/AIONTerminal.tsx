import { useState } from "react";

export default function AIONTerminal() {
  const [input, setInput] = useState("");
  const [log, setLog] = useState<string[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setLog((prev) => [...prev, `👤: ${input}`]);

    const res = await fetch("/api/aion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: input }),
    });
    const data = await res.json();

    setLog((prev) => [...prev, `🤖 AION: ${data.reply}`]);
    setInput("");
  };

  return (
    <div className="bg-black text-green-400 font-mono p-4 rounded shadow-md">
      <div className="h-64 overflow-y-scroll whitespace-pre-line mb-4">
        {log.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>
      <form onSubmit={handleSubmit} className="flex">
        <input
          className="flex-1 bg-gray-900 text-green-300 px-2 py-1 rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask AION anything..."
        />
        <button className="ml-2 px-4 py-1 bg-green-600 text-white rounded">
          Send
        </button>
      </form>
    </div>
  );
}
