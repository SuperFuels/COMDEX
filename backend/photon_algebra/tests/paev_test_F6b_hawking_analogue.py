import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# === Parameters ===
N = 128
steps = 600
dt = 0.01
chi = 0.15          # coupling
damping = 0.001     # radiation leakage
curv_thresh = 0.3   # defines "horizon"
radiation_rate = 0.0005

# === Field Initialization ===
x = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, x)
kappa = 0.9 * np.exp(-(X**2 + Y**2)/0.05)  # curvature spike (black hole)
psi = np.exp(-((X+0.3)**2 + Y**2)/0.2)     # radiation field
psi_t = np.zeros_like(psi)

E_trace, S_trace, A_trace, Flux_trace = [], [], [], []

def laplacian(Z):
    return -4*Z + np.roll(Z,1,0)+np.roll(Z,-1,0)+np.roll(Z,1,1)+np.roll(Z,-1,1)

def spectral_entropy(field):
    f = np.abs(np.fft.fft2(field))**2
    p = f / np.sum(f)
    p = p[p>0]
    return -np.sum(p*np.log(p)) / np.log(len(p))

# === Simulation ===
for step in range(steps):
    lap_k = laplacian(kappa)
    lap_psi = laplacian(psi)

    # Evolve curvature (black hole core)
    kappa_t = chi * lap_k - damping * kappa
    kappa += dt * kappa_t

    # Radiative field evolution (ψ leaks out)
    psi_tt = lap_psi - chi * kappa * psi
    psi_t += dt * psi_tt
    psi += dt * psi_t

    # Apply radiation leakage at outer boundary
    psi[0,:] *= (1 - radiation_rate)
    psi[-1,:] *= (1 - radiation_rate)
    psi[:,0] *= (1 - radiation_rate)
    psi[:,-1] *= (1 - radiation_rate)

    # Compute metrics
    E = np.mean(psi_t**2 + psi**2)
    S = spectral_entropy(psi)
    A = np.sum(np.abs(kappa) > curv_thresh)
    Flux = radiation_rate * np.sum(np.abs(psi[-2,:]) + np.abs(psi[:, -2]))

    E_trace.append(E)
    S_trace.append(S)
    A_trace.append(A)
    Flux_trace.append(Flux)

    if step % 100 == 0:
        print(f"Step {step:03d} - E={E:.4e}, A={A}, Flux={Flux:.3e}, S={S:.3f}")

# === Derived relations ===
A_arr = np.array(A_trace)
Flux_arr = np.array(Flux_trace)
E_arr = np.array(E_trace)
S_arr = np.array(S_trace)
T_proxy = 1.0 / np.sqrt(A_arr + 1e-8)

# === Plots ===
plt.figure()
plt.plot(A_arr, Flux_arr, 'o-', color='crimson')
plt.title("Radiative Flux vs Area (Hawking Analogue)")
plt.xlabel("Horizon Area A")
plt.ylabel("Flux Φ_out")
plt.savefig("PAEV_TestF6b_HawkingFlux_vs_Area.png")

plt.figure()
plt.plot(E_arr, label="Energy")
plt.plot(S_arr, label="Entropy")
plt.title("Energy and Entropy Decay (Hawking Evaporation)")
plt.legend()
plt.savefig("PAEV_TestF6b_EnergyEntropy.png")

plt.figure()
plt.plot(A_arr, label="Horizon Area")
plt.plot(T_proxy, label="Temperature Proxy (1/√A)")
plt.legend()
plt.title("Horizon Shrinkage and Hawking Temperature")
plt.savefig("PAEV_TestF6b_HorizonShrinkage.png")

# === Summary Output ===
print("\n=== Test F6b - Hawking Radiation Analogue Complete ===")
print(f"⟨E⟩ final  = {E_arr[-1]:.6e}")
print(f"⟨S⟩ final  = {S_arr[-1]:.6e}")
print(f"⟨A⟩ final  = {A_arr[-1]:.6e}")
print(f"Mean Flux  = {np.mean(Flux_arr[-50:]):.6e}")
print(f"T_H proxy  = {np.mean(T_proxy[-50:]):.6e}")
print("\nAll output files saved in working directory.")
print("----------------------------------------------------------")