// Glyph_Net_Browser/src/components/PhotonStubPanel.tsx
import React from "react";

type PhotonStubPanelProps = {
  code: string;
};

export function PhotonStubPanel({ code }: PhotonStubPanelProps) {
  if (!code) return null;

  function handleSendToEditor() {
    if (typeof window === "undefined") return;

    const stub = {
      docId: "devtools",          // matches <PhotonEditor docId="devtools" />
      source: code,               // the stub text
      name: "crystal motif stub", // label in the editor name box (optional)
      language: "photon",
    };

    // 🔹 store it so PhotonEditor can hydrate on mount
    (window as any).__DEVTOOLS_LAST_PHOTON_STUB = stub;

    // 🔹 switch to the Text Editor tab
    window.dispatchEvent(
      new CustomEvent("devtools.switch_tab", {
        detail: { tool: "editor" },
      }),
    );

    // 🔹 also broadcast the event (in case the editor is already mounted)
    window.dispatchEvent(
      new CustomEvent("devtools.photon_open", {
        detail: stub,
      }),
    );
  }

  function handleCopy() {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(code).catch(() => {});
    }
  }

  return (
    <div
      style={{
        borderRadius: 10,
        border: "1px solid #020617",
        background: "#020617",
        color: "#e5e7eb",
        padding: 8,
        fontSize: 11,
        fontFamily:
          'SFMono-Regular, ui-monospace, Menlo, Monaco, Consolas, "Courier New", monospace',
      }}
    >
      <div
        style={{
          marginBottom: 4,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontWeight: 600 }}>Photon motif stub</span>

        <div style={{ display: "flex", gap: 6 }}>
          <button
            type="button"
            onClick={handleSendToEditor}
            style={{
              padding: "3px 10px",
              borderRadius: 999,
              border: "1px solid #22c55e",
              background: "#16a34a",
              color: "#ecfdf5",
              fontSize: 11,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            ⤏ Send to Text Editor
          </button>

          <button
            type="button"
            onClick={handleCopy}
            style={{
              padding: "3px 8px",
              borderRadius: 999,
              border: "1px solid #4b5563",
              background: "#020617",
              color: "#e5e7eb",
              fontSize: 11,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            Copy
          </button>
        </div>
      </div>

      <pre
        style={{
          margin: 0,
          padding: 8,
          borderRadius: 6,
          background: "#020617",
          border: "1px solid #111827",
          overflow: "auto",
          maxHeight: 260,
          whiteSpace: "pre",
        }}
      >
        {code}
      </pre>
    </div>
  );
}