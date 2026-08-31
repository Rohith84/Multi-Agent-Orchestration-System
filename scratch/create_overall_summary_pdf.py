"""Create a concise, status-free overview PDF for MultiAgent OS."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable, HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "MultiAgent_OS_Project_Overview.pdf"

NAVY = colors.HexColor("#10233F")
BLUE = colors.HexColor("#1E67D6")
CYAN = colors.HexColor("#12A8C8")
INK = colors.HexColor("#27364B")
MUTED = colors.HexColor("#607086")
PALE = colors.HexColor("#F4F7FB")
LINE = colors.HexColor("#D5DFED")
LIME = colors.HexColor("#C8E83C")


class ArchitectureDiagram(Flowable):
    """Vector architecture diagram drawn directly in the PDF."""

    def __init__(self, width=540, height=310):
        super().__init__()
        self.width, self.height = width, height

    def _box(self, canvas, x, y, w, h, title, subtitle, color):
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(color)
        canvas.setLineWidth(1.3)
        canvas.roundRect(x, y, w, h, 8, fill=1, stroke=1)
        canvas.setFillColor(color)
        canvas.roundRect(x, y + h - 8, w, 8, 8, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 8.2)
        title_y = y + h - (16 if h <= 36 else 21)
        subtitle_y = y + (8 if h <= 36 else 13)
        canvas.drawCentredString(x + w / 2, title_y, title)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 6.8)
        canvas.drawCentredString(x + w / 2, subtitle_y, subtitle)

    def _arrow(self, canvas, x1, y1, x2, y2, color=BLUE, dashed=False):
        canvas.saveState()
        canvas.setStrokeColor(color)
        canvas.setFillColor(color)
        canvas.setLineWidth(1.4)
        if dashed:
            canvas.setDash(3, 2)
        canvas.line(x1, y1, x2, y2)
        canvas.setDash()
        import math
        a = math.atan2(y2 - y1, x2 - x1)
        s = 6
        canvas.line(x2, y2, x2 - s * math.cos(a - 0.45), y2 - s * math.sin(a - 0.45))
        canvas.line(x2, y2, x2 - s * math.cos(a + 0.45), y2 - s * math.sin(a + 0.45))
        canvas.restoreState()

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(colors.HexColor("#F8FAFD"))
        c.setStrokeColor(LINE)
        c.roundRect(0, 0, self.width, self.height, 12, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(18, self.height - 25, "Architecture at a glance")
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7.3)
        c.drawString(18, self.height - 38, "Client requests flow through the API and orchestration engine to local AI, tools, storage, and delivery surfaces.")

        # Entry and delivery tier
        self._box(c, 22, 212, 124, 44, "Web client", "Next.js / React", CYAN)
        self._box(c, 207, 212, 126, 44, "Application API", "FastAPI + SSE", BLUE)
        self._box(c, 394, 212, 124, 44, "Delivery surfaces", "Chat, workflows, artifacts", CYAN)
        self._arrow(c, 146, 234, 207, 234)
        self._arrow(c, 333, 234, 394, 234)

        # Orchestration tier
        self._box(c, 116, 133, 308, 48, "LangGraph orchestration core", "State graph, dynamic routing, approvals, checkpoints, repair loop", colors.HexColor("#7957C5"))
        self._arrow(c, 270, 212, 270, 181)

        # Agents
        agent_y, agent_w, agent_h = 67, 87, 43
        labels = [
            ("Planner", "task plan", "#C69500"),
            ("Researcher", "RAG context", "#1687A7"),
            ("Coder", "artifacts", "#7957C5"),
            ("Tester", "test design", "#E07B1F"),
            ("Reviewer", "assessment", "#2B9B68"),
        ]
        xs = [18, 124, 230, 336, 442]
        for x, (name, desc, color) in zip(xs, labels):
            self._box(c, x, agent_y, agent_w, agent_h, name, desc, colors.HexColor(color))
        for x in [105, 211, 317, 423]:
            self._arrow(c, x, agent_y + 22, x + 19, agent_y + 22)
        self._arrow(c, 270, 133, 270, 110)

        # Supporting components
        self._box(c, 18, 14, 124, 34, "MCP tool layer", "tools and integrations", colors.HexColor("#4F7CAC"))
        self._box(c, 160, 14, 110, 34, "Ollama", "local AI models", colors.HexColor("#D35F85"))
        self._box(c, 288, 14, 110, 34, "Knowledge", "Chroma vectors", colors.HexColor("#1687A7"))
        self._box(c, 416, 14, 106, 34, "Persistence", "Postgres / Redis", colors.HexColor("#4F7CAC"))
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawCentredString(270, 53, "Agent execution is supported by these shared platform services")
        c.restoreState()


def paragraph(text, style):
    return Paragraph(text, style)


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 28, letter[0] - doc.rightMargin, 28)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(doc.leftMargin, 17, "MultiAgent OS - Project Overview")
    canvas.drawRightString(letter[0] - doc.rightMargin, 17, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter, leftMargin=36, rightMargin=36, topMargin=38, bottomMargin=42)
    base = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=NAVY, spaceAfter=4)
    subtitle = ParagraphStyle("subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=BLUE, spaceAfter=12)
    h1 = ParagraphStyle("h1", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=12, spaceAfter=6, keepWithNext=True)
    h2 = ParagraphStyle("h2", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=9.3, leading=12, textColor=BLUE, spaceBefore=7, spaceAfter=3, keepWithNext=True)
    body = ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.8, leading=12.3, textColor=INK, spaceAfter=5)
    small = ParagraphStyle("small", parent=body, fontSize=7.8, leading=10.2, textColor=INK)
    th = ParagraphStyle("th", parent=small, fontName="Helvetica-Bold", textColor=colors.white, leading=10)
    td = ParagraphStyle("td", parent=small, leading=10.5)
    tdb = ParagraphStyle("tdb", parent=td, fontName="Helvetica-Bold", textColor=NAVY)

    story = [
        paragraph("MultiAgent OS", title),
        paragraph("Overall project summary and architecture", subtitle),
        HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=8),
        paragraph("Purpose", h1),
        paragraph("MultiAgent OS is a full-stack AI orchestration platform for taking a user request from conversation to a coordinated, multi-step software-workflow outcome. It combines a web application, an asynchronous API, local large-language-model inference, a LangGraph execution engine, knowledge retrieval, tool integrations, isolated workspaces, and persistent operational data.", body),
        paragraph("The product supports two interaction patterns: concise assistant-style exchanges and richer workflow runs that coordinate specialist agents. During workflow runs, the platform can stream events to the browser, preserve execution context, route work between agents, create artifacts, and expose the resulting workspace through dedicated interfaces.", body),
        paragraph("System architecture", h1),
        ArchitectureDiagram(),
        Spacer(1, 8),
        paragraph("The browser-facing Next.js application presents dashboards, chat, workflow management, workspaces, knowledge, tools, analytics, governance, and operations views. Its service modules call FastAPI endpoints, while Server-Sent Events carry incremental workflow activity back to the UI.", body),
        paragraph("Core execution flow", h1),
    ]

    flow = [
        [paragraph("Stage", th), paragraph("Responsibility", th), paragraph("Primary output", th)],
        [paragraph("Planner", tdb), paragraph("Interprets the request, creates an execution plan, and determines the agent sequence.", td), paragraph("Plan and required-agent list", td)],
        [paragraph("Researcher", tdb), paragraph("Builds context from the knowledge layer and approved tools.", td), paragraph("Research notes", td)],
        [paragraph("Coder", tdb), paragraph("Creates or revises source artifacts in an isolated workspace.", td), paragraph("Generated code and files", td)],
        [paragraph("Tester", tdb), paragraph("Produces tests and coverage-oriented analysis for generated work.", td), paragraph("Test artifacts and analysis", td)],
        [paragraph("Quality gate", tdb), paragraph("Runs deterministic validation over the workspace, including syntax/import checks, Ruff, pytest, and Bandit.", td), paragraph("Validation evidence", td)],
        [paragraph("Reviewer", tdb), paragraph("Uses the workflow context and validation results to provide a qualitative assessment.", td), paragraph("Review output", td)],
    ]
    table = Table(flow, colWidths=[1.1 * inch, 3.65 * inch, 2.25 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([table, paragraph("Major project components", h1)])

    components = [
        ("Frontend application", "Next.js 16, React 19, TypeScript, TanStack React Query, Axios, Tailwind CSS, Three.js, and Lucide. The App Router organizes public pages and the authenticated application shell; components and hooks support chat, system diagnostics, workflow visualisation, navigation, and status-aware UX."),
        ("Backend API and services", "FastAPI provides REST and streaming interfaces. Route modules cover chat, agents, workflows, workflow builder, workspaces, artifacts, knowledge, tools, analytics, operations, tenants, authentication, prompts, health, and AIOps. Service and repository layers keep business rules, storage access, scheduling, and artifact management separate from endpoint handlers."),
        ("Orchestration and agents", "LangGraph supplies a shared-state execution graph. The planner, researcher, coder, tester, and reviewer are specialized agent modules. Dynamic routing can reduce or expand the selected path; for build-oriented work it enforces the core sequence. A failed validation result can feed a bounded repair loop back to the coder."),
        ("AI and knowledge", "Ollama is the local model provider. The knowledge pipeline accepts documents, chunks content, generates embeddings, stores vectors in ChromaDB, and retrieves relevant context for planning and research. Planning memory provides an additional vector-backed context surface."),
        ("Tools and workspaces", "The Model Context Protocol implementation registers filesystem, PostgreSQL, GitHub, HTTP, and terminal tools. Workspace services isolate generated files by session, track metadata, and support artifact extraction and delivery."),
        ("Persistence and background work", "PostgreSQL is accessed with asynchronous SQLAlchemy and migrated with Alembic. Redis serves Celery broker/result-backend needs; workers and scheduled jobs separate long-running workflow, indexing, analytics, and tool work from interactive API handling."),
        ("Security and governance", "Authentication, rate limiting, structured exception handling, DLP masking, and prompt-security checks live in dedicated backend modules. The application also includes tenant, workspace, operations, analytics, and AIOps domains for governed use of the platform."),
    ]
    for name, text in components:
        story.extend([paragraph(name, h2), paragraph(text, body)])

    story.extend([
        paragraph("Deployment topology", h1),
        paragraph("The repository includes Docker Compose definitions for PostgreSQL, Redis, the FastAPI backend, Celery worker, Celery Beat scheduler, the Next.js frontend, and Nginx. The backend reaches Ollama through a configurable base URL, supporting a local model runtime while the remainder of the application runs as coordinated services.", body),
        paragraph("Repository map", h1),
    ])
    repo = [
        [paragraph("Area", th), paragraph("What it contains", th)],
        [paragraph("backend/app", tdb), paragraph("FastAPI application, agents, orchestration graph, API routes, services, repositories, schemas, models, security, knowledge, MCP server, and workers.", td)],
        [paragraph("backend/tests", tdb), paragraph("Backend tests covering workflow behavior, quality-gate rules, workspace handling, routing, authentication, embeddings, chat, and artifact extraction.", td)],
        [paragraph("frontend/app", tdb), paragraph("Next.js routes for public pages, dashboard, chat, workflows, workspace, knowledge, tools, analytics, governance, settings, and AIOps.", td)],
        [paragraph("frontend/components, hooks, services", tdb), paragraph("Reusable UI, client-side interaction logic, and typed API service modules.", td)],
        [paragraph("docker-compose.yml and nginx", tdb), paragraph("Containerized service topology and reverse-proxy configuration.", td)],
    ]
    repo_table = Table(repo, colWidths=[1.8 * inch, 5.2 * inch], repeatRows=1)
    repo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(repo_table)
    story.extend([
        paragraph("Operating model", h1),
        paragraph("A request enters through the web client and is handled by the FastAPI application. For a workflow request, the orchestration engine carries a shared state object through the selected agents, records checkpoints, and streams progress to the browser. The application can pause at configured approval points and resume from the persisted workflow context.", body),
        paragraph("Generated work is placed in a session-scoped workspace. The deterministic quality gate reads that workspace and returns validation evidence to the graph; the reviewer receives the generated output, testing context, research notes, and validation results. Persistent relational records support chat, workflows, agent executions, artifacts, knowledge metadata, tenants, and metrics.", body),
        paragraph("Service boundaries", h2),
        paragraph("Interactive API traffic, background jobs, vector retrieval, model inference, file workspaces, and database persistence are kept in separate modules and services. This separation lets the UI stay responsive while workflows, indexing, analytics, and tool execution operate through their respective workers and integrations.", body),
    ])

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
