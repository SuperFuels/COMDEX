# ──────────────────────────────────────────────────────────────
# Tessaris Symatics – Figure Generator (Volume VII)
# Generates publication figures:
#   1. resonant_feedback_loop.png
#   2. resonant_gradient_flow.png
# Author: Tessaris Core Systems / Codex Intelligence Group
# Version: October 2025
# ──────────────────────────────────────────────────────────────

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Circle

from backend.modules.codex.codex_render import telemetry_buffer
from backend.symatics.core.grad_operators import compute_gradients

# ──────────────────────────────────────────────────────────────
# Utility: ensure output directory
# ──────────────────────────────────────────────────────────────
os.makedirs("docs/figures", exist_ok=True)


# ──────────────────────────────────────────────────────────────
# FIGURE 1 — Resonant Continuity Feedback Loop
# λ → ψ → E → ℛ → λ schematic
# ──────────────────────────────────────────────────────────────
def draw_feedback_loop():
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Node positions
    nodes = {
        "lambda": (1, 3),
        "psi": (4, 3),
        "E": (7, 3),
        "R": (4, 1),
    }

    # Draw nodes
    style = dict(fc="#EAD1DC", ec="#C27BA0", lw=1.5)
    for name, (x, y) in nodes.items():
        circ = Circle((x, y), 0.6, **style)
        ax.add_patch(circ)
        label = {"lambda": r"$\lambda(t)$",
                 "psi": r"$\psi(t)$",
                 "E": r"$E(t)$",
                 "R": r"$\mathcal{R}(\psi,t)$"}[name]
        ax.text(x, y, label, ha="center", va="center", fontsize=12, color="#4A4A4A")

    # Arrows
    arrows = [
        ("lambda", "psi", "modulates"),
        ("psi", "E", "drives"),
        ("E", "R", ""),
        ("R", "lambda", "∇ψℛ feedback")
    ]

    def add_arrow(a, b, label=None, bend=0.0, color="#4F90C2"):
        x1, y1 = nodes[a]
        x2, y2 = nodes[b]
        arrow = FancyArrowPatch(
            (x1+0.6, y1),
            (x2-0.6, y2),
            connectionstyle=f"arc3,rad={bend}",
            arrowstyle="-|>",
            color=color,
            mutation_scale=12,
            lw=1.5,
        )
        ax.add_patch(arrow)
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2+0.3, label, color="#4A4A4A",
                    ha="center", va="bottom", fontsize=9)

    for a, b, lbl in arrows:
        add_arrow(a, b, lbl)

    ax.text(5, 5.3, "Resonant Continuity Feedback Loop", fontsize=13,
            color="#4A4A4A", ha="center")
    out1 = "docs/figures/resonant_feedback_loop.png"
    plt.tight_layout()
    plt.savefig(out1, dpi=200)
    print(f"✅ Saved {out1}")


# ──────────────────────────────────────────────────────────────
# FIGURE 2 — λ–E–∇ψℛ Gradient Flow Plot
# Derived from telemetry buffer + computed gradients
# ──────────────────────────────────────────────────────────────
def plot_gradient_flow():
    events = telemetry_buffer.snapshot()
    events.sort(key=lambda e: e["timestamp"])

    λ = [e.get("new_weight") for e in events if e["event_type"] in ("law_weight_update", "resonant_law_update")]
    E = [e.get("value") for e in events if e["event_type"] == "wave_energy"]
    C = [e.get("value") for e in events if e["event_type"] == "coherence_index"]
    t = np.arange(min(len(λ), len(E)))

    if not λ or not E:
        print("⚠️  No telemetry data found — run a simulation first.")
        return

    plt.figure(figsize=(8, 5))
    plt.plot(t[:len(λ)], λ[:len(t)], label=r"$\lambda(t)$", color="tab:blue")
    plt.plot(t[:len(E)], E[:len(t)], label=r"$E(t)$", color="tab:green")

    # Compute gradients using GradOperators
    if len(E) > 1:
        grads = [
            compute_gradients({"energy": E[i], "phase": 0.1*i},
                              {"energy": E[i+1], "phase": 0.1*(i+1)})
            for i in range(len(E)-1)
        ]
        gmag = [abs(g["grad_energy"]) for g in grads]
        plt.plot(t[:len(gmag)], gmag, label=r"$\nabla_\psi\mathcal{R}$", color="tab:purple", alpha=0.7)

    plt.title("Resonant Gradient Flow — λ, E, ∇ψℛ")
    plt.xlabel("Time index (t)")
    plt.ylabel("Magnitude")
    plt.legend()
    plt.grid(True, alpha=0.3)

    out2 = "docs/figures/resonant_gradient_flow.png"
    plt.tight_layout()
    plt.savefig(out2, dpi=200)
    print(f"✅ Saved {out2}")


# ──────────────────────────────────────────────────────────────
# Main execution
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    draw_feedback_loop()
    plot_gradient_flow()
    print("🎨 Figure generation complete for Volume VII.")