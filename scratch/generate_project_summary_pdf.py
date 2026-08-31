"""
Script to generate an elegant, professional Project Summary PDF for the Multi-Agent Orchestration System.
"""

from __future__ import annotations

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import (
    Drawing,
    Rect,
    String,
    Line,
    Polygon,
    Group,
)


def create_architecture_diagram(width=500, height=210) -> Drawing:
    """Draws a clean, vector-based architecture diagram of the 5-agent pipeline and quality gate."""
    d = Drawing(width, height)
    
    # Background card
    d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#0D1117"), strokeColor=colors.HexColor("#30363D"), strokeWidth=1, rx=8, ry=8))
    
    # Title
    d.add(String(20, height - 22, "MULTI-AGENT WORKFLOW & QUALITY GATE ARCHITECTURE", fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor("#58A6FF")))
    
    # Agent boxes configuration: (name, desc, x, y, width, height, color, text_color)
    nodes = [
        ("Planner Agent", "Deconstructs goal & builds plan", 20, 125, 130, 42, "#1F2937", "#E5E7EB", "#9333EA"),
        ("Research Agent", "Retrieves context & docs", 185, 125, 130, 42, "#1F2937", "#E5E7EB", "#2563EB"),
        ("Coder Agent", "Generates clean source files", 350, 125, 130, 42, "#1F2937", "#E5E7EB", "#059669"),
        ("Tester Agent", "Generates unit test suites", 350, 50, 130, 42, "#1F2937", "#E5E7EB", "#D97706"),
        ("Quality Gate", "Ruff · Pytest · Bandit", 185, 50, 130, 42, "#111827", "#F3F4F6", "#DC2626"),
        ("Reviewer Agent", "Evaluates architecture & gate", 20, 50, 130, 42, "#1F2937", "#E5E7EB", "#4F46E5"),
    ]
    
    for title, desc, x, y, w, h, bg, fg, border in nodes:
        # Box shadow/outline
        d.add(Rect(x, y, w, h, fillColor=colors.HexColor(bg), strokeColor=colors.HexColor(border), strokeWidth=1.5, rx=6, ry=6))
        # Title text
        d.add(String(x + 10, y + 25, title, fontName="Helvetica-Bold", fontSize=9, fillColor=colors.HexColor(fg)))
        # Subtitle text
        d.add(String(x + 10, y + 10, desc, fontName="Helvetica", fontSize=6.5, fillColor=colors.HexColor("#9CA3AF")))
    
    # Arrows connecting the flow
    def draw_arrow(x1, y1, x2, y2, label=""):
        d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#58A6FF"), strokeWidth=1.5))
        # Arrowhead
        if x2 > x1:  # right
            d.add(Polygon([x2, y2, x2 - 5, y2 + 3, x2 - 5, y2 - 3], fillColor=colors.HexColor("#58A6FF"), strokeColor=None))
        elif x2 < x1:  # left
            d.add(Polygon([x2, y2, x2 + 5, y2 + 3, x2 + 5, y2 - 3], fillColor=colors.HexColor("#58A6FF"), strokeColor=None))
        elif y2 < y1:  # down
            d.add(Polygon([x2, y2, x2 - 3, y2 + 5, x2 + 3, y2 + 5], fillColor=colors.HexColor("#58A6FF"), strokeColor=None))
        elif y2 > y1:  # up
            d.add(Polygon([x2, y2, x2 - 3, y2 - 5, x2 + 3, y2 - 5], fillColor=colors.HexColor("#58A6FF"), strokeColor=None))
            
        if label:
            d.add(String((x1+x2)/2 - 15, (y1+y2)/2 + 4, label, fontName="Helvetica-Bold", fontSize=6, fillColor=colors.HexColor("#F59E0B")))

    # Planner -> Research
    draw_arrow(150, 146, 185, 146)
    # Research -> Coder
    draw_arrow(315, 146, 350, 146)
    # Coder -> Tester
    draw_arrow(415, 125, 415, 92)
    # Tester -> Quality Gate
    draw_arrow(350, 71, 315, 71)
    # Quality Gate -> Reviewer (Pass)
    draw_arrow(185, 71, 150, 71, label="Pass")
    # Quality Gate -> Coder (Fail / Repair Loop)
    d.add(Line(250, 92, 250, 110, strokeColor=colors.HexColor("#EF4444"), strokeWidth=1.2, strokeDashArray=[2, 2]))
    d.add(Line(250, 110, 380, 110, strokeColor=colors.HexColor("#EF4444"), strokeWidth=1.2, strokeDashArray=[2, 2]))
    d.add(Line(380, 110, 380, 125, strokeColor=colors.HexColor("#EF4444"), strokeWidth=1.2, strokeDashArray=[2, 2]))
    d.add(Polygon([380, 125, 377, 120, 383, 120], fillColor=colors.HexColor("#EF4444"), strokeColor=None))
    d.add(String(260, 113, "Fail / Repair Loop", fontName="Helvetica-Bold", fontSize=6, fillColor=colors.HexColor("#EF4444")))

    # Bottom legend
    d.add(String(20, 15, "• Exactly 5 LLM Agents  |  • Internal Deterministic Quality Gate (Ruff + Pytest + Bandit)  |  • Fail-Closed Security", fontName="Helvetica-Oblique", fontSize=7, fillColor=colors.HexColor("#8B949E")))
    
    return d


