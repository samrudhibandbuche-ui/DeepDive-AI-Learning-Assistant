from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


def generate_notes_pdf(
    video_name: str,
    transcript: str,
    study_notes: str,
) -> str:
    """Generate a formatted PDF containing the transcript and AI notes."""

    pdf_folder = Path("pdfs")
    pdf_folder.mkdir(exist_ok=True)

    safe_name = Path(video_name).stem.replace(" ", "_")
    pdf_path = pdf_folder / f"{safe_name}_deepdive_notes.pdf"

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
        title="DeepDive AI Study Notes",
        author="DeepDive AI",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DeepDiveTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    subtitle_style = ParagraphStyle(
        "DeepDiveSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=24,
    )

    heading_style = ParagraphStyle(
        "DeepDiveHeading",
        parent=styles["Heading2"],
        fontSize=16,
        leading=20,
        spaceBefore=14,
        spaceAfter=10,
    )

    body_style = ParagraphStyle(
        "DeepDiveBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=15,
        spaceAfter=8,
    )

    story = []

    story.append(Paragraph("DeepDive AI", title_style))
    story.append(
        Paragraph(
            "AI-Powered Video Note Taker and Learning Assistant",
            subtitle_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>Video:</b> {escape(video_name)}",
            body_style,
        )
    )

    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("AI-Generated Study Notes", heading_style))

    for block in study_notes.split("\n"):
        cleaned_block = block.strip()

        if not cleaned_block:
            story.append(Spacer(1, 6))
            continue

        upper_block = cleaned_block.upper()

        if upper_block in {
            "SUMMARY",
            "DETAILED NOTES",
            "KEY POINTS",
            "KEYWORDS",
        }:
            story.append(Paragraph(escape(cleaned_block), heading_style))

        elif cleaned_block.startswith(("-", "•", "*")):
            bullet_text = cleaned_block.lstrip("-•* ").strip()

            story.append(
                Paragraph(
                    f"• {escape(bullet_text)}",
                    body_style,
                )
            )

        else:
            story.append(
                Paragraph(
                    escape(cleaned_block),
                    body_style,
                )
            )

    story.append(PageBreak())
    story.append(Paragraph("Complete Transcript", heading_style))

    transcript_paragraphs = transcript.split("\n")

    for paragraph in transcript_paragraphs:
        cleaned_paragraph = paragraph.strip()

        if cleaned_paragraph:
            story.append(
                Paragraph(
                    escape(cleaned_paragraph),
                    body_style,
                )
            )
            story.append(Spacer(1, 5))

    document.build(story)

    return str(pdf_path)