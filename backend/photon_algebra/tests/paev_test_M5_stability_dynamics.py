"""
M5 — Wormhole Stability and Collapse Dynamics
---------------------------------------------
Analyzes the dynamic stability of the entangled curvature bridge (ER=EPR analogue)
under small perturbations to the throat curvature κ.

Outputs:
  - PAEV_M5_ThroatStability.png
  - PAEV_M5_EnergyFluxEvolution.png
  - PAEV_M5_Classification.txt
  - docs/rfc/TOE_Wormhole_Appendix_M.pdf
"""

import numpy as np
import matplotlib.pyplot as plt
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from datetime import datetime

# === Load constants ===
with open("backend/modules/knowledge/constants_v1.1.json") as f:
    consts = json.load(f)

ħ = consts["ħ_eff"]
G = consts["G_eff"]
Λ = consts["Λ_eff"]
α = consts["α_eff"]

# === Simulation parameters ===
N = 1000
t = np.linspace(0, 10, N)
ε = 0.05
ω = 2 * np.pi * 0.25
κ0 = np.array([-1.0, -1.0])
κ1 = κ0[0] + ε * np.sin(ω * t)
κ2 = κ0[1] + ε * np.sin(ω * t + np.pi / 4)

# === Compute stability metrics ===
Δκ = np.abs(κ1 - κ2)
S = np.exp(-Δκ / α)
E_flux = np.abs(np.gradient(κ1 + κ2)) * ħ

# === Stability classification ===
Δκ_final = Δκ[-1]
if Δκ_final < 0.1:
    stability = "Stable"
elif Δκ_final < 0.3:
    stability = "Oscillatory"
else:
    stability = "Collapsed"

# === Save classification ===
class_path = Path("backend/modules/knowledge/PAEV_M5_Classification.txt")
class_path.write_text(f"M5 Wormhole Stability: {stability}\nΔκ_final = {Δκ_final:.3e}\n")

# === Plot 1: Throat Stability ===
plt.figure(figsize=(8,5))
plt.plot(t, S, label="Stability Metric S", color="purple")
plt.axhline(0.9, color="gray", ls="--", label="Stable threshold (S=0.9)")
plt.xlabel("Time")
plt.ylabel("Stability S")
plt.title("M5 — Throat Stability Evolution")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_M5_ThroatStability.png", dpi=150)
plt.close()

# === Plot 2: Energy Flux Evolution ===
plt.figure(figsize=(8,5))
plt.plot(t, E_flux / np.max(E_flux), label="Normalized Energy Flux", color="orange")
plt.xlabel("Time")
plt.ylabel("Normalized flux")
plt.title("M5 — Energy Flux Evolution")
plt.legend()
plt.tight_layout()
plt.savefig("PAEV_M5_EnergyFluxEvolution.png", dpi=150)
plt.close()

print("=== M5 — Wormhole Stability and Collapse Dynamics ===")
print(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}")
print(f"Δκ_final={Δκ_final:.3e}")
print(f"Classification: {stability}")
print("✅ Plots and classification file saved.")

# === PDF Report Export ===
report_path = Path("docs/rfc/TOE_Wormhole_Appendix_M.pdf")
report_path.parent.mkdir(parents=True, exist_ok=True)

doc = SimpleDocTemplate(str(report_path), pagesize=A4)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("<b>Appendix M — Wormhole Stability & Collapse Dynamics</b>", styles["Title"]))
story.append(Spacer(1, 12))
story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
story.append(Spacer(1, 12))

story.append(Paragraph(f"Classification Result: <b>{stability}</b>", styles["Normal"]))
story.append(Paragraph(f"Δκ_final = {Δκ_final:.3e}", styles["Normal"]))
story.append(Paragraph(f"ħ={ħ:.3e}, G={G:.3e}, Λ={Λ:.3e}, α={α:.3f}", styles["Normal"]))
story.append(Spacer(1, 12))

table_data = [
    ["Metric", "Description", "Value"],
    ["Δκ_final", "Final curvature difference", f"{Δκ_final:.3e}"],
    ["Max |E_flux|", "Maximum energy flux magnitude", f"{np.max(E_flux):.3e}"],
    ["Mean S", "Average stability metric", f"{np.mean(S):.3f}"],
]
t = Table(table_data)
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
    ("GRID", (0,0), (-1,-1), 0.5, colors.black),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold")
]))
story.append(t)
story.append(Spacer(1, 12))
story.append(Paragraph("See associated figures:", styles["Italic"]))
story.append(Paragraph("- PAEV_M5_ThroatStability.png", styles["Normal"]))
story.append(Paragraph("- PAEV_M5_EnergyFluxEvolution.png", styles["Normal"]))

doc.build(story)

print(f"📘 Exported Appendix → {report_path.resolve()}")
print("----------------------------------------------------------")