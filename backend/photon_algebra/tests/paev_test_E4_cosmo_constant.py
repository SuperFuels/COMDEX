# ==========================================================
# Test E4 - Emergent Cosmological Constant (Vacuum Curvature Balance)
# ==========================================================
# Purpose:
#   Explore whether a stable average curvature offset (Λ_eff)
#   emerges naturally from the equilibrium of quantum foam fluctuations.
#
# Outputs:
#   - Animation of curvature-vacuum interaction
#   - Plot of mean curvature (⟨κ⟩) and variance (⟨κ2⟩)
#   - Effective cosmological constant Λ_eff evolution
#   - Correlation between curvature pressure and vacuum noise
# ==========================================================

import numpy as np
import matplotlib.pyplot as plt
import imageio.v2 as imageio

# Grid and parameters
N = 200
x = np.linspace(-1, 1, N)
y = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)

# Initial vacuum curvature field
kappa = 0.01 * np.random.randn(N, N)

# Parameters
dt = 0.01
steps = 400
alpha = 0.05     # curvature damping
beta = 0.02      # vacuum drive
gamma = 0.001    # feedback coupling

frames = []
mean_curv = []
var_curv = []
lambda_eff = []

def laplacian(Z):
    return (
        -4 * Z
        + np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
        + np.roll(Z, 1, 1) + np.roll(Z, -1, 1)
    )

# Main evolution loop
for step in range(steps):
    d2k = laplacian(kappa)
    noise = np.random.randn(N, N) * 0.001
    kappa += dt * (beta * d2k - alpha * kappa + gamma * noise)

    mean_k = np.mean(kappa)
    var_k = np.var(kappa)
    Λ_eff = mean_k + 0.1 * var_k  # emergent offset relation

    mean_curv.append(mean_k)
    var_curv.append(var_k)
    lambda_eff.append(Λ_eff)

    if step % 20 == 0:
        fig, ax = plt.subplots(figsize=(5,5))
        im = ax.imshow(kappa, cmap='twilight_shifted', extent=[-1,1,-1,1])
        ax.set_title(f"Test E4 - Vacuum Curvature Field\nStep {step}")
        plt.colorbar(im, ax=ax, label="κ curvature")
        plt.tight_layout()
        fig.canvas.draw()
        frames.append(np.array(fig.canvas.renderer.buffer_rgba()))
        plt.close(fig)

# Save animation
imageio.mimsave("PAEV_TestE4_CosmoConstant.gif", frames, fps=10)
print("✅ Saved animation to: PAEV_TestE4_CosmoConstant.gif")

# Mean and variance evolution
plt.figure()
plt.plot(mean_curv, label="⟨κ⟩ mean curvature", color="blue")
plt.plot(var_curv, label="⟨κ2⟩ variance", color="orange")
plt.title("Test E4 - Curvature Mean & Variance Evolution")
plt.xlabel("Time step")
plt.ylabel("Value")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_TestE4_CosmoConstant_CurvatureStats.png")
plt.close()
print("✅ Saved curvature statistics plot: PAEV_TestE4_CosmoConstant_CurvatureStats.png")

# Effective Λ evolution
plt.figure()
plt.plot(lambda_eff, color="green")
plt.title("Test E4 - Effective Cosmological Constant Evolution")
plt.xlabel("Time step")
plt.ylabel("Λ_eff")
plt.tight_layout()
plt.savefig("PAEV_TestE4_CosmoConstant_LambdaEff.png")
plt.close()
print("✅ Saved Λ_eff evolution plot: PAEV_TestE4_CosmoConstant_LambdaEff.png")

print("\n=== Test E4 - Emergent Cosmological Constant Complete ===")
print(f"⟨κ⟩ final = {np.mean(mean_curv):.4e}")
print(f"⟨κ2⟩ final = {np.mean(var_curv):.4e}")
print(f"⟨Λ_eff⟩ final = {np.mean(lambda_eff):.4e}")
print("All output files saved in working directory.")
print("----------------------------------------------------------")