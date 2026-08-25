"""
Preview Agent - deliberately has NO prompt.py and makes NO LLM call.

It takes the JSON already produced by Requirement / Architecture / Tools /
Cost and renders it into a single proposal PDF using reportlab only. This
keeps the "overall preview" stage free (no tokens spent) since it's pure
formatting of data we already have.
"""
import os
from html import escape
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)

from app.agents.base_agent import BaseAgent
from app.config import settings


class PreviewAgent(BaseAgent):
    name = "preview"

    def run(self, context: dict) -> dict:
        os.makedirs(settings.generated_dir, exist_ok=True)
        session_id = context.get("session_id", "session")
        filename = f"{session_id}_preview.pdf"
        filepath = os.path.join(settings.generated_dir, filename)

        self._build_pdf(filepath, context)

        return {
            "pdf_filename": filename,
            "pdf_path": filepath,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # -- rendering -----------------------------------------------------

    def _build_pdf(self, filepath: str, context: dict) -> None:
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("H1", parent=styles["Heading1"], spaceAfter=10)
        h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
        body = styles["BodyText"]

        story = [
            Paragraph("Project Proposal Preview", h1),
            Paragraph(f"Request: {escape(str(context.get('query', '')))}", body),
            Spacer(1, 0.4 * cm),
        ]

        requirement = context.get("requirement", {}) or {}
        architecture = context.get("architecture", {}) or {}
        tools = context.get("tools", {}) or {}
        cost = context.get("cost", {}) or {}

        story.append(Paragraph("1. Requirements", h2))
        story.append(Paragraph(escape(str(requirement.get("feature_summary", "-"))), body))
        story.extend(self._bullet_section("Functional requirements", requirement.get("functional_requirements"), body))
        story.extend(self._bullet_section("Non-functional requirements", requirement.get("non_functional_requirements"), body))
        story.extend(self._bullet_section("Edge cases", requirement.get("edge_cases"), body))
        story.extend(self._bullet_section("Assumptions", requirement.get("assumptions"), body))

        story.append(Paragraph("2. Architecture", h2))
        story.append(Paragraph(escape(str(architecture.get("approach_summary", "-"))), body))
        components = architecture.get("components") or []
        if components:
            rows = [["Component", "Responsibility", "Type"]]
            rows += [[c.get("name", ""), c.get("responsibility", ""), c.get("type", "")] for c in components]
            story.append(self._table(rows))
        story.extend(self._bullet_section("Data flow", architecture.get("data_flow"), body))
        story.extend(self._bullet_section("File structure", architecture.get("file_structure"), body))

        story.append(Paragraph("3. Tools", h2))
        tool_rows = tools.get("tools") or []
        if tool_rows:
            rows = [["Tool", "Category", "Purpose", "Required"]]
            rows += [
                [t.get("name", ""), t.get("category", ""), t.get("purpose", ""), "Yes" if t.get("required") else "No"]
                for t in tool_rows
            ]
            story.append(self._table(rows))

        story.append(Paragraph("4. Cost Estimate (tools/services only)", h2))
        line_items = cost.get("line_items") or []
        if line_items:
            rows = [["Tool", "Pricing model", "Est. cost", "Notes"]]
            rows += [
                [li.get("tool", ""), li.get("pricing_model", ""), li.get("estimated_cost", ""), li.get("notes", "")]
                for li in line_items
            ]
            story.append(self._table(rows))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"Estimated monthly total: {escape(str(cost.get('estimated_monthly_total', '-')))}", body))
        if cost.get("disclaimer"):
            story.append(Paragraph(f"Note: {escape(str(cost['disclaimer']))}", styles["Italic"]))

        doc.build(story)

    @staticmethod
    def _bullet_section(title: str, items, body_style) -> list:
        if not items:
            return []
        out = [Paragraph(f"<b>{title}</b>", body_style)]
        out.append(
            ListFlowable(
                [ListItem(Paragraph(escape(str(i)), body_style)) for i in items],
                bulletType="bullet",
            )
        )
        return out

    @staticmethod
    def _table(rows: list[list[str]]) -> Table:
        safe_rows = [[escape(str(cell)) for cell in row] for row in rows]
        t = Table(safe_rows, hAlign="LEFT", repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d2d2d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
                ]
            )
        )
        return t
