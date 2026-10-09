"""
report_generator.py
Generates a PDF analytics report using reportlab (pure-python, no
external binaries or network downloads required).
"""

import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

FOREST_GREEN = colors.Color(9 / 255, 38 / 255, 24 / 255)
ACCENT_GREEN = colors.Color(60 / 255, 230 / 255, 143 / 255)


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(FOREST_GREEN)
    canvas.rect(0, A4[1] - 25 * mm, A4[0], 25 * mm, fill=1, stroke=0)
    canvas.setFillColor(ACCENT_GREEN)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(15 * mm, A4[1] - 16 * mm, "WildSense — Wildlife Conflict Alert Report")
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(
        15 * mm, 10 * mm,
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | Page {doc.page}"
    )
    canvas.restoreState()


def generate_pdf_report(stats, animal_freq, threat_dist, recent_detections):
    filename = f"wildlife_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=32 * mm, bottomMargin=18 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=FOREST_GREEN, spaceBefore=10, spaceAfter=6)
    body = styles["Normal"]

    story = []

    # Summary
    story.append(Paragraph("Summary", h2))
    top_animal = animal_freq[0]["animal_name"] if animal_freq else "N/A"
    summary_lines = [
        f"Total Detections: <b>{stats['total']}</b>",
        f"High Risk Detections: <b>{stats['high_risk']}</b>",
        f"Unique Animals: <b>{stats['unique_animals']}</b>",
        f"Most Detected Animal: <b>{str(top_animal).title()}</b>",
    ]
    for line in summary_lines:
        story.append(Paragraph(line, body))
    story.append(Spacer(1, 10))

    # Animal frequency table
    story.append(Paragraph("Animal Detection Frequency", h2))
    if animal_freq:
        data = [["Animal", "Count"]] + [[row["animal_name"].title(), str(row["count"])] for row in animal_freq]
        story.append(_styled_table(data, [90 * mm, 30 * mm]))
    else:
        story.append(Paragraph("No data yet.", body))
    story.append(Spacer(1, 10))

    # Threat distribution table
    story.append(Paragraph("Threat Distribution", h2))
    if threat_dist:
        data = [["Threat Level", "Count"]] + [[row["threat_level"], str(row["count"])] for row in threat_dist]
        story.append(_styled_table(data, [90 * mm, 30 * mm]))
    else:
        story.append(Paragraph("No data yet.", body))
    story.append(Spacer(1, 10))

    # Recent detections table
    story.append(Paragraph("Recent Detections", h2))
    if recent_detections:
        data = [["Animal", "Confidence", "Date/Time", "Location"]]
        for row in list(recent_detections)[:20]:
            data.append([
                str(row["animal_name"]).title(),
                f"{row['confidence']}%",
                str(row["date_time"]),
                str(row["location"])[:30],
            ])
        story.append(_styled_table(data, [35 * mm, 25 * mm, 40 * mm, 55 * mm]))
    else:
        story.append(Paragraph("No detections recorded yet.", body))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return filepath


def _styled_table(data, col_widths):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), FOREST_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t
