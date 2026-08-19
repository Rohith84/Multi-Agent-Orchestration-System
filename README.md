# MultiAgent OS — AI Orchestration System

<div align="center">

![MultiAgent OS](https://img.shields.io/badge/MultiAgent-OS-DFFF00?style=for-the-badge&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16.2-000000?style=for-the-badge&logo=next.js&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-6A0DAD?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-FF6B35?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)

**An enterprise-grade AI Agent Orchestration Platform running fully locally on your machine — no cloud API keys required.**

</div>

---

## What is MultiAgent OS?

MultiAgent OS is a full-stack AI orchestration system that coordinates **5 specialized AI agents** to plan, research, write, test, and review code autonomously. It runs entirely on local LLMs via **Ollama** (supports GPU acceleration) and is managed through a polished Neo-Brutalist enterprise web interface.

You describe a task. The system breaks it down, assigns it across specialized agents, generates production-quality code with tests, and delivers a reviewed result — all with real-time streaming output and optional **human approval gates**.

---

## Architecture Overview

```
                         MULTIAGENT OS
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
   AI ASSISTANT (Ask Mode)          WORKFLOW ENGINE (Build Mode)
   Single LLM call — fast           5-Agent LangGraph pipeline
   explanations & advice            Full code generation cycle
            │                                     │
            └──────────────────┬──────────────────┘
                               │
                    SUPERVISOR ORCHESTRATION CORE
                      (LangGraph State Machine)
                               │
        ┌──────────┬───────────┼───────────┬──────────┐
        │          │           │           │          │
   01 PLANNER  02 RESEARCHER  03 CODER  04 TESTER  05 REVIEWER
```

### The 5 AI Execution Agents

| # | Agent | Color | Role |
|---|-------|-------|------|
| 01 | **PLANNER** | 🟡 Lime | Decomposes tasks into structured execution plans |
| 02 | **RESEARCHER** | 🔵 Cyan | Knowledge retrieval, RAG search, web research |
| 03 | **CODER** | 🟣 Purple | Code synthesis, file generation, refactoring |
| 04 | **TESTER** | 🟠 Amber | Test suite generation and automated pytest execution |
| 05 | **REVIEWER** | 🟢 Green | Code quality review, static analysis, security audit |

### Platform Core Layers

- **Supervisor Core** — LangGraph state machine managing agent routing, checkpoints, and human approval gates
- **Memory / Knowledge** — ChromaDB vector store with `nomic-embed-text` embeddings for RAG retrieval
- **Workspace Engine** — Isolated `sandbox_workspace/<session_id>/` per workflow, tracked in PostgreSQL
- **MCP Tools** — Model Context Protocol tool integrations

---

## Features

### 🤖 Dual Chat Modes
- **Ask Mode** — Single fast LLM call using the explain model. Returns concise, direct answers without running the full pipeline. Ideal for questions and explanations.
- **Build Mode** — Triggers the full 5-agent LangGraph workflow for code generation tasks. Streams agent execution events in real-time.

### 🔀 Human-in-the-Loop Approval Gates
- Select which agents require human approval before proceeding (Coder, Tester, Reviewer)
- Workflow pauses, notifies you, and waits for **Approve** or **Reject**
- Checkpoints are saved to PostgreSQL so nothing is lost on rejection

### 💾 Session Persistence
- Active session ID is persisted in `localStorage` and the URL (`/app/chat?session=<uuid>`)
- Reloading or navigating away and returning automatically restores the conversation
- Interrupted workflows are still recoverable after page refresh

### ⚡ GPU/CPU Runtime Diagnostics
- Live **Ollama Runtime** status badge in the chat header (GPU / CPU / CPU-GPU)
- `GET /api/ollama/runtime` endpoint queries Ollama's `/api/ps` for loaded models, VRAM usage, and processor classification
- Accurate — reports `"unknown"` rather than guessing when data is unavailable

### 📊 Real-Time Streaming
- SSE (Server-Sent Events) stream with typed events: `workflow_started`, `agent_start`, `agent_end`, `workflow_complete`, `workflow_paused_approval`, `workflow_failed`
- Agent execution timeline inspector updates live in the browser as each agent completes
- Only the final workflow answer appears in the chat transcript — no raw intermediate agent logs

### 🏗️ Visual Workflow Builder
- 3-panel graph canvas to design custom agent pipelines
- Supports 1-to-5 agent subset topologies
- Real-time graph validation and template saving

### 📁 Workspace Studio
- Generated files and artifacts persisted per session under `backend/sandbox_workspace/<session_id>/`
- Tracked in the PostgreSQL `workspace_files` table with full metadata
- Browse, view, and download from `/app/workspace`

---

## Application Routes

| Route | Name | Description |
|-------|------|-------------|
| `/` | Landing Page | Platform overview, 3D visualizer, live metrics |
| `/app` | Command Center | Dashboard with system status, recent workflows, quick run |
| `/app/chat` | AI Assistant | Ask Mode + Build Mode chat with agent execution timeline |
| `/app/agents` | Agent Control | Per-agent execution cards, model config, prompt overrides |
| `/app/workflows` | Workflow Manager | Table of all workflow runs, status filter, run/schedule modals |
| `/app/workflows/[id]` | Execution Center | Live SSE stream, human approval gate, checkpoint inspector |
| `/app/workflow-builder` | Visual Builder | Graph canvas for custom pipeline design |
| `/app/workspace` | Workspace Studio | Generated files browser and artifact downloader |
| `/app/knowledge` | Knowledge Base | Document upload and RAG knowledge management |
| `/app/tools` | MCP Tools | Model Context Protocol tool registry |

---

## Tech Stack

### Backend (`/backend`)
| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (Python 3.13) |
| Agent Orchestration | LangGraph 0.2 |
| LLM Integration | Ollama (local, GPU-accelerated) |
| Database | PostgreSQL 15 + async SQLAlchemy |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Vector Store | ChromaDB + nomic-embed-text |
| Security | python-jose JWT, passlib, bcrypt |
| HTTP Client | httpx (async) |
| Testing | pytest-asyncio, httpx ASGI |

### Frontend (`/frontend`)
| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16.2 (App Router, React 19) |
| Language | TypeScript 5.0+ |
| Styling | Neo-Brutalist Design System (Vanilla CSS + Tailwind v4) |
| State Management | TanStack React Query v5 |
| HTTP Client | Axios |
| 3D Visualizer | Three.js |
| Icons | Lucide React |

---

## Getting Started

### Prerequisites
- **Python** 3.11+
- **Node.js** 18+
- **PostgreSQL** 15+
- **Ollama** — [Install from ollama.ai](https://ollama.ai)

### 1. Install Ollama Models

```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

> **GPU Tip**: Ollama automatically uses your NVIDIA GPU if drivers and VRAM allow. Check status with `ollama ps`. For best performance on a 6GB VRAM GPU, use `deepseek-coder:6.7b` (3.8GB).

### 2. Database Setup

```sql
CREATE DATABASE multi_agent_db;
```

### 3. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `/backend`:
```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/multi_agent_db

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=qwen2.5-coder:7b
MODEL_EXPLAIN=deepseek-coder:6.7b
MODEL_PLANNER=deepseek-coder:6.7b
MODEL_RESEARCH=deepseek-coder:6.7b
MODEL_CODER=qwen2.5-coder:7b
MODEL_TESTER=qwen2.5-coder:7b
MODEL_REVIEWER=deepseek-coder:6.7b
```

Start the backend server:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Application available at: `http://localhost:3000`

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Backend liveness check |
| `GET` | `/api/system-status` | Aggregated health: FastAPI, DB, Ollama |
| `GET` | `/api/ollama/runtime` | Live GPU/CPU runtime status from Ollama `/api/ps` |
| `POST` | `/api/chat` | Single-LLM Ask Mode chat with session history |
| `POST` | `/api/agents/chat` | Multi-agent Build Mode SSE stream |
| `GET` | `/api/workflows` | List all workflow runs |
| `GET` | `/api/workflows/{id}` | Workflow details, checkpoints, approvals |
| `POST` | `/api/workflows/chat` | Start a new workflow execution |
| `POST` | `/api/workflows/{id}/approve` | Approve a human approval gate |
| `POST` | `/api/workflows/{id}/reject` | Reject a human approval gate |
| `POST` | `/api/workflows/{id}/resume` | Resume a paused workflow |
| `POST` | `/api/workflows/schedule` | Schedule a recurring cron workflow |
| `GET` | `/api/workflows/templates` | List saved workflow templates |
| `POST` | `/api/workflows/templates` | Save a custom workflow template |

---

## Project Structure

```
Multi Agent/
├── backend/
│   ├── app/
│   │   ├── agents/          # Planner, Researcher, Coder, Tester, Reviewer
│   │   ├── ai/              # OllamaClient with GPU/CPU runtime diagnostics
│   │   ├── api/             # FastAPI route handlers
│   │   ├── core/            # Config, auth, logging, exceptions
│   │   ├── db/              # Async SQLAlchemy engine setup
│   │   ├── knowledge/       # ChromaDB vector store, RAG retrieval
│   │   ├── mcp/             # Model Context Protocol tool integrations
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── orchestration/   # LangGraph workflow executor and state graph
│   │   ├── repositories/    # DB query layer (workflows, chat, workspace)
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   ├── security/        # DLP scanners, prompt injection detection
│   │   ├── services/        # Business logic (chat, workspace, scheduler)
│   │   └── worker/          # Background task workers
│   ├── tests/               # pytest-asyncio integration tests
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # Reusable UI components
│   ├── hooks/               # React hooks (use-chat, use-system-status)
│   ├── lib/                 # Axios API client
│   └── services/            # API service modules
├── .gitignore
└── README.md
```

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

Key test files:
- `tests/test_phase1.py` — Human approval gates, checkpoint resume, workspace isolation
- `tests/test_chat_features.py` — Ask/Build modes, `workflow_started` SSE event, Ollama runtime endpoint

---

## Roadmap

- [x] Phase 1 — 5-Agent LangGraph execution engine, human approval gates, session checkpoints
- [x] Phase 1 — Chat experience overhaul: Ask vs Build modes, session persistence, GPU/CPU diagnostics
- [ ] Phase 2 — Security hardening: JWT enforcement, DLP scanning, prompt injection protection
- [ ] Phase 3 — Knowledge Base Studio: document upload, RAG pipeline UI
- [ ] Phase 4 — MCP Tool Registry: integrations with GitHub, browser, terminal
- [ ] Phase 5 — Analytics & LLMOps: agent latency, token usage, cost tracking
- [ ] Phase 6 — Docker deployment: single `docker-compose up` for full stack
- [ ] Phase 7 — Multi-tenancy: team workspaces, RBAC, audit logs

---

## License

Proprietary. All rights reserved © 2026 Rohith.
