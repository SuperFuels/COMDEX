"""
K3 — Whitepaper Appendix Auto-Export
Generates LaTeX appendices for TOE whitepaper publication.
"""

import json
from pathlib import Path

# Load constants
const_path = Path("backend/modules/knowledge/constants_v1.1.json")
constants = json.loads(const_path.read_text())

appendix_dir = Path("docs/rfc")
appendix_dir.mkdir(parents=True, exist_ok=True)

# Appendix A: Lagrangian
tex_A = r"""
\section*{Appendix A — Unified Lagrangian Form}
\[
\mathcal{L}_{total} =
\hbar_{eff} |\nabla \psi|^2 + G_{eff} R - \Lambda_{eff} g + \alpha_{eff} |\psi|^2 \kappa
\]
All constants are derived from post-J2 TOE synchronization.
"""

# Appendix B: Constants table
tex_B = "\\section*{Appendix B — Validated Constants Table}\n\\begin{tabular}{lll}\n"
tex_B += "\\textbf{Constant} & \\textbf{Value} & \\textbf{Description} \\\\\n\\hline\n"
for k,v in constants.items():
    if isinstance(v,(int,float)):
        tex_B += f"{k} & {v:.6e} &  \\\\\n"
tex_B += "\\end{tabular}\n"

# Combined master export
master = appendix_dir / "TOE_Whitepaper_Appendices.tex"
(master).write_text(tex_A + "\n\n" + tex_B)
print("=== K3 — Whitepaper Appendix Export ===")
print(f"✅ Exported → {master.resolve()}")
print("----------------------------------------------------------")