# backend/photon_algebra/tests/paev_test3_pi_sweep.py
import numpy as np, matplotlib.pyplot as plt
from backend.photon_algebra.utils.visibility import project_with_pi, compute_visibility

def generate_double_slit_frames(T=100, H=256, W=256, phase_shift=0.0):
    x = np.linspace(-np.pi, np.pi, W)
    slit1 = np.sin(5*x)
    slit2 = np.sin(5*x + phase_shift)
    pattern = (slit1 + slit2)**2
    frames = np.tile(pattern, (T, H, 1))
    frames += np.random.normal(0, 0.02, frames.shape)
    return frames

def run():
    stack = generate_double_slit_frames()
    pi_spatial_values = [1,2,4,8,16]
    visibilities = []
    for pi_s in pi_spatial_values:
        proj = project_with_pi(stack, pi_spatial=pi_s)
        V = compute_visibility(proj.mean(axis=0))
        visibilities.append(V)
        print(f"π_spatial={pi_s} → V={V:.3f}")
    plt.plot(pi_spatial_values, visibilities, marker='o')
    plt.xlabel("π_spatial (bin width)"); plt.ylabel("Visibility V")
    plt.title("Symatics π-sweep: V vs projection bandwidth")
    plt.savefig("docs/theory/figures/PAEV_Test3_PiSweep.png", dpi=300)
    np.savetxt("docs/theory/tables/PAEV_Test3_PiSweep.csv",
               np.column_stack([pi_spatial_values, visibilities]),
               header="pi_spatial,V", delimiter=",", fmt="%.6f")
if __name__ == "__main__":
    run()