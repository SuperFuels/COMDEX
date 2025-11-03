// /Glyph_Net_Browser/src/App.tsx
import WormholeBar from "./components/WormholeBar";

export default function App() {
  const onNavigate = (t: { mode: "wormhole" | "http"; address: string }) => {
    if (t.mode === "http") {
      window.location.href = t.address; // legacy web
    } else {
      alert(`Teleport to ${t.address} (router stub)`); // placeholder
    }
  };

  return (
    <div style={{ padding: 16, fontFamily: "ui-sans-serif, system-ui" }}>
      <h1>Glyph_Net_Browser — Alpha Shell</h1>
      <p>
        Home: your personal container (AION entry). Try <code>nike</code> or{" "}
        <code>www.wikipedia.org</code>.
      </p>
      <WormholeBar onNavigate={onNavigate} />
      <div
        style={{
          marginTop: 12,
          padding: 12,
          border: "1px solid #ddd",
          borderRadius: 8,
        }}
      >
        <strong>AION:</strong> ready (UI stub). This pane becomes the agent
        console / GlyphGrid.
      </div>
    </div>
  );
}