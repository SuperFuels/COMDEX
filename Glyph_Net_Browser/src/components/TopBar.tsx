// src/components/TopBar.tsx
import WormholeBar from "./WormholeBar";

type Props = {
  onNavigate: (t: { mode: "wormhole" | "http"; address: string }) => void;
  onOpenSidebar: () => void;
  onAskAion: () => void;
  onConnectWallet: () => void;
  onToggleWaves: () => void;
  wavesCount: number;
};

export default function TopBar(p: Props) {
  return (
    <header
      style={{
        height: 56,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 12px",
        borderBottom: "1px solid #e5e7eb",
        background: "#fff",
        position: "sticky",
        top: 0,
        zIndex: 38,
      }}
    >
      {/* subtle hamburger (only opens; closing handled by overlay) */}
      <button
        onClick={p.onOpenSidebar}
        aria-label="Open sidebar"
        title="Open sidebar"
        style={navBtn}
      >
        ☰
      </button>

      {/* back / fwd / reload */}
      <button title="Back" style={navBtn} onClick={() => history.back()}>
        ◀
      </button>
      <button title="Forward" style={navBtn} onClick={() => history.forward()}>
        ▶
      </button>
      <button title="Reload" style={navBtn} onClick={() => location.reload()}>
        ⟳
      </button>

      {/* address bar */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <WormholeBar onNavigate={p.onNavigate} />
      </div>

      {/* right actions */}
      <button style={pill} onClick={p.onAskAion}>🫖 Ask AION</button>
      <button style={pill} onClick={p.onConnectWallet}>🔑 Connect</button>
      <button style={pill} onClick={p.onToggleWaves}>
        🌊 Waves {p.wavesCount ? `(${p.wavesCount})` : ""}
      </button>
    </header>
  );
}

const navBtn: React.CSSProperties = {
  width: 34,
  height: 34,
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  background: "#fff",
};

const pill: React.CSSProperties = {
  borderRadius: 12,
  padding: "6px 10px",
  border: "1px solid #e5e7eb",
  background: "#fff",
};