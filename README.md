# 🤖 MULTIAGENT OS — Enterprise Multi-Agent AI Orchestration System

[![Next.js](https://img.shields.io/badge/Next.js-16.2-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Three.js](https://img.shields.io/badge/Three.js-3D_Visualizer-black?style=for-the-badge&logo=three.js)](https://threejs.org/)

**MULTIAGENT OS** is an enterprise-grade Multi-Agent AI Orchestration Platform built with a **Next.js 16 (App Router)** neo-brutalist frontend and a high-performance **FastAPI** backend. It coordinates autonomous AI agents across complex software development, research, coding, automated testing, and security code reviews — orchestrated seamlessly via **LangGraph** with real-time SSE event streaming and checkpoint observability.

---

## 📌 Milestone Status (Tasks 1–4.1 Complete)

> **Current Status: Multi-Page Enterprise Application Shell & Visual Workflow Builder Live**
> - 🎨 **Task 1**: Neo-Brutalist visual design language system, theme manager (Dark/Light mode), and Three.js 3D Orchestration Visualizer core.
> - 🤖 **Task 2**: Architecture correction to **exactly 5 AI Execution Agents** (`Planner`, `Researcher`, `Coder`, `Tester`, `Reviewer`), `Supervisor` as Orchestration Core, `Memory` as Platform RAG capability, and `/app/*` enterprise application shell.
> - ⚡ **Task 3**: Workflow Management Center (`/app/workflows`), Real-Time Execution Center (`/app/workflows/[id]`), `fetch` + `ReadableStream` POST-based SSE stream decoder, human approval gates, and data-driven checkpoint inspectors.
> - 🛠️ **Task 4 & 4.1**: Visual Workflow Builder (`/app/workflow-builder`), 3-panel graph canvas environment, 1-to-5 agent subset pipeline topologies, real-time graph validation engine, template saving (`POST /api/workflows/templates`), and execution handoffs.

---

## 🧠 System Architecture & Agent Model

### 1. Exactly 5 AI Execution Agents
| Agent ID | Name | Brand Color | Function / Purpose |
| :---: | :--- | :---: | :--- |
| **01** | **PLANNER** | `#DFFF00` (Lime) | Task decomposition, dependency mapping, and structured plan generation. |
| **02** | **RESEARCHER** | `#22D3EE` (Cyan) | Web research, documentation indexing, vector retrieval & RAG search. |
| **03** | **CODER** | `#8B5CF6` (Purple) | Typed code synthesis, file system operations, and architectural refactoring. |
| **04** | **TESTER** | `#FBBF24` (Amber) | Test suite generation, automated pytest execution, and assertion verification. |
| **05** | **REVIEWER** | `#4ADE80` (Green) | Code quality review, static analysis, security auditing, and quality gate decisions. |

### 2. Platform Core Layers (Not AI Agents)
- **SUPERVISOR CORE**: The central Orchestration & Control Layer coordinating graph state transitions, branch routing, and human approval gates.
- **MEMORY / KNOWLEDGE CAPABILITY**: Vector RAG store & conversation context layer providing persistent document retrieval.

```text
                               MULTIAGENT OS
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
            WORKFLOW BUILDER                WORKFLOW EXECUTION
          /app/workflow-builder             /app/workflows/[id]
                     │                               │
           Create / Edit / Save             Real-Time SSE Stream
                     │                               │
                     └───────────────┬───────────────┘
                                     ▼
                          SUPERVISOR ORCHESTRATION CORE
                                     │
         ┌──────────────────┬────────┴─────────┬──────────────────┐
         ▼                  ▼                  ▼                  ▼
   01 PLANNER         02 RESEARCHER        03 CODER           04 TESTER          05 REVIEWER
```

---

## 🌐 Application Routes & Modules

| Route | View Name | Description |
| :--- | :--- | :--- |
| `/` | **Public Platform Landing** | Hero section, live 3D visualizer canvas, architectural overview, live performance metrics. |
| `/app` | **Command Center Dashboard** | Aggregated workspace metrics, system status pulse, recent workflow executions, quick run prompt. |
| `/app/agents` | **Agent Control Center** | Execution cards for all 5 agents, prompt overrides, tool assignments, and dynamic model status. |
| `/app/workflows` | **Workflow Management** | Table of backend workflows, real-time search, status filters, workflow trigger & schedule modals. |
| `/app/workflows/[id]` | **Execution Center** | Live execution graph, real-time event stream, human approval gate banner, and checkpoint state inspector. |
| `/app/workflow-builder` | **Visual Workflow Builder** | 3-Panel graph builder, node library, blueprint canvas, properties panel, topology validator, save & run handoff. |

---

## 🛠️ Tech Stack & Dependencies

### Frontend (`/frontend`)
- **Framework:** Next.js 16.2 (React 19 / App Router)
- **Language:** TypeScript 5.0+
- **Styling:** Neo-Brutalist design tokens (`globals.css`), Tailwind CSS v4, Lucide React icons
- **3D Graphics:** Vanilla Three.js (`/components/visualizer/three-visualizer.tsx`)
- **Data & APIs:** Axios, TanStack React Query v5

### Backend (`/backend`)
- **Framework:** FastAPI (Python 3.12+)
- **Orchestration:** LangGraph dynamic graph execution engine
- **ORM & Database:** Async SQLAlchemy, PostgreSQL 15+, Alembic migrations
- **Validation:** Pydantic v2 with custom UUID-to-string serializers
- **LLM Integration:** Ollama (qwen2.5-coder, llama3.1)

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js**: `v18.x` or higher
- **Python**: `3.12+`
- **PostgreSQL**: `15.0+`
- **Ollama**: (Optional for local LLM execution)

### 2. Database Setup
```sql
CREATE DATABASE multi_agent_db;
```

### 3. Backend Quickstart
```bash
cd backend
python -m venv venv

# Activate Virtual Environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python -m uvicorn app.main:app --reload --port 8000
```
- API Swagger Docs: `http://localhost:8000/docs`

### 4. Frontend Quickstart
```bash
cd frontend
npm install
npm run dev
```
- App Client: `http://localhost:3000`

---

## 🔌 Core API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Backend liveness and system health check. |
| `GET` | `/api/system-status` | Aggregated health for FastAPI, Database, and Ollama. |
| `GET` | `/api/workflows` | List workflows with pagination and status filters. |
| `GET` | `/api/workflows/{id}` | Fetch workflow execution details, checkpoints, and approvals. |
| `POST` | `/api/workflows/chat` | Start a streaming workflow execution (`StreamingResponse`). |
| `POST` | `/api/workflows/{id}/approve` | Approve a paused human-in-the-loop approval gate. |
| `POST` | `/api/workflows/{id}/reject` | Reject a paused approval gate. |
| `POST` | `/api/workflows/{id}/resume` | Resume execution of a paused workflow. |
| `POST` | `/api/workflows/schedule` | Schedule a recurring workflow execution cron task. |
| `GET` | `/api/workflows/templates` | List saved preset and custom workflow templates. |
| `POST` | `/api/workflows/templates` | Save a new visual workflow template definition. |
| `POST` | `/api/workflows/builder/{id}/simulate` | Dry-run graph simulation returning execution order. |

---

## 🛣️ System Roadmap

- [x] **Task 1**: Visual Design System, Themes & 3D Control Center Visualizer
- [x] **Task 2**: 5 AI Agent Architecture, Supervisor Core & `/app/*` Shell
- [x] **Task 3**: Workflow Management Center & Real-Time Execution Center (`/app/workflows`, `/app/workflows/[id]`)
- [x] **Task 4 & 4.1**: Visual Workflow Builder (`/app/workflow-builder`) with Subset Pipeline Topologies
- [ ] **Task 5**: Enterprise Knowledge Base & Vector RAG Studio (`/app/knowledge`)
- [ ] **Task 6**: MCP Tools & Integration Registry (`/app/tools`)
- [ ] **Task 7**: Workspace Studio & File Artifact Engine (`/app/workspace`, `/app/artifacts`)
- [ ] **Task 8**: Analytics, LLMOps & Observability Dashboard (`/app/analytics`)

---

## 📝 License

Proprietary enterprise software. All rights reserved.
