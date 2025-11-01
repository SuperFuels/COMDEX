import matplotlib.pyplot as plt
from pathlib import Path

def render_awareness_plot(phi: float, res: float, stab: float, gain: float, save_path: str = "data/visualizations/awareness_live.png"):
    """Render a simple Φ-R-S snapshot to a PNG."""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(4,3))
    plt.title("GHX Awareness Snapshot")
    plt.bar(["Φ","R","S","g"], [phi, res, stab, gain])
    plt.ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    return save_path