import React, { useEffect, useState } from "react";
import { Card } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Check, X, Zap } from "lucide-react";

interface TessarisIntent {
  id: string;
  type: string;
  description: string;
  status: "pending" | "approved" | "executed" | "denied";
  source: string;
  target?: string;
  glyph?: string;
}

const TessarisIntentExecutor: React.FC = () => {
  const [intents, setIntents] = useState<TessarisIntent[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchIntents = async () => {
    setLoading(true);
    const res = await fetch("/api/aion/tessaris-intents");
    const data = await res.json();
    setIntents(data.intents || []);
    setLoading(false);
  };

  const updateIntentStatus = async (id: string, status: TessarisIntent["status"]) => {
    await fetch(`/api/aion/tessaris-intents/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    fetchIntents();
  };

  useEffect(() => {
    fetchIntents();
  }, []);

  return (
    <div className="mt-4 w-full p-4 border rounded">
      <h2 className="text-xl font-bold mb-2">🧠 Tessaris Intent Queue</h2>
      {loading ? (
        <p>Loading intents...</p>
      ) : intents.length === 0 ? (
        <p>No intents found.</p>
      ) : (
        <div className="grid gap-4">
          {intents.map((intent) => (
            <div key={intent.id} className="border p-4 rounded bg-white">
              <div className="flex justify-between items-center mb-1">
                <span className="font-semibold">{intent.description}</span>
                <Badge className="bg-gray-200 text-gray-700 px-2 py-0.5 text-xs rounded">
                  {intent.type}
                </Badge>
              </div>
              <div className="text-sm text-gray-500 mb-2">
                Source: {intent.source}
                {intent.target && <> → Target: {intent.target}</>}
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => updateIntentStatus(intent.id, "approved")}
                  disabled={intent.status !== "pending"}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white"
                >
                  <Check className="w-4 h-4 mr-1 inline" /> Approve
                </Button>
                <Button
                  onClick={() => updateIntentStatus(intent.id, "denied")}
                  disabled={intent.status !== "pending"}
                  className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white"
                >
                  <X className="w-4 h-4 mr-1 inline" /> Deny
                </Button>
                <Button
                  onClick={() => updateIntentStatus(intent.id, "executed")}
                  disabled={intent.status !== "approved"}
                  className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white"
                >
                  <Zap className="w-4 h-4 mr-1 inline" /> Execute
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TessarisIntentExecutor;