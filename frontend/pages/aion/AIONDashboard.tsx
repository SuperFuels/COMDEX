"use client";

import React, { useEffect, useState } from "react";

type Milestone = {
  name: string;
  timestamp: string;
  dream_excerpt?: string;
};

type Goal = {
  name: string;
  description?: string;
  reward?: number;
  completed_at?: string | null;
  status?: string;
};

type Strategy = {
  id: string;
  goal: string;
  action: string;
  priority: number;
};

type LearnedSkill = {
  title: string;
  tags: string[];
  status: string;
  learned_on: string;
};

export default function AIONDashboard() {
  const [status, setStatus] = useState<{
    phase: string;
    milestones: Milestone[];
    unlocked: string[];
    locked: string[];
  } | null>(null);

  const [goals, setGoals] = useState<Goal[]>([]);
  const [currentGoal, setCurrentGoal] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [learnedSkills, setLearnedSkills] = useState<LearnedSkill[]>([]);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

  useEffect(() => {
    fetch(`${API_BASE}/aion/status`)
      .then((res) => res.json())
      .then(setStatus)
      .catch(console.error);

    fetch(`${API_BASE}/aion/goals`)
      .then((res) => res.json())
      .then((data) => setGoals(data.goals || []))
      .catch(console.error);

    fetch(`${API_BASE}/aion/current-goal`)
      .then((res) => res.json())
      .then((data) => setCurrentGoal(data.current_goal || null))
      .catch(console.error);

    fetch(`${API_BASE}/aion/strategy-plan`)
      .then((res) => res.json())
      .then((data) => setStrategies(data.strategy || []))
      .catch(console.error);

    fetch(`${API_BASE}/aion/learned-skills`)
      .then((res) => res.json())
      .then(setLearnedSkills)
      .catch(() => setLearnedSkills([]));
  }, [API_BASE]);

  const markComplete = (goalName: string) => {
    fetch(`${API_BASE}/aion/goals/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: goalName }),
    })
      .then((res) => res.json())
      .then(() => {
        fetch(`${API_BASE}/aion/goals`)
          .then((res) => res.json())
          .then((data) => setGoals(data.goals || []));
      })
      .catch(console.error);
  };

  const editGoalName = (oldName: string, newName: string) => {
    fetch(`${API_BASE}/aion/goals/edit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ old_name: oldName, new_name: newName }),
    })
      .then((res) => res.json())
      .then(() => {
        fetch(`${API_BASE}/aion/goals`)
          .then((res) => res.json())
          .then((data) => setGoals(data.goals || []));
      })
      .catch(console.error);
  };

  return (
    <div className="p-6 max-w-5xl mx-auto font-sans text-black bg-white rounded-xl shadow-xl overflow-y-auto max-h-screen">
      <h1 className="text-3xl font-bold mb-6">🧠 AION Dashboard</h1>

      <section className="mb-6">
        <h2 className="text-2xl font-semibold mb-2">Status</h2>
        {status ? (
          <>
            <p>
              <strong>Phase:</strong> {status.phase}
            </p>
            <p>
              <strong>Unlocked Modules:</strong> {status.unlocked.join(", ")}
            </p>
            <p>
              <strong>Locked Modules:</strong> {status.locked.join(", ")}
            </p>
            <h3 className="mt-4 text-xl font-semibold">Milestones</h3>
            <ul className="list-disc list-inside ml-4 space-y-2">
              {status.milestones.map((m, i) => (
                <li key={i}>
                  <strong>{m.name}</strong> —{" "}
                  <span className="text-gray-500">
                    {new Date(m.timestamp).toLocaleString()}
                  </span>
                  {m.dream_excerpt && (
                    <p className="italic text-gray-600 mt-1">{m.dream_excerpt}</p>
                  )}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p>Loading status...</p>
        )}
      </section>

      <section className="mb-6">
        <h2 className="text-2xl font-semibold mb-2">Current Goal</h2>
        {currentGoal ? <p>{currentGoal}</p> : <p>Loading current goal...</p>}
      </section>

      <section className="mb-6">
        <h2 className="text-2xl font-semibold mb-2">Goals</h2>
        {goals.length === 0 ? (
          <p>No goals loaded.</p>
        ) : (
          <ul className="space-y-4">
            {goals.map((goal) => (
              <li key={goal.name}>
                <EditableGoal
                  goal={goal}
                  onComplete={() => markComplete(goal.name)}
                  onEdit={editGoalName}
                />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mb-6">
        <h2 className="text-2xl font-semibold mb-2">Top Strategies</h2>
        {strategies.length === 0 ? (
          <p>No strategies loaded.</p>
        ) : (
          <ul className="list-disc list-inside ml-4 space-y-2">
            {strategies.map((s) => (
              <li key={s.id}>
                <strong>{s.goal}</strong>: {s.action} (Priority: {s.priority})
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-2xl font-semibold mb-2">Learned Skills</h2>
        {learnedSkills.length === 0 ? (
          <p>No learned skills found.</p>
        ) : (
          <ul className="list-disc list-inside ml-4 space-y-2">
            {learnedSkills.map((skill, i) => (
              <li key={i}>
                <strong>{skill.title}</strong> [{skill.status}] — Learned on:{" "}
                {new Date(skill.learned_on).toLocaleString()}
                <br />
                Tags: {skill.tags.join(", ")}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function EditableGoal({
  goal,
  onComplete,
  onEdit,
}: {
  goal: Goal;
  onComplete: () => void;
  onEdit: (oldName: string, newName: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [newName, setNewName] = useState(goal.name);

  return (
    <div>
      {editing ? (
        <>
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="border border-gray-600 rounded px-2 py-1 mr-2 text-black"
          />
          <button
            onClick={() => {
              onEdit(goal.name, newName);
              setEditing(false);
            }}
            className="bg-green-600 px-3 py-1 rounded text-white"
          >
            Save
          </button>
          <button
            onClick={() => setEditing(false)}
            className="ml-2 px-3 py-1 rounded border border-gray-600"
          >
            Cancel
          </button>
        </>
      ) : (
        <>
          <span
            className={`cursor-pointer ${goal.completed_at ? "line-through text-gray-500" : ""}`}
            onDoubleClick={() => setEditing(true)}
          >
            {goal.name}
          </span>{" "}
          <button
            onClick={onComplete}
            disabled={!!goal.completed_at}
            className="ml-2 px-2 py-1 rounded bg-blue-600 text-white disabled:opacity-50"
          >
            Complete
          </button>
        </>
      )}
      {goal.description && <div className="text-sm text-gray-600">{goal.description}</div>}
      {goal.reward && <div className="text-sm text-yellow-600">Reward: {goal.reward} $STK</div>}
    </div>
  );
}