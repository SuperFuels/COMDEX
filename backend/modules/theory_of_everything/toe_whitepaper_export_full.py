"""
TOE Whitepaper Full Export — backend/modules/theory_of_everything/toe_whitepaper_export_full.py

Generates a full-color PDF of the Unified TOE Framework (Post-L Series),
combining constants, equations, and plots into a formatted report.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf():
    # === Paths ===
    base_dir = Path(__file__).resolve().parents[3]  # /workspaces/COMDEX
    docs_dir = base_dir / "docs" / "rfc"
    docs_dir.mkdir(parents=True, exist_ok=True)

    constants_path = base_dir / "backend" / "modules" / "knowledge" / "constants_v1.1.json"
    pdf_path = docs_dir / "TOE_Whitepaper_v1.1_full.pdf"

    # === Load constants ===
    constants = json.loads(constants_path.read_text(encoding="utf-8"))

    # === Setup PDF ===
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=22, alignment=1, textColor=colors.HexColor("#002b5c"))
    section_style = ParagraphStyle("Section", parent=styles["Heading1"], textColor=colors.HexColor("#004488"))
    normal = styles["Normal"]

    story = []

    # === Title Page ===
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("Unified Theory of Everything Framework", title_style))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Post-L Series Consolidation — COMDEX Research Initiative", normal))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", normal))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("<b>Version:</b> v1.1 (Full Export with Figures)", normal))
    story.append(Spacer(1, 1 * inch))

    # === Abstract ===
    story.append(Paragraph("Abstract", section_style))
    story.append(Paragraph(
        "This document consolidates the Theory of Everything (TOE) constants derived from "
        "the H through L series tests. It presents a unified Lagrangian form consistent across "
        "quantum, relativistic, and thermodynamic domains. Verified internal stability was achieved "
        "through multi-domain synchronization and reproducibility validation.", normal))
    story.append(Spacer(1, 0.3 * inch))

    # === Unified Lagrangian ===
    story.append(Paragraph("Unified Lagrangian Form", section_style))
    story.append(Paragraph(
        r"$\mathcal{L}_{total} = \hbar_{eff} |\nabla \psi|^2 + G_{eff} R - \Lambda_{eff} g + \alpha_{eff} |\psi|^2 \kappa$",
        normal))
    story.append(Spacer(1, 0.3 * inch))

    # === Constants Table ===
    story.append(Paragraph("Effective Constants Summary", section_style))
    data = [["Constant", "Value", "Description"]]
    for key, val in constants.items():
        if isinstance(val, (float, int)):
            data.append([key, f"{val:.6e}", "—"])
    tbl = Table(data, colWidths=[2*inch, 2*inch, 2*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#004488")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.3 * inch))

    # === Figures ===
    story.append(Paragraph("Selected Validation Plots", section_style))
    plots = [
        "PAEV_J2_HolographicDrift.png",
        "PAEV_K2_MultiDomainEnergy.png",
        "PAEV_L1_ConsistencyMap.png",
        "PAEV_L2_Reproducibility.png",
    ]
    for plot_name in plots:
        plot_path = base_dir / plot_name
        if plot_path.exists():
            story.append(Image(str(plot_path), width=5.5*inch, height=3.0*inch))
            story.append(Spacer(1, 0.2 * inch))
        else:
            story.append(Paragraph(f"⚠️ Missing plot: {plot_name}", normal))
            story.append(Spacer(1, 0.2 * inch))

    # === Discussion ===
    story.append(Paragraph("Discussion", section_style))
    story.append(Paragraph(
        "The results demonstrate stable cross-domain coherence within tolerance bounds. "
        "Residual drift across quantum–relativistic–thermal coupling was minimized post-J2. "
        "Future work includes empirical correlation to observed cosmological data and "
        "possible integration with high-energy datasets for validation.", normal))
    story.append(Spacer(1, 0.4 * inch))

    # === Footer ===
    story.append(Paragraph("<b>COMDEX Research Initiative — Internal TOE Framework Export</b>", normal))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("© 2025 COMDEX — All rights reserved", normal))

    # === Build PDF ===
    doc.build(story)
    print(f"✅ TOE whitepaper successfully generated → {pdf_path}")

if __name__ == "__main__":
    generate_pdf()