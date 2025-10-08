#!/usr/bin/env python3
"""
PAEV Test F6f+ — Page Curve (CSV + Annotation + Summary)
Adds:
  • CSV export of S_in, S_out, S_tot, E, A, flux
  • Auto-annotated Page time (argmax S_in)
  • JSON summary artifact
"""
import json, numpy as np, matplotlib.pyplot as plt, imageio.v2 as imageio
from datetime import datetime

# ----- helpers -----
def laplacian(Z): return (-4.0*Z + np.roll(Z,1,0)+np.roll(Z,-1,0)+np.roll(Z,1,1)+np.roll(Z,-1,1))
def grad2(Z):
    gx = 0.5*(np.roll(Z,-1,1)-np.roll(Z,1,1))
    gy = 0.5*(np.roll(Z,-1,0)-np.roll(Z,1,0))
    return gx*gx + gy*gy
def shannon_entropy(p):
    p = np.clip(p, 1e-16, 1.0); return float(-np.sum(p*np.log(p)))
def region_entropy_proxy(psi2, mask):
    w = psi2[mask]; Z = float(np.sum(w))+1e-16; return shannon_entropy((w/Z).ravel())

# ----- grid & init -----
N = 96
x = np.linspace(-1, 1, N); X, Y = np.meshgrid(x, x); R = np.sqrt(X**2 + Y**2)
rng = np.random.default_rng(7)
psi = 0.1*(rng.standard_normal((N,N)) + 1j*rng.standard_normal((N,N)))
psi_t = np.zeros_like(psi, dtype=complex)
r_h0 = 0.55
kappa = 0.6*np.exp(-((R/r_h0)**2)) + 0.01*rng.standard_normal((N,N))

# ----- dynamics params -----
dt, steps = 0.02, 700
c1, chi, gamma = 0.35, 0.10, 0.02
eta, alpha, flux_gain = 0.04, 0.015, 0.06
r_h = r_h0

def masks_from_radius(r): 
    inside = R <= r; return inside, ~inside

inside_mask, outside_mask = masks_from_radius(r_h)

# ----- traces -----
S_in, S_out, S_tot, E_tr, A_tr, Flux = [], [], [], [], [], []
frames = []

# ----- simulate -----
for t in range(steps):
    # ψ update (curvature-coupled wave)
    lap_psi = laplacian(psi.real) + 1j*laplacian(psi.imag)
    # div(κ∇ψ) approx
    gx_re = 0.5*(np.roll(psi.real,-1,1)-np.roll(psi.real,1,1)); gy_re = 0.5*(np.roll(psi.real,-1,0)-np.roll(psi.real,1,0))
    gx_im = 0.5*(np.roll(psi.imag,-1,1)-np.roll(psi.imag,1,1)); gy_im = 0.5*(np.roll(psi.imag,-1,0)-np.roll(psi.imag,1,0))
    div_k_grad = 0.5*(np.roll(kappa*gx_re,-1,1)-np.roll(kappa*gx_re,1,1)) + 0.5*(np.roll(kappa*gy_re,-1,0)-np.roll(kappa*gy_re,1,0)) \
               + 1j*(0.5*(np.roll(kappa*gx_im,-1,1)-np.roll(kappa*gx_im,1,1)) + 0.5*(np.roll(kappa*gy_im,-1,0)-np.roll(kappa*gy_im,1,0)))
    psi_tt = c1*lap_psi + chi*div_k_grad - gamma*psi_t
    psi_t  = psi_t + dt*psi_tt
    psi    = psi   + dt*psi_t

    # κ update + evaporation
    shell = np.logical_and(R > (r_h*0.95), R < (r_h*1.05))
    grad_energy = float(np.mean(grad2(psi.real)[shell] + grad2(psi.imag)[shell])) if np.any(shell) else 0.0
    evap = alpha + flux_gain*grad_energy
    kappa = kappa + dt*(eta*laplacian(kappa) - evap*kappa)

    # horizon shrink
    r_h = max(0.12, r_h - 0.025*dt*(1.0 + 40.0*grad_energy))
    inside_mask, outside_mask = masks_from_radius(r_h)

    # observables
    psi2 = (psi.real**2 + psi.imag**2)
    E = float(np.mean(np.abs(psi_t)**2 + 0.5*grad2(psi.real) + 0.5*grad2(psi.imag) + 0.01*kappa**2))
    A = int(np.sum(inside_mask))
    Z = float(np.sum(psi2)) + 1e-12
    S_in.append(region_entropy_proxy(psi2, inside_mask))
    S_out.append(region_entropy_proxy(psi2, outside_mask))
    S_tot.append(shannon_entropy((psi2/Z).ravel()))
    E_tr.append(E); A_tr.append(A); Flux.append(grad_energy)

    # visuals
    if t % 12 == 0:
        def norm_img(Z):
            zmin, zmax = float(np.nanpercentile(Z,1)), float(np.nanpercentile(Z,99))
            Zc = np.clip((Z - zmin)/max(zmax-zmin,1e-9), 0, 1)
            return np.uint8(plt.cm.magma(Zc)*255)
        tile = np.concatenate([
            np.concatenate([norm_img(psi.real), norm_img(psi.imag)], axis=1),
            np.concatenate([norm_img(kappa), norm_img(psi2)], axis=1)
        ], axis=0)
        frames.append(tile)

# ----- analytics -----
S_in = np.array(S_in); S_out=np.array(S_out); S_tot=np.array(S_tot)
E_tr=np.array(E_tr); A_tr=np.array(A_tr); Flux=np.array(Flux)
page_step = int(np.argmax(S_in))
page_time = page_step*dt

# ----- plots -----
plt.figure(figsize=(7.4,4.6))
plt.plot(S_in,  label="S_inside (Page)")
plt.plot(S_out, label="S_outside")
plt.plot(S_tot, label="S_total", alpha=0.7)
plt.axvline(page_step, ls="--", color="k", alpha=0.6)
plt.text(page_step+5, np.max(S_in)*0.9, f"Page time ≈ {page_time:.2f}", fontsize=9)
plt.xlabel("Step"); plt.ylabel("Entropy (proxy)")
plt.title("Test F6f — Page Curve (auto-annotated)")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_TestF6f_PageCurve_Annotated.png", dpi=160); plt.close()

plt.figure(figsize=(7.2,4.2))
plt.plot(np.gradient(S_in),  label="dS_inside/dt")
plt.plot(np.gradient(S_out), label="dS_outside/dt")
plt.plot(Flux,               label="Flux (shell proxy)", alpha=0.7)
plt.xlabel("Step"); plt.ylabel("Rate / Flux")
plt.title("F6f — Information Flux vs Evaporation")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_TestF6f_InfoFlux.png", dpi=160); plt.close()

plt.figure(figsize=(7.2,4.2))
plt.plot(E_tr, label="Energy ⟨E⟩")
plt.plot(A_tr, label="Area (pixels)")
plt.xlabel("Step"); plt.ylabel("Value")
plt.title("F6f — Energy & Horizon Area")
plt.legend(); plt.tight_layout()
plt.savefig("PAEV_TestF6f_EnergyArea.png", dpi=160); plt.close()

imageio.mimsave("PAEV_TestF6f_Propagation.gif", frames, fps=10)

# ----- CSV + JSON artifacts -----
import csv
with open("PAEV_TestF6f_PageCurve.csv","w",newline="") as f:
    w = csv.writer(f); w.writerow(["step","time","S_in","S_out","S_tot","Energy","Area","Flux"])
    for i in range(len(S_in)):
        w.writerow([i, i*dt, S_in[i], S_out[i], S_tot[i], E_tr[i], A_tr[i], Flux[i]])

summary = {
  "test": "F6f_PageCurve",
  "dt": dt, "steps": steps,
  "page_step": page_step, "page_time": page_time,
  "final": {"S_in": float(S_in[-1]), "S_out": float(S_out[-1]), "S_tot": float(S_tot[-1]),
            "Energy": float(E_tr[-1]), "Area": int(A_tr[-1])},
  "files": {
    "page_plot": "PAEV_TestF6f_PageCurve_Annotated.png",
    "infoflux_plot": "PAEV_TestF6f_InfoFlux.png",
    "energy_area_plot": "PAEV_TestF6f_EnergyArea.png",
    "animation": "PAEV_TestF6f_Propagation.gif",
    "csv": "PAEV_TestF6f_PageCurve.csv"
  },
  "timestamp": datetime.utcnow().isoformat(timespec="seconds")+"Z"
}
with open("backend/modules/knowledge/F6f_page_curve_summary.json","w") as f:
    json.dump(summary, f, indent=2)

print("=== F6f+ — Complete ===")
print(f"Page time @ step {page_step} (~{page_time:.2f})")
print("Artifacts:")
for k,v in summary["files"].items(): print(f"  - {k}: {v}")