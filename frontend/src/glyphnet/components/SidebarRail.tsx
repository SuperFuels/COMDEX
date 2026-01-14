import { ReactNode } from "react";

type Item = {
  id: string;
  icon: ReactNode;
  label: string;
  onClick?: () => void;
};

type Props = {
  items: Item[];
  activeId?: string;
};

export function SidebarRail({ items, activeId }: Props) {
  return (
    <nav
      style={{
        width: 56,
        background: "#f9fafb",
        borderRight: "1px solid #e5e7eb",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: 8,
        gap: 8,
      }}
    >
      {items.map((item) => {
        const active = item.id === activeId;
        return (
          <button
            key={item.id}
            type="button"
            onClick={item.onClick}
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              border: "none",
              background: active ? "#0f172a" : "#ffffff",
              boxShadow: active
                ? "0 0 0 1px #0ea5e9"
                : "0 0 0 1px rgba(148,163,184,0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              position: "relative",
            }}
            title={item.label}
          >
            <span
              style={{
                fontSize: 20,
                filter: active ? "none" : "grayscale(0.1)",
              }}
            >
              {item.icon}
            </span>
          </button>
        );
      })}
    </nav>
  );
}