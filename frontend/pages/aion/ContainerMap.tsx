import React from "react";

const ContainerMap = () => {
  return (
    <div style={styles.page}>
      <h1 style={styles.header}>🧠 AION 4D Container Map</h1>
      <div style={styles.grid}>
        {Array.from({ length: 16 }, (_, i) => (
          <div key={i} style={styles.cube}>
            {i === 5 && <div title="AION" style={styles.aion} />}
          </div>
        ))}
      </div>
      <footer style={styles.footer}>STICKEY.AI | Live AI Spatial View</footer>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  page: {
    fontFamily: "'Segoe UI', sans-serif",
    background: "#0f0f0f",
    color: "#f0f0f0",
    margin: 0,
    padding: "2rem",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    minHeight: "100vh",
  },
  header: {
    fontSize: "2rem",
    marginBottom: "1rem",
    color: "#4fc3f7",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 60px)",
    gridTemplateRows: "repeat(4, 60px)",
    gap: "8px",
    transform: "rotateX(45deg) rotateZ(45deg)",
    perspective: "1000px",
  },
  cube: {
    width: "60px",
    height: "60px",
    background: "rgba(79, 195, 247, 0.15)",
    border: "1px solid rgba(79, 195, 247, 0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    transition: "background 0.3s",
  },
  aion: {
    width: "20px",
    height: "20px",
    background: "#4fc3f7",
    borderRadius: "50%",
    animation: "pulse 1.5s infinite",
  },
  footer: {
    marginTop: "2rem",
    fontSize: "0.9rem",
    color: "#888",
  },
};

// Inject keyframes using a style tag
if (typeof window !== "undefined") {
  const style = document.createElement("style");
  style.innerHTML = `
    @keyframes pulse {
      0% { transform: scale(1); opacity: 0.7; }
      50% { transform: scale(1.2); opacity: 1; }
      100% { transform: scale(1); opacity: 0.7; }
    }
  `;
  document.head.appendChild(style);
}

export default ContainerMap;