def build_pdf(filename: str):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#0F172A")
    accent_color = colors.HexColor("#2563EB")
    dark_gray = colors.HexColor("#334155")
    light_bg = colors.HexColor("#F8FAFC")
    
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=4,
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=accent_color,
        spaceAfter=12,
    )
    
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    sub_section_heading = ParagraphStyle(
        "SubSectionHeading",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=accent_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=dark_gray,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=dark_gray,
        leftIndent=12,
        spaceAfter=3,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=dark_gray,
    )

    table_bold_cell = ParagraphStyle(
        "TableBoldCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=primary_color,
    )

    story = []

    # ─── HEADER ──────────────────────────────────────────────────────────
    story.append(Paragraph("Multi-Agent Orchestration System (MAOS)", title_style))
    story.append(Paragraph("Comprehensive Project Summary & Technical Architecture Specification", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=10))

    # ─── 1. EXECUTIVE OVERVIEW ──────────────────────────────────────────
    story.append(Paragraph("1. Executive Overview", section_heading))
    story.append(Paragraph(
        "The <b>Multi-Agent Orchestration System (MAOS)</b> is an enterprise-grade platform designed to autonomously plan, research, write, test, validate, and review complex software systems. Built on an asynchronous micro-orchestration engine with LangGraph, FastAPI, and Next.js, the system coordinates specialized local and cloud-based Large Language Models (Ollama, Groq, OpenAI) to deliver high-quality, production-ready applications with zero hallucinated verification.",
        body_style
    ))

    # ─── 2. SYSTEM ARCHITECTURE & 5-AGENT PIPELINE ──────────────────────
    story.append(Paragraph("2. Core Architecture & 5-Agent Workflow", section_heading))
    story.append(Paragraph(
        "The system maintains a strict separation of concerns across <b>exactly 5 LLM agents</b> supported by an <b>internal deterministic quality gate</b>:",
        body_style
    ))

    # Add Architecture Diagram
    story.append(Spacer(1, 4))
    story.append(create_architecture_diagram(width=540, height=195))
    story.append(Spacer(1, 8))

    # Table describing the 5 agents
    agent_data = [
        [Paragraph("Agent / Stage", table_header_style), Paragraph("Role & Responsibilities", table_header_style), Paragraph("Input / Output Artifacts", table_header_style)],
        [
            Paragraph("1. Planner Agent", table_bold_cell),
            Paragraph("Deconstructs high-level user requirements into an execution plan, determines required agent stages, and builds a comprehensive file manifest.", table_cell_style),
            Paragraph("<b>In:</b> User prompt<br/><b>Out:</b> Execution Plan, Manifest, Required Agents", table_cell_style),
        ],
        [
            Paragraph("2. Research Agent", table_bold_cell),
            Paragraph("Queries local vector embeddings (ChromaDB + FastEmbed) and performs domain knowledge synthesis for optimal architecture patterns.", table_cell_style),
            Paragraph("<b>In:</b> Plan + Knowledge Base<br/><b>Out:</b> Architectural Research Notes", table_cell_style),
        ],
        [
            Paragraph("3. Coder Agent", table_bold_cell),
            Paragraph("Generates production-ready code for each file in the manifest with clean artifact separation (no markdown commentary inside code).", table_cell_style),
            Paragraph("<b>In:</b> Plan + Research Notes<br/><b>Out:</b> Structured Code Artifacts", table_cell_style),
        ],
        [
            Paragraph("4. Tester Agent", table_bold_cell),
            Paragraph("Designs isolated unit & integration test suites and provides qualitative test coverage analysis without executing subprocesses.", table_cell_style),
            Paragraph("<b>In:</b> Generated Code + Plan<br/><b>Out:</b> Pytest Test Files + Coverage Analysis", table_cell_style),
        ],
        [
            Paragraph("Internal Quality Gate", table_bold_cell),
            Paragraph("Deterministic infrastructure executing syntax validation, import resolution, full Ruff linting, Pytest test suites, and Bandit security scans.", table_cell_style),
            Paragraph("<b>In:</b> Workspace Sandbox<br/><b>Out:</b> Authoritative Pass / Warning / Fail Evidence", table_cell_style),
        ],
        [
            Paragraph("5. Reviewer Agent", table_bold_cell),
            Paragraph("Performs qualitative review (SOLID principles, maintainability, architectural design) strictly governed by Quality Gate results.", table_cell_style),
            Paragraph("<b>In:</b> Code + Gate Evidence<br/><b>Out:</b> Final Review & Quality Score", table_cell_style),
        ],
    ]

    agent_table = Table(agent_data, colWidths=[1.3 * inch, 3.8 * inch, 2.4 * inch])
    agent_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), accent_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(agent_table)
    story.append(Spacer(1, 8))

    # Page Break for clean second page
    story.append(PageBreak())

    # ─── 3. KEY SUBSYSTEMS & PLATFORM MODULES ───────────────────────────
    story.append(Paragraph("3. Core Subsystems & Technical Capabilities", section_heading))

    story.append(Paragraph("A. Orchestration Engine & State Graph", sub_section_heading))
    story.append(Paragraph(
        "Powered by LangGraph, the workflow is structured as a state machine with full pause/resume capabilities, human-in-the-loop approval gates, checkpointing, and dynamic agent routing. If the Quality Gate detects a syntax or test failure, the engine automatically triggers an autonomous <b>Repair Loop</b> back to the Coder Agent (up to 3 attempts) before escalating to the Reviewer.",
        body_style
    ))

    story.append(Paragraph("B. Deterministic Quality Gate & Security Scanner", sub_section_heading))
    story.append(Paragraph(
        "A fail-closed verification pipeline guaranteeing code correctness: "
        "• <b>AST Syntax & Import Validator:</b> Parses AST trees and validates cross-file module imports against the workspace manifest. "
        "• <b>Ruff Static Analysis:</b> Executes <code>ruff check --no-cache</code> for linting and undefined symbol detection. "
        "• <b>Pytest Subprocess Sandbox:</b> Executes tests in an isolated sandbox workspace. "
        "• <b>Bandit Security Engine:</b> Runs static security scans ignoring legitimate test assertions (<code>-s B101</code>).",
        body_style
    ))

    story.append(Paragraph("C. RAG & Knowledge Vector Store", sub_section_heading))
    story.append(Paragraph(
        "Integrates <b>ChromaDB</b> vector store paired with <b>FastEmbed</b> (in-process ONNX embeddings on CPU) and <b>Nomic Embed Text</b>. Features recursive text chunking, automatic dimension mismatch auto-healing, and multi-format document ingestion (PDF, DOCX, Markdown, Python, TSX, YAML, SQL).",
        body_style
    ))

    story.append(Paragraph("D. Model Context Protocol (MCP) Server", sub_section_heading))
    story.append(Paragraph(
        "Implements a standard MCP tool server offering 20+ specialized execution tools across File Systems, PostgreSQL operations, GitHub integrations, HTTP requests, and sandboxed Terminal commands with timeout enforcement and security constraints.",
        body_style
    ))

    story.append(Paragraph("E. Enterprise Security, Multi-Tenancy & AIOps", sub_section_heading))
    story.append(Paragraph(
        "Built-in JWT authentication, Argon2/bcrypt password hashing, Role-Based Access Control (RBAC: Admin, Lead Developer, Developer, Viewer), Organization/Team tenancy isolation, audit logging, model routing rules, and real-time system health diagnostics.",
        body_style
    ))

    # ─── 4. TECHNOLOGY STACK ────────────────────────────────────────────
    story.append(Paragraph("4. Technology Stack & Infrastructure", section_heading))

    tech_data = [
        [Paragraph("Layer", table_header_style), Paragraph("Technologies & Frameworks", table_header_style), Paragraph("Key Role", table_header_style)],
        [
            Paragraph("Backend Core", table_bold_cell),
            Paragraph("Python 3.13, FastAPI, Uvicorn, AsyncIO", table_cell_style),
            Paragraph("High-performance asynchronous REST & SSE APIs", table_cell_style),
        ],
        [
            Paragraph("AI & Orchestration", table_bold_cell),
            Paragraph("LangGraph, LangChain, Ollama, Groq Cloud API", table_cell_style),
            Paragraph("Multi-agent graph scheduling & LLM inference", table_cell_style),
        ],
        [
            Paragraph("Database & Vector", table_bold_cell),
            Paragraph("PostgreSQL 16, SQLAlchemy 2.0 (asyncpg), Alembic, ChromaDB, FastEmbed", table_cell_style),
            Paragraph("Relational persistence & semantic document retrieval", table_cell_style),
        ],
        [
            Paragraph("Frontend & UI", table_bold_cell),
            Paragraph("Next.js 16 (Turbopack), React 19, Tailwind CSS v4, Lucide Icons", table_cell_style),
            Paragraph("Real-time interactive dashboard & timeline streaming", table_cell_style),
        ],
        [
            Paragraph("Code Verification", table_bold_cell),
            Paragraph("Ruff, Pytest, Pytest-AsyncIO, Bandit, AST Inspector", table_cell_style),
            Paragraph("Deterministic static analysis & security scanning", table_cell_style),
        ],
    ]

    tech_table = Table(tech_data, colWidths=[1.4 * inch, 3.7 * inch, 2.4 * inch])
    tech_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 10))

    # ─── FOOTER METADATA ───────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#94A3B8"), spaceAfter=6))
    story.append(Paragraph(
        "<i>Multi-Agent Orchestration System · Enterprise AI Architecture Specification · Confidential & Proprietary</i>",
        ParagraphStyle("FooterNote", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=7.5, leading=10, textColor=colors.HexColor("#64748B"), alignment=1)
    ))

    doc.build(story)
    print(f"Project summary PDF generated successfully at: {filename}")


if __name__ == "__main__":
    out_path = r"c:\Users\rohit\Multi Agent\Multi_Agent_Orchestration_System_Summary.pdf"
    build_pdf(out_path)
