import { useEffect } from "react";

type Props = {
  open: boolean;
  active:
    | "home"
    | "chat"
    | "inbox"
    | "outbox"
    | "kg"
    | "devtools"
    | "settings";
  onSelect: (id: Props["active"]) => void;
  onClose: () => void;
};

export default function Sidebar({ open, active, onSelect, onClose }: Props) {
  // close on ESC
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const Item = ({
    id,
    label,
    emoji,
  }: {
    id: Props["active"];
    label: string;
    emoji: string;
  }) => (
    <button
      onClick={() => {
        onSelect(id);
        onClose();
      }}
      aria-label={label}
      aria-current={active === id ? "page" : undefined}
      title={label}
      style={{
        width: 48,
        height: 48,
        borderRadius: 12,
        border: "1px solid #e5e7eb",
        background: active === id ? "#eef2ff" : "#fff",
        cursor: "pointer",
        fontSize: 20,
      }}
    >
      {emoji}
    </button>
  );

  return (
    <>
      {/* Scrim */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,.12)",
          opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none",
          transition: "opacity .2s ease",
          zIndex: 39,
        }}
      />

      {/* Drawer */}
      <aside
        role="navigation"
        aria-label="Sidebar"
        style={{
          position: "fixed",
          top: 56, // height of TopBar
          left: 0,
          bottom: 0,
          width: 72,
          padding: 12,
          background: "#fff",
          borderRight: "1px solid #e5e7eb",
          transform: open ? "translateX(0)" : "translateX(-100%)",
          transition: "transform .22s cubic-bezier(.2,.8,.2,1)",
          zIndex: 40,
          display: "flex",
          gap: 10,
          alignItems: "center",
          flexDirection: "column",
        }}
      >
        <Item id="home" label="Home" emoji="🏠" />
        <Item id="chat" label="Chat" emoji="💬" />
        <Item id="inbox" label="Wave Inbox" emoji="📥" />
        <Item id="outbox" label="Wave Outbox" emoji="📤" />
        <Item id="kg" label="Knowledge Graph" emoji="🧠" />
        <Item id="devtools" label="Dev Tools" emoji="🛠️" />
        <Item id="settings" label="Settings" emoji="⚙️" />
      </aside>
    </>
  );
}