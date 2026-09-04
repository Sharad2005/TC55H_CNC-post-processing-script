from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "report-source.md"
OUTPUT = ROOT / "output" / "pdf" / "CM45L_TC55H_Technical_Dossier.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2670A7")
PALE = colors.HexColor("#EAF3F8")
INK = colors.HexColor("#1E2933")
MUTED = colors.HexColor("#60717F")
LINE = colors.HexColor("#C8D7E2")


def inline_markup(text: str) -> str:
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(
        r"(https?://[^\s<]+)",
        lambda m: f'<link href="{m.group(1).rstrip(".,;)")}" color="#2670A7">{m.group(1).rstrip(".,;)")}</link>'
        + m.group(1)[len(m.group(1).rstrip(".,;)")):],
        text,
    )
    return text


class DossierDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=19 * mm,
            bottomMargin=18 * mm,
            title="CM45L / TopCNC TC55H Technical Dossier",
            author="OpenAI Codex",
            subject="Controller identification, operation, wiring, programming, and revision notes",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="main", frames=[frame], onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 15 * mm, A4[0] - doc.rightMargin, 15 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, 10.5 * mm, "CM45L / TC55H technical dossier")
        canvas.drawRightString(A4[0] - doc.rightMargin, 10.5 * mm, f"Page {doc.page}")
        canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=29,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=7 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "CoverMeta",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=3 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "H1x",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=NAVY,
        spaceBefore=7 * mm,
        spaceAfter=3 * mm,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        "Bodyx",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.4,
        leading=13.4,
        textColor=INK,
        spaceAfter=2.5 * mm,
        allowWidows=0,
        allowOrphans=0,
    )
)
styles.add(
    ParagraphStyle(
        "Bulletx",
        parent=styles["Bodyx"],
        leftIndent=5 * mm,
        firstLineIndent=-3.5 * mm,
        bulletIndent=0,
        spaceAfter=1.5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "Numberx",
        parent=styles["Bodyx"],
        leftIndent=6 * mm,
        firstLineIndent=-5 * mm,
        spaceAfter=1.8 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "Callout",
        parent=styles["Bodyx"],
        backColor=PALE,
        borderColor=BLUE,
        borderWidth=0.7,
        borderPadding=9,
        leading=14,
        spaceBefore=2 * mm,
        spaceAfter=5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        "CodeLine",
        parent=styles["Bodyx"],
        fontName="Courier",
        fontSize=8.5,
        leading=12,
        backColor=colors.HexColor("#F3F5F7"),
        borderPadding=6,
        leftIndent=4 * mm,
        rightIndent=4 * mm,
        spaceAfter=3 * mm,
    )
)


def build_story(markdown: str):
    lines = markdown.splitlines()
    title = lines[0].removeprefix("# ").strip()
    story = [Spacer(1, 22 * mm), Paragraph(inline_markup(title), styles["CoverTitle"])]

    idx = 1
    meta = []
    while idx < len(lines) and not lines[idx].startswith("## "):
        if lines[idx].strip():
            meta.append(lines[idx].replace("  ", " ").strip())
        idx += 1
    for item in meta:
        story.append(Paragraph(inline_markup(item), styles["CoverMeta"]))
    story.extend([Spacer(1, 8 * mm), Paragraph(
        "Verified controller-family reference. Host-machine identity and machine-builder wiring remain to be supplied from the physical machine.",
        styles["Callout"],
    )])

    callout_next = False
    paragraph = []

    def flush():
        nonlocal paragraph, callout_next
        if paragraph:
            text = " ".join(x.strip() for x in paragraph)
            style = styles["Callout"] if callout_next else styles["Bodyx"]
            story.append(Paragraph(inline_markup(text), style))
            paragraph = []
            callout_next = False

    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()
        if not stripped:
            flush()
        elif raw.startswith("## "):
            flush()
            heading = raw[3:].strip()
            story.append(Paragraph(inline_markup(heading), styles["H1x"]))
            callout_next = heading == "Direct answer"
        elif raw.startswith("- "):
            flush()
            story.append(Paragraph(inline_markup(raw[2:]), styles["Bulletx"], bulletText="•"))
        elif re.match(r"^\d+\. ", raw):
            flush()
            number, rest = raw.split(". ", 1)
            story.append(Paragraph(inline_markup(rest), styles["Numberx"], bulletText=number + "."))
        elif stripped.startswith("`") and stripped.endswith("`"):
            flush()
            story.append(Paragraph(escape(stripped.strip("`")), styles["CodeLine"]))
        else:
            paragraph.append(raw)
        idx += 1
    flush()
    return story


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
markdown = SOURCE.read_text(encoding="utf-8")
doc = DossierDoc(str(OUTPUT))
doc.build(build_story(markdown))
print(OUTPUT)
