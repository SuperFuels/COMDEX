import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def normalize(x):
    """Normalize array between 0 and 1 safely."""
    x_min, x_max = np.min(x), np.max(x)
    return (x - x_min) / (x_max - x_min + 1e-12)

def curvature_evolution(kappa, alpha=0.1, beta=0.5, dt=0.1, steps=300):
    """Simple nonlinear curvature rewrite evolution."""
    E_total = []
    for i in range(steps):
        lap = (
            np.roll(kappa, 1, 0) + np.roll(kappa, -1, 0) +
            np.roll(kappa, 1, 1) + np.roll(kappa, -1, 1) - 4 * kappa
        )
        dk = alpha * lap - beta * kappa * (kappa**2 - 1)
        kappa += dt * dk
        E_total.append(np.sum(kappa**2))
    return kappa, np.array(E_total)

def main():
    print("=== Starting Test D3 — Soliton Fusion and Bound-State Formation ===")

    try:
        N = 121
        x = np.linspace(-3, 3, N)
        X, Y = np.meshgrid(x, x)

        # Two solitons slightly overlapping
        r1 = np.sqrt((X + 0.8)**2 + Y**2)
        r2 = np.sqrt((X - 0.8)**2 + Y**2)
        kappa0 = np.exp(-r1**2) + np.exp(-r2**2)
        kappa0 = normalize(kappa0)

        print("Initialized curvature field.")

        # === Animation setup ===
        kappa = kappa0.copy()
        dt, steps = 0.1, 400

        fig, ax = plt.subplots()
        im = ax.imshow(kappa, cmap="inferno", animated=True)
        ax.set_title("Test D3 — Soliton Fusion Dynamics")

        def update(frame):
            nonlocal kappa
            lap = (
                np.roll(kappa, 1, 0) + np.roll(kappa, -1, 0) +
                np.roll(kappa, 1, 1) + np.roll(kappa, -1, 1) - 4 * kappa
            )
            dk = 0.08 * lap - 0.4 * kappa * (kappa**2 - 1)
            kappa += dt * dk
            im.set_array(normalize(kappa))
            return [im]

        print("Beginning animation...")
        anim = FuncAnimation(fig, update, frames=steps, interval=50, blit=True)
        anim.save("PAEV_TestD3_SolitonFusion.gif", writer="pillow", fps=24)
        plt.close(fig)
        print("✅ Animation saved.")

        # === Compute energy evolution ===
        print("Computing energy evolution...")
        kappa_final, E_total = curvature_evolution(kappa0, alpha=0.08, beta=0.4, dt=dt, steps=steps)

        plt.figure()
        plt.plot(E_total, "b-")
        plt.title("Test D3 — Total Energy Evolution (Fusion Stability)")
        plt.xlabel("Time step")
        plt.ylabel("Total curvature energy (κ²)")
        plt.tight_layout()
        plt.savefig("PAEV_TestD3_SolitonFusion_Energy.png", dpi=180)
        plt.close()
        print("✅ Energy plot saved.")

        print("\n=== Test D3 — Soliton Fusion Results ===")
        print(f"Grid size: {N}x{N}, Steps: {steps}, dt={dt}")
        print(f"Initial energy = {E_total[0]:.4e}")
        print(f"Final energy   = {E_total[-1]:.4e}")
        print(f"ΔE             = {E_total[-1]-E_total[0]:.4e}")
        print("Files saved:\n - PAEV_TestD3_SolitonFusion.gif\n - PAEV_TestD3_SolitonFusion_Energy.png")

    except Exception as e:
        print("❌ Error during simulation:", e)

if __name__ == "__main__":
    main()