import * as React from "react";

type Goal = { id: string; text: string; done: boolean };

export default function SciGoalPanel() {
  const [goals, setGoals] = React.useState<Goal[]>(() => {
    try { return JSON.parse(localStorage.getItem("sqs.goals.v1") || "[]"); } catch { return []; }
  });
  const [text, setText] = React.useState("");

  React.useEffect(() => {
    localStorage.setItem("sqs.goals.v1", JSON.stringify(goals));
  }, [goals]);

  const add = () => {
    if (!text.trim()) return;
    setGoals(g => [...g, { id: Math.random().toString(36).slice(2), text: text.trim(), done: false }]);
    setText("");
  };

  const toggle = (id: string) => setGoals(g => g.map(x => x.id === id ? { ...x, done: !x.done } : x));
  const remove = (id: string) => setGoals(g => g.filter(x => x.id !== id));

  return (
    <div className="p-3 text-sm">
      <div className="flex gap-2 mb-3">
        <input
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Add goal…"
          className="flex-1 px-2 py-1 rounded border border-neutral-700 bg-neutral-900"
        />
        <button className="px-2 py-1 rounded border border-neutral-700" onClick={add}>Add</button>
      </div>
      <ul className="space-y-1">
        {goals.map(g => (
          <li key={g.id} className="flex items-center gap-2">
            <input type="checkbox" checked={g.done} onChange={() => toggle(g.id)} />
            <span className={g.done ? "line-through text-zinc-500" : ""}>{g.text}</span>
            <button className="ml-auto text-zinc-400 hover:text-zinc-200" onClick={() => remove(g.id)}>×</button>
          </li>
        ))}
      </ul>
    </div>
  );
}