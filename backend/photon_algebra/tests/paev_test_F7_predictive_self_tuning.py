# ==========================================================
# Test F7 - Predictive Resonance & Self-Tuning Phase Dynamics
# ==========================================================
#
# Objective:
#   Extend the meta-adaptive resonance (F6) with a predictive layer.
#   The field estimates future entropy shifts and pre-emptively tunes
#   χ (coupling) and α (meta-rate) to maintain coherence.
#
#   This establishes a closed predictive feedback loop - the algebra
#   learns to stabilize itself in time.
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# ----------------------------
# basic lattice ops
# ----------------------------
def laplacian(Z):
    return -4 * Z + np.roll(Z,1,0) + np.roll(Z,-1,0) + np.roll(Z,1,1) + np.roll(Z,-1,1)

def grad_xy(Z):
    gx = 0.5*(np.roll(Z,-1,1)-np.roll(Z,1,1))
    gy = 0.5*(np.roll(Z,-1,0)-np.roll(Z,1,0))
    return gx, gy

def spectral_entropy(field):
    f2 = np.abs(np.fft.fftshift(np.fft.fft2(field)))**2
    p = f2/np.sum(f2)
    p = p[np.isfinite(p)]
    return -np.sum(p*np.log(p+1e-12))

# ----------------------------
# parameters
# ----------------------------
N = 64
steps = 320
dt = 0.02
x = np.linspace(-1,1,N)
X,Y = np.meshgrid(x,x)

rng = np.random.default_rng(7)
theta = np.exp(-(X**2+Y**2)/0.4)
theta_t = np.zeros_like(theta)
kappa = np.exp(-(X**2+Y**2)/0.5)
kappa += 0.03*rng.standard_normal((N,N))

# couplings
chi = 0.18
alpha = 0.05
gamma = 0.02

# predictive control params
predict_window = 6   # how many steps ahead to forecast
forecast_gain = 0.3  # how strongly prediction alters chi/alpha

# histories
energy_trace, corr_trace, entropy_trace = [], [], []
chi_trace, alpha_trace = [], []
forecast_error_trace = []
frames = []

# ----------------------------
# evolution
# ----------------------------
for t in range(steps):
    gx, gy = grad_xy(theta)
    grad2 = gx**2 + gy**2
    lap_th = laplacian(theta)
    lap_kp = laplacian(kappa)

    # theta and kappa update
    theta_tt = lap_th + chi * np.divmod(np.gradient(kappa*theta)[0],1)[0]
    theta_t = (1-gamma)*theta_t + dt*theta_tt
    theta += dt*theta_t
    kappa += dt*(alpha*lap_kp - 0.1*kappa + chi*grad2)

    # diagnostics
    L = 0.5*(theta_t**2 - chi*grad2) - 0.5*kappa**2
    energy_trace.append(np.nanmean(L))
    corr_trace.append(np.nanmean(theta*kappa))
    S = spectral_entropy(theta)
    entropy_trace.append(S)
    chi_trace.append(chi)
    alpha_trace.append(alpha)

    # --- predictive self-tuning ---
    if t > predict_window:
        # simple linear forecast of entropy
        prev = np.array(entropy_trace[-predict_window:])
        slope = np.polyfit(np.arange(predict_window), prev, 1)[0]
        forecast = prev[-1] + slope*predict_window
        err = forecast - prev[-1]
        forecast_error_trace.append(err)

        # update χ and α based on forecast
        chi += -forecast_gain*err*0.05
        alpha += forecast_gain*err*0.02
        chi = np.clip(chi, 0.1, 0.25)
        alpha = np.clip(alpha, 0.03, 0.07)
    else:
        forecast_error_trace.append(0.0)

    # occasional snapshot
    if t % 30 == 0:
        fig, ax = plt.subplots(1,2,figsize=(7.5,3.3))
        ax[0].imshow(theta,cmap='inferno')
        ax[0].set_title(f"θ field @ step {t}")
        ax[1].imshow(kappa,cmap='plasma')
        ax[1].set_title("κ field")
        for a in ax: a.axis('off')
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# ----------------------------
# detect transition
# ----------------------------
entropy_arr = np.array(entropy_trace)
dS = np.gradient(entropy_arr)
transition_step = int(np.argmax(np.abs(dS) > 0.02))

# ----------------------------
# plots
# ----------------------------
plt.figure(figsize=(7,4))
plt.plot(energy_trace,label='⟨L⟩')
plt.plot(corr_trace,label='⟨θ*κ⟩')
plt.plot(np.array(entropy_trace)/max(entropy_trace),label='Spectral entropy (norm.)',color='green')
plt.plot(np.array(chi_trace)/max(chi_trace),'r--',label='χ(t)/χmax')
plt.axvline(transition_step,color='magenta',ls='--',label='transition')
plt.legend()
plt.title("F7 - Predictive Self-Tuning Dynamics")
plt.tight_layout()
plt.savefig("PAEV_TestF7_Predictive_Trace.png",dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF7_Predictive_Trace.png")

plt.figure(figsize=(5,4))
plt.plot(entropy_trace,corr_trace,color='orange')
plt.xlabel("Spectral entropy")
plt.ylabel("⟨θ*κ⟩")
plt.title("F7 - Predictive Phase Portrait")
plt.tight_layout()
plt.savefig("PAEV_TestF7_PredictivePhasePortrait.png",dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF7_PredictivePhasePortrait.png")

plt.figure(figsize=(6,4))
plt.plot(forecast_error_trace,color='purple')
plt.title("F7 - Forecast Error Evolution")
plt.xlabel("Step")
plt.ylabel("Entropy Forecast Error")
plt.tight_layout()
plt.savefig("PAEV_TestF7_ForecastError.png",dpi=160)
plt.close()
print("✅ Saved file: PAEV_TestF7_ForecastError.png")

# animation
imageio.mimsave("PAEV_TestF7_Propagation.gif",frames,fps=10)
print("✅ Saved animation to: PAEV_TestF7_Propagation.gif")

# ----------------------------
# summary
# ----------------------------
summary = f"""
=== Test F7 - Predictive Self-Tuning Phase Dynamics ===
⟨L⟩ final = {energy_trace[-1]:.4e}
⟨θ*κ⟩ final = {corr_trace[-1]:.4e}
Spectral entropy final = {entropy_trace[-1]:.4e}
χ final = {chi_trace[-1]:.4e}
α final = {alpha_trace[-1]:.4e}
Transition detected at step {transition_step}
Mean forecast error = {np.mean(np.abs(forecast_error_trace)):.4e}
Perturbation mode: ON
All output files saved in working directory.
----------------------------------------------------------
"""
with open("PAEV_TestF7_Summary.txt","w",encoding="utf-8") as f: f.write(summary)
print(summary)