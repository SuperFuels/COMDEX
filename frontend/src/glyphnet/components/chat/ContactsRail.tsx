import React from "react";

type KG = "personal" | "work";

type Contact = {
  id: string;
  name: string;
  wa: string;           // ucs://... topic (shared container identity / DM topic)
  tag: KG | string;     // “personal” / “work” etc.
  initials?: string;
};

const CONTACTS: Contact[] = [
  {
    id: "dave",
    name: "Dave Ross",
    wa: "ucs://wave.tp/dave@personal",
    tag: "personal",
    initials: "DR",
  },
  {
    id: "alice",
    name: "Alice Nguyen",
    wa: "ucs://wave.tp/alice@work",
    tag: "work",
    initials: "AN",
  },
  {
    id: "nia",
    name: "Nia Patel",
    wa: "ucs://wave.tp/nia@personal",
    tag: "personal",
    initials: "NP",
  },
];

// Open the chat route for a given contact/topic.
// Example hash: #/chat?topic=ucs%3A%2F%2Fwave.tp%2Fdave%40personal&kg=personal
function openChat(topic: string, kg?: KG) {
  const next =
    `#/chat?topic=${encodeURIComponent(topic)}` + (kg ? `&kg=${kg}` : "");
  window.location.hash = next;
}

// Helper: tidy ellipsis
const ellipsis: React.CSSProperties = {
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

export default function ContactsRail({ selectedTopic }: { selectedTopic?: string }) {
  return (
    <aside
      style={{
        height: "100%",
        overflow: "auto",
        borderRight: "1px solid #e5e7eb",
        background: "#fff",
      }}
    >
      {/* Tabs (static for now) */}
      <div style={{ display: "flex", gap: 12, padding: "10px 12px" }}>
        <button style={tabActive}>Personal</button>
        <button style={tab}>Work</button>
      </div>

      {/* Search (non-functional stub for now, cleans the look) */}
      <div style={{ padding: "0 12px 8px" }}>
        <input
          placeholder="Search contacts…"
          spellCheck={false}
          style={{
            width: "100%",
            padding: "8px 10px",
            borderRadius: 10,
            border: "1px solid #e5e7eb",
            outline: "none",
          }}
        />
      </div>

      <div style={{ padding: "8px 12px", color: "#6b7280", fontWeight: 700 }}>
        Contacts
      </div>

      <div style={{ padding: "0 8px 12px" }}>
        {CONTACTS.map((c) => {
          const isActive =
            selectedTopic &&
            selectedTopic.toLowerCase() === c.wa.toLowerCase();

          return (
            <button
              key={c.id}
              onClick={() => openChat(c.wa, c.tag as KG)}
              title={c.wa}
              style={{
                width: "100%",
                textAlign: "left",
                padding: 12,
                borderRadius: 12,
                border: "1px solid #e5e7eb",
                background: isActive ? "#f1f5f9" : "#fff",
                boxShadow: isActive ? "inset 0 0 0 2px #11182711" : "none",
                display: "flex",
                alignItems: "center",
                gap: 12,
                cursor: "pointer",
                marginBottom: 10,
              }}
            >
              {/* Avatar */}
              <div
                aria-hidden
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 999,
                  display: "grid",
                  placeItems: "center",
                  fontWeight: 800,
                  border: "1px solid #e5e7eb",
                  background: "#f8fafc",
                  color: "#111827",
                  flex: "0 0 auto",
                }}
              >
                {c.initials || c.name[0].toUpperCase()}
              </div>

              {/* Text */}
              <div style={{ minWidth: 0 }}>
                <div style={{ ...ellipsis, fontWeight: 700, color: "#111827" }}>
                  {c.name}
                </div>
                <div
                  style={{
                    ...ellipsis,
                    fontSize: 12,
                    color: "#6b7280",
                    marginTop: 2,
                  }}
                >
                  {String(c.tag).toLowerCase()}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

const tab: React.CSSProperties = {
  borderRadius: 999,
  padding: "6px 10px",
  border: "1px solid #e5e7eb",
  background: "#fff",
  cursor: "pointer",
  fontWeight: 700,
  color: "#111827",
};

const tabActive: React.CSSProperties = {
  ...tab,
  background: "#111827",
  color: "#fff",
};