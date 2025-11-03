// src/components/KGDock.tsx
export default function KGDock() {
  const nodes = [
    { id: "n1", label: "Identity: kevin.tp" },
    { id: "n2", label: "Bond: partner.home" },
    { id: "n3", label: "Topic: glyphnet" },
  ];
  return (
    <div style={{ padding: 12 }}>
      <h3>Knowledge Graph</h3>
      <div style={{ display: "grid", gap: 8 }}>
        {nodes.map(n => (
          <div key={n.id} style={{ padding: 10, border: "1px solid #e5e7eb", borderRadius: 8 }}>
            {n.label}
          </div>
        ))}
      </div>
    </div>
  );
}