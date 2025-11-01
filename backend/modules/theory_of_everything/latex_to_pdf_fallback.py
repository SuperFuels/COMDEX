# backend/modules/theory_of_everything/latex_to_pdf_fallback.py
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from pathlib import Path
import re

def convert_tex_to_pdf(tex_path: str):
    tex = Path(tex_path)
    if not tex.exists():
        raise FileNotFoundError(f"Missing LaTeX file: {tex_path}")

    pdf_path = tex.with_suffix(".pdf")
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Basic parsing: split into sections
    content = tex.read_text(encoding="utf-8")
    sections = re.split(r"\\\\section\*{([^}]*)}", content)

    # Title
    title = "Unified TOE Framework: Post-J Series Consolidation"
    elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    elements.append(Spacer(1, 1 * cm))

    # Loop sections
    for i in range(1, len(sections), 2):
        heading = sections[i].strip()
        body = sections[i + 1].strip()
        elements.append(Paragraph(f"<b>{heading}</b>", styles["Heading2"]))
        elements.append(Paragraph(body.replace("\\", ""), styles["BodyText"]))
        elements.append(Spacer(1, 0.5 * cm))

    # Table formatting (replace any LaTeX table with simple text table)
    content = re.sub(r"\\begin{tabular}.*?\\end{tabular}", "[Table omitted in fallback PDF]", content, flags=re.S)

    elements.append(Paragraph("<i>Generated via COMDEX TOE Engine - Python fallback exporter.</i>", styles["Italic"]))
    doc.build(elements)
    print(f"✅ PDF exported -> {pdf_path.resolve()}")

if __name__ == "__main__":
    convert_tex_to_pdf("docs/rfc/TOE_Whitepaper_v1.tex")