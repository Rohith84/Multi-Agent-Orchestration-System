# 🤖 Multi-Agent Orchestration System

[![Next.js](https://img.shields.io/badge/Next.js-15.0-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Proprietary-blue?style=for-the-badge)]()

A high-performance, full-stack **Multi-Agent Orchestration Platform** built with **Next.js 15 (App Router)** on the frontend and **FastAPI** on the backend. Designed for AI-powered autonomous agents capable of collaborative planning, web research, code synthesis, automated testing, and code review — orchestrated seamlessly using **LangGraph**.

---

## 📌 Current Milestone Status

> **Milestone 1: Foundation Complete**
> - ✨ Next.js 15 frontend dashboard with dark mode UI components (shadcn/ui & Tailwind CSS).
> - ⚡ FastAPI asynchronous backend with Pydantic settings and route modules.
> - 🗄️ PostgreSQL database connection configured via async SQLAlchemy & Alembic migrations.
> - 🤖 Ollama local LLM integration setup and status monitoring.
> - 📡 Real-time system health checks & aggregated subsystem status API.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Client                        │
│                 Next.js 15 (App Router)                     │
│                       (Port 3000)                           │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼──────────────────────────────┐
│                      FastAPI Backend                        │
│                       (Port 8000)                           │
│  ┌───────────────────┬───────────────────┬───────────────┐  │
│  │   Health Check    │    LangGraph      │   Database    │  │
│  │    Endpoints      │  Orchestration    │   Manager     │  │
│  └───────────────────┴───────────────────┴───────────────┘  │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
┌───────────────▼─────────────┐ ┌─────────────▼──────────────┐
│     PostgreSQL Database     │ │         Ollama LLM          │
│         (Port 5432)         │ │        (Port 11434)         │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 🛠️ Tech Stack & Technologies

### Frontend
- **Framework:** Next.js 15 (React 19 / App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS, shadcn/ui components, Lucide icons
- **State & Data Fetching:** TanStack React Query v5, Axios

### Backend
- **Framework:** FastAPI (Python 3.12+)
- **ORM & Migrations:** Async SQLAlchemy, Alembic
- **Validation:** Pydantic v2 & Pydantic Settings
- **Server:** Uvicorn ASGI Server
- **Linting & Formatting:** Ruff

### Infrastructure & External Services
- **Database:** PostgreSQL 15+
- **Local AI Engine:** Ollama (qwen, llama3, deepseek, etc.)
- **Agent Orchestration:** LangGraph (upcoming milestones)

---

## 📋 Requirements & Prerequisites

Before setting up the project, make sure you have the following installed:

| Tool | Recommended Version | Purpose |
| :--- | :--- | :--- |
| **Node.js** | `v18.x` or higher | Frontend runtime environment |
| **npm** | `v9.x` or higher | Package manager |
| **Python** | `3.12+` | Backend runtime environment |
| **PostgreSQL** | `15.0+` | Relational database engine |
| **Git** | `2.40+` | Distributed version control |
| **Ollama** | Latest | Local LLM hosting (Optional) |

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Rohith84/Multi-Agent-Orchestration-System.git
cd Multi-Agent-Orchestration-System
```

### 2. Database Initialization

Connect to your local PostgreSQL instance and create the database:

```sql
CREATE DATABASE multi_agent_db;
```

---

### 3. Backend Setup

```bash
cd backend

# 1. Create a Python virtual environment
python -m venv venv

# 2. Activate the virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# 3. Install required Python packages
pip install -r requirements.txt

# 4. Configure Environment Variables
cp .env.example .env
# Open .env and adjust DATABASE_URL, OLLAMA_BASE_URL if necessary

# 5. Run Database Migrations (Optional/Initial)
alembic upgrade head
```

---

### 4. Frontend Setup

```bash
cd ../frontend

# Install Node modules
npm install
```

---

## ▶️ Running the Application

### 1. Start the Backend API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
- **Backend API:** `http://localhost:8000`
- **Interactive API Docs (Swagger):** `http://localhost:8000/docs`
- **ReDoc Documentation:** `http://localhost:8000/redoc`

### 2. Start the Frontend Application

```bash
cd frontend
npm run dev
```
- **Dashboard Interface:** `http://localhost:3000`

---

## 📁 Project Directory Structure

```
Multi-Agent-Orchestration-System/
├── backend/                     # FastAPI Application
│   ├── alembic/                 # Database migration scripts & configuration
│   ├── app/
│   │   ├── api/                 # API Endpoint routes (health, system status)
│   │   ├── core/                # Application configuration & Pydantic settings
│   │   ├── db/                  # Async database engine & session handlers
│   │   ├── models/              # SQLAlchemy database models
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── services/            # Core business & orchestration logic
│   │   ├── utils/               # Helper functions
│   │   └── main.py              # FastAPI application entry point
│   ├── .env.example             # Backend environment template
│   ├── alembic.ini              # Alembic config
│   ├── requirements.txt         # Backend Python dependencies
│   └── ruff.toml                # Ruff linter configuration
│
├── frontend/                    # Next.js 15 Web Client
│   ├── app/                     # Next.js App Router (pages, layout, globals)
│   │   ├── globals.css          # Theme definitions & global styles
│   │   ├── layout.tsx           # Root layout component
│   │   ├── page.tsx             # Main System Dashboard
│   │   └── providers.tsx        # React Query & Provider wrappers
│   ├── components/              # Reusable UI Components
│   │   ├── ui/                  # Base shadcn/ui components (card, badge, button)
│   │   ├── dashboard-header.tsx # Top navigation / title header
│   │   └── status-card.tsx      # System status monitor card
│   ├── hooks/                   # React Hooks (useHealth, useSystemStatus)
│   ├── lib/                     # Axios instance & utility functions
│   ├── services/                # API client layer (health-service)
│   ├── package.json             # Frontend dependencies & scripts
│   └── tsconfig.json            # TypeScript configuration
│
├── .gitignore                   # Workspace gitignore rule set
└── README.md                    # Project documentation
```

---

## 🔌 Core API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Basic liveness check for backend readiness. |
| `GET` | `/api/system-status` | Aggregated health check for Database & Ollama. |

#### Sample Health Response (`GET /api/system-status`)
```json
{
  "status": "healthy",
  "components": {
    "backend": "connected",
    "database": "connected",
    "ollama": "connected"
  },
  "timestamp": "2026-07-28T10:57:00Z"
}
```

---

## 🧹 Code Quality & Formatting

### Backend (Python)
```bash
cd backend
ruff check .      # Run Linter
ruff format .     # Run Code Formatter
```

### Frontend (TypeScript / React)
```bash
cd frontend
npm run lint      # Run ESLint
npx prettier --write .  # Format code
```

---

## 🛣️ Roadmap & Planned Agent Milestones

| Milestone | Target Feature | Description |
| :---: | :--- | :--- |
| ✅ **M1** | **Foundation** | Project setup, DB connection, status APIs, UI layout |
| 🔲 **M2** | **Planner Agent** | Task decomposition & graph execution with LangGraph |
| 🔲 **M3** | **Research Agent** | Web scraping, vector search & RAG with ChromaDB |
| 🔲 **M4** | **Coding Agent** | File system operations, code generation & refactoring |
| 🔲 **M5** | **Testing Agent** | Automated test creation and terminal test execution |
| 🔲 **M6** | **Reviewer Agent** | Code review, security auditing, and performance analysis |
| 🔲 **M7** | **Memory & Context** | Long-term vector memory & conversation history |
| 🔲 **M8** | **Containerization** | Docker Compose orchestration for full stack |

---

## 📝 License

This repository is proprietary. All rights reserved.
