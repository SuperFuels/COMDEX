"use client";

import type { BoardroomModel, BoardroomSeat } from "./boardroom.types";

export default function BoardroomHudPanel({
  model,
  selectedSeat,
  onSelectSeat,
}: {
  model: BoardroomModel;
  selectedSeat: BoardroomSeat | null;
  onSelectSeat: (seat: BoardroomSeat) => void;
}) {
  return (
    <div
      style={{
        borderRadius: 16,
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div>
        <div style={{ fontSize: 12, color: "#6b7280" }}>Boardroom</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}>{model.label}</div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, minmax(0,1fr))",
          gap: 10,
        }}
      >
        {[
          ["Revenue", model.center.revenue],
          ["Cash", model.center.cash],
          ["Pipeline", model.center.pipeline],
          ["Profit", model.center.profit],
          ["Health", model.center.health],
        ].map(([label, value]) => (
          <div
            key={label}
            style={{
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              padding: "10px 12px",
            }}
          >
            <div style={{ fontSize: 12, color: "#6b7280" }}>{label}</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#111827", marginTop: 4 }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      <div>
        <div style={{ fontSize: 12, fontWeight: 700, color: "#111827", marginBottom: 8 }}>
          Seats
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: 10 }}>
          {model.seats.map((seat) => {
            const active = selectedSeat?.id === seat.id;
            return (
              <button
                key={seat.id}
                type="button"
                onClick={() => onSelectSeat(seat)}
                style={{
                  textAlign: "left",
                  borderRadius: 14,
                  border: active ? "1px solid #0f172a" : "1px solid #e5e7eb",
                  background: active ? "#eff6ff" : "#ffffff",
                  padding: "12px 14px",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontSize: 14, fontWeight: 700, color: "#111827" }}>{seat.label}</div>
                <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
                  {seat.owner ?? "Unassigned"}
                </div>
                <div style={{ fontSize: 12, color: "#4b5563", marginTop: 8 }}>
                  Open {seat.tasks?.open ?? 0} · Blocked {seat.tasks?.blocked ?? 0}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}