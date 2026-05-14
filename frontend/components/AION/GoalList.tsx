import React, { useEffect, useState } from "react";
import { GripVertical, Edit, CheckCircle2, Save, XCircle } from "lucide-react";
import { motion, Reorder } from "framer-motion";

type Goal = {
  name: string;
  created_at?: string;
  status?: "pending" | "completed";
  strategy?: string;
};

export default function GoalList() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  useEffect(() => {
    fetch("/api/aion/goals")
      .then((res) => res.json())
      .then((data) => {
        setGoals(data.goals || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch goals", err);
        setLoading(false);
      });
  }, []);

  const updateGoalBackend = async (index: number) => {
    const goal = goals[index];
    try {
      await fetch("/api/aion/goals/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index, name: goal.name, status: goal.status }),
      });
    } catch (e) {
      console.error("Failed to update goal", e);
    }
  };

  const reorderGoalsBackend = async (newOrder: Goal[]) => {
    try {
      await fetch("/api/aion/goals/reorder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goals: newOrder }),
      });
    } catch (e) {
      console.error("Failed to reorder goals", e);
    }
  };

  const handleEdit = (index: number) => {
    setEditingIndex(index);
    setEditText(goals[index].name);
  };

  const handleSave = (index: number) => {
    const updated = [...goals];
    updated[index].name = editText.trim();
    setGoals(updated);
    setEditingIndex(null);
    updateGoalBackend(index);
  };

  const toggleStatus = (index: number) => {
    const updated = [...goals];
    updated[index].status =
      updated[index].status === "completed" ? "pending" : "completed";
    setGoals(updated);
    updateGoalBackend(index);
  };

  const handleReorder = (newOrder: Goal[]) => {
    setGoals(newOrder);
    reorderGoalsBackend(newOrder);
  };

  if (loading) return <p>Loading goals...</p>;

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">🎯 AION Goals</h2>

      {goals.length === 0 ? (
        <p>No goals yet.</p>
      ) : (
        <Reorder.Group
          as="ul"
          axis="y"
          values={goals}
          onReorder={handleReorder}
          className="space-y-3"
        >
          {goals.map((goal, index) => (
            <Reorder.Item
              key={index}
              value={goal}
              className="bg-white shadow p-4 rounded border-l-4 flex items-start gap-3"
              style={{
                borderColor:
                  goal.status === "completed" ? "#22c55e" : "#facc15",
              }}
            >
              <GripVertical className="text-gray-400 mt-1 cursor-move" />

              <div className="flex-1">
                {editingIndex === index ? (
                  <input
                    className="w-full border border-gray-300 rounded px-2 py-1"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSave(index);
                    }}
                  />
                ) : (
                  <div
                    className={`font-semibold text-lg ${
                      goal.status === "completed" ? "line-through" : ""
                    }`}
                  >
                    {goal.name}
                  </div>
                )}

                <div className="text-sm text-gray-500 mt-1 flex items-center gap-2">
                  Status:
                  <button
                    onClick={() => toggleStatus(index)}
                    className={`px-2 py-1 rounded text-xs ${
                      goal.status === "completed"
                        ? "bg-green-100 text-green-700"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {goal.status}
                  </button>

                  {goal.strategy && (
                    <span className="italic text-gray-400">
                      Strategy: {goal.strategy}
                    </span>
                  )}
                </div>

                {goal.created_at && (
                  <div className="text-xs text-gray-400 mt-1">
                    Created: {new Date(goal.created_at).toLocaleString()}
                  </div>
                )}
              </div>

              <div className="mt-1 flex gap-2">
                {editingIndex === index ? (
                  <>
                    <button onClick={() => handleSave(index)}>
                      <Save className="w-5 h-5 text-blue-600" />
                    </button>
                    <button onClick={() => setEditingIndex(null)}>
                      <XCircle className="w-5 h-5 text-gray-500" />
                    </button>
                  </>
                ) : (
                  <button onClick={() => handleEdit(index)}>
                    <Edit className="w-5 h-5 text-gray-500" />
                  </button>
                )}
              </div>
            </Reorder.Item>
          ))}
        </Reorder.Group>
      )}
    </div>
  );
}