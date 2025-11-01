# backend/photon_algebra/tests/sim_mzi_photon_algebra.py
import numpy as np
import cmath
import matplotlib.pyplot as plt
from math import cos, sin
from backend.photon_algebra.rewriter import normalize

# ==========================================================
#  Quantum Mach-Zehnder Interferometer model
# ==========================================================
H_bs = (1/np.sqrt(2)) * np.array([[1, 1],
                                  [1,-1]], dtype=complex)  # 50/50 beamsplitter
I2  = np.eye(2, dtype=complex)

def phase(phi):
    """Phase on |U> arm only."""
    return np.array([[np.exp(1j*phi), 0],
                     [0, 1]], dtype=complex)

def which_path_marker(on=True):
    """Marks which-path by flipping polarization on upper arm."""
    X = np.array([[0,1],[1,0]], dtype=complex)
    PU = np.array([[1,0],[0,0]], dtype=complex)
    PL = np.array([[0,0],[0,1]], dtype=complex)
    if not on:
        return np.kron(I2, I2)
    return np.kron(PU, X) + np.kron(PL, I2)

def eraser(theta):
    """Polarizer at angle θ projecting onto |Hθ> = cosθ|H> + sinθ|V>."""
    ket = np.array([[cos(theta)], [sin(theta)]], dtype=complex)
    Pth = ket @ ket.conj().T
    return np.kron(I2, Pth)

def mzi_output_probs(phi, marker_on=False, theta=None):
    """Return probabilities at D0, D1 after full MZI."""
    psi_in = np.kron(np.array([[1],[0]], dtype=complex),  # |U>
                     np.array([[1],[0]], dtype=complex))  # |H>

    U = np.kron(H_bs, I2)               # BS1
    U = np.kron(phase(phi), I2) @ U     # phase
    U = which_path_marker(marker_on) @ U
    U = np.kron(H_bs, I2) @ U           # BS2

    psi = U @ psi_in

    if theta is not None:
        E = eraser(theta)
        psi = E @ psi
        norm = np.linalg.norm(psi)
        if norm > 1e-12:
            psi = psi / norm

    psi_mat = psi.reshape(2, 2)
    rho_path = psi_mat @ psi_mat.conj().T
    pU = np.real(rho_path[0,0])
    pL = np.real(rho_path[1,1])
    return float(pU), float(pL)


# ==========================================================
#  Quantitative Photon Algebra mapping
# ==========================================================
def photon_algebra_intensity(phi, marker_on=False, theta=None):
    """
    Quantitative version of photon algebra prediction.
    Returns (I0, I1) from phase logic.
    """
    # Path amplitudes: |U>, |L>
    amps = [cmath.exp(1j * 0.0), cmath.exp(1j * phi)]

    # Phase π -> complement (sign flip)
    if abs((phi % (2*np.pi)) - np.pi) < 1e-6:
        amps[0] *= -1

    # Default coherent interference
    A_sum = sum(amps) / np.sqrt(2)
    I0 = abs(A_sum)**2
    I1 = 1 - I0

    # Marker destroys interference
    if marker_on:
        I0 = 0.5
        I1 = 0.5

        # Eraser at θ≈π/2 restores coherence
        if theta is not None and abs(theta - np.pi/2) < 1e-6:
            A_sum = sum(amps) / np.sqrt(2)
            I0 = abs(A_sum)**2
            I1 = 1 - I0

    return float(I0), float(I1)


# ==========================================================
#  Simulation sweep + comparison plot
# ==========================================================
if __name__ == "__main__":
    phis = np.linspace(0, 2*np.pi, 300)

    # Quantum models
    q_no_marker = [mzi_output_probs(phi, marker_on=False)[0] for phi in phis]
    q_marker_on = [mzi_output_probs(phi, marker_on=True)[0] for phi in phis]
    q_marker_erase = [mzi_output_probs(phi, marker_on=True, theta=np.pi/2)[0] for phi in phis]

    # Photon Algebra models
    pa_no_marker = [photon_algebra_intensity(phi, marker_on=False)[0] for phi in phis]
    pa_marker_on = [photon_algebra_intensity(phi, marker_on=True)[0] for phi in phis]
    pa_marker_erase = [photon_algebra_intensity(phi, marker_on=True, theta=np.pi/2)[0] for phi in phis]

    plt.figure(figsize=(8,5))
    plt.plot(phis, q_no_marker, "b-", label="No marker (Quantum)")
    plt.plot(phis, pa_no_marker, "b--", label="No marker (PhotonAlg)")
    plt.plot(phis, q_marker_on, "r-", label="Marker ON (Quantum)")
    plt.plot(phis, pa_marker_on, "r--", label="Marker ON (PhotonAlg)")
    plt.plot(phis, q_marker_erase, "g-", label="Marker+Eraser (Quantum)")
    plt.plot(phis, pa_marker_erase, "g--", label="Marker+Eraser (PhotonAlg)")

    plt.title("Mach-Zehnder Interferometer - Quantum vs Photon Algebra")
    plt.xlabel("Phase φ (radians)")
    plt.ylabel("Detector D0 Intensity")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    outfile = "mzi_photon_vs_quantum2.png"
    plt.savefig(outfile, dpi=150)
    print(f"✅ Saved output plot to: {outfile}")