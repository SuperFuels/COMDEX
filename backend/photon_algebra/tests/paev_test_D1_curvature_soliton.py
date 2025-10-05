import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ==============================================================
#  Test D1 — Curvature Soliton Localization (Self-Stabilizing Graviton Packet)
# ==============================================================
# Purpose:
#   Demonstrate formation of a self-trapped curvature soliton under nonlinear rewrite coupling.
#   Equation of motion (discrete form):
#       ∂²κ/∂t² = c²∇²κ − λκ³
#   The cubic term counteracts wave spreading.
# ==============================================================

def normalize(x):
    x = np.nan_to_num(x)
    return (x - x.min()) / (np.ptp(x) + 1e-12)

def laplacian(Z):
    return (
        np.roll(Z, 1, 0) + np.roll(Z, -1, 0) +
        np.roll(Z, 1, 1) + np.roll(Z, -1, 1) -
        4 * Z
    )

def main():
    print("=== Test D1 — Curvature Soliton Localization ===")

    # Parameters
    N = 121              # lattice size
    c = 1.0              # propagation speed
    lam = 0.002          # nonlinear self-coupling strength
    dt = 0.1
    steps = 400

    # Spatial grid
    x = np.linspace(-6, 6, N)
    y = np.linspace(-6, 6, N)
    X, Y = np.meshgrid(x, y)

    # Initial curvature bump (localized Gaussian)
    kappa = np.exp(-(X**2 + Y**2))
    v = np.zeros_like(kappa)  # velocity field

    energy = []

    # Prepare figure for animation
    fig, ax = plt.subplots(figsize=(5,5))
    im = ax.imshow(normalize(kappa), cmap="inferno", animated=True)
    ax.set_title("Test D1 — Curvature Soliton Evolution")

    frames = []

    for t in range(steps):
        # PDE integration step
        lap = laplacian(kappa)
        a = c**2 * lap - lam * kappa**3
        v += a * dt
        kappa += v * dt

        # Total energy (kinetic + potential + nonlinear)
        E = np.sum(0.5 * v**2 + 0.5 * c**2 * kappa * lap + 0.25 * lam * kappa**4)
        energy.append(E)

        if t % 5 == 0:
            frames.append([im])
            im.set_array(normalize(kappa))

    ani = FuncAnimation(fig, lambda i: frames[i], frames=len(frames), blit=True)
    ani.save("PAEV_TestD1_SolitonEvolution.gif", fps=10)
    plt.close(fig)

    # Plot total energy evolution
    plt.figure(figsize=(6,4))
    plt.plot(energy, color="blue")
    plt.title("Test D1 — Total Rewrite Energy (Soliton Stability)")
    plt.xlabel("Time step")
    plt.ylabel("Total energy (arb. units)")
    plt.tight_layout()
    plt.savefig("PAEV_TestD1_SolitonEnergy.png")

    print("✅ Saved animation to: PAEV_TestD1_SolitonEvolution.gif")
    print("✅ Saved energy plot to: PAEV_TestD1_SolitonEnergy.png")
    print(f"Energy mean={np.mean(energy):.4e}, std={np.std(energy):.4e}")
    print("=== Test D1 complete ===")

if __name__ == "__main__":
    main()