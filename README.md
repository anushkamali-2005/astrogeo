# 🚀 AstroGeo AI - Enterprise MLOps Platform

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Production-ready MLOps platform combining Agentic AI, Geospatial Analytics, and Modern ML Infrastructure.**

---

## 📖 Welcome to AstroGeo AI!

Hi there! If you're new to this project, here's the "elevator pitch": AstroGeo AI is a sophisticated backend platform designed to handle complex tasks that involve **Location Data (Geospatial)** and **Artificial Intelligence**. 

Imagine needing to analyze satellite imagery, predict weather patterns for specific coordinates, and then have an AI "agent" write a report about it—that's what this system is built to orchestrate.

---

## 📋 Table of Contents
- [✨ Key Features](#-key-features)
- [🚦 Current Project Status](#-current-project-status)
- [✅ What's Already Done](#-whats-already-done)
- [🚧 What's Still Remaining](#-whats-still-remaining)
- [🏗️ Architecture](#-architecture)
- [📂 Project Structure](#-project-structure)
- [🚀 Quick Start (For Developers)](#-quick-start-for-developers)

---

## ✨ Key Features

- 🤖 **Agentic AI**: Multi-agent system (Data, Geo, and ML agents) that can decompose complex user requests into smaller tasks.
- 🌍 **Geospatial Intelligence**: Built-in support for PostGIS, allowing for advanced spatial queries (finding things within a radius, calculating distances, etc.).
- 🔬 **MLOps Excellence**: Integrated with MLflow for experiment tracking and DVC for data versioning.
- ⚡ **High Performance**: Built with FastAPI for asynchronous, non-blocking API endpoints.
- 🚢 **Cloud Ready**: Complete Kubernetes (EKS) manifests and Docker support for production deployment.

---

## 🚦 Current Project Status

**Status**: 🏗️ **Functional Backend Prototype**

The project has a very solid architectural foundation. All the "plumbing" (database connections, API routes, authentication, agent orchestration logic) is **complete**. 

The system is currently in a state where it can be demonstrated using "mock" (simulated) data for the AI agents, while the core infrastructure is fully production-grade.

---

## ✅ What's Already Done

We have successfully implemented the following core components:

### 1. 💾 Database Layer (100% Complete)
- **Advanced Models**: Support for Users, Geospatial Locations (PostGIS), ML Models, Predictions, and Agent Execution logs.
- **Async Connections**: High-performance asynchronous database management using SQLAlchemy and `asyncpg`.
- **Migrations**: Fully set up with Alembic for easy database schema updates.

### 2. 🔌 API Layer & Security
- **Comprehensive Routes**: Endpoints for Agent execution, System Health monitoring, and Administrative tasks.
- **JWT Authentication**: Secure user login and role-based access control (Admin vs. Regular User).
- **Auto-Docs**: Interactive Swagger/OpenAPI documentation is automatically generated.

### 3. 🧠 AI Orchestration
- **The Brain**: An `AgentOrchestrator` that knows how to pick the right "agent" for a job.
- **Task Decomposition**: Ability to break one big request into multiple steps for Data, ML, and Geo agents.

---

## 🚧 What's Still Remaining

To move from a prototype to a full production system, the following tasks are on the roadmap:

1. **Replace Mock Logic**: The "Data", "Geo", and "ML" agents currently return simulated data. We need to plug in real logic:
    - **DataAgent**: Integrate real Pandas/SQL processing.
    - **GeoAgent**: Integrate real `geopy` and `geopandas` calculations.
    - **MLAgent**: Connect to real Scikit-learn/TensorFlow training scripts.
2. **Frontend UI**: Currently, the project is purely a backend API. A dashboard for interacting with agents and viewing predictions is needed.
3. **Data Population**: Filling the geospatial database with more real-world datasets for testing.

---

## 🏗️ Architecture

```mermaid
graph TD
    Client[Web/Mobile Client] --> API[FastAPI Gateway]
    API --> Auth[JWT Auth Service]
    API --> Orchestrator[Agent Orchestrator]
    
    Orchestrator --> DataAgent[Data Agent]
    Orchestrator --> GeoAgent[Geo Agent]
    Orchestrator --> MLAgent[ML Agent]
    
    DataAgent --> DB[(PostgreSQL + PostGIS)]
    GeoAgent --> DB
    MLAgent --> MLflow[MLflow Tracking]
    
    subgraph Infrastructure
        DB
        Redis[Redis Cache]
        MLflow
    end
```

---

## 📂 Project Structure

- `src/api/`: All the API "doors" (routes) and the main application entry point.
- `src/agents/`: The logic for our AI agents and the orchestrator.
- `src/database/`: Where our data models and connection logic live.
- `src/schemas/`: The "contracts" for how data should look when coming in or going out.
- `src/services/`: Specific business logic (e.g., how to handle uploads or predictions).
- `k8s/`: Settings for running the app on Kubernetes (Cloud).
- `docker-compose.yaml`: The "easy button" to start all databases and services locally.

---

## 🚀 Quick Start (Demo)

```bash
# 1. Clone and install
git clone <repo>
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Add: OPENAI_API_KEY=sk-... (optional, uses local embeddings as fallback)

# 3. Start infrastructure
docker-compose up -d

# 4. Seed demo data + train models
python scripts/seed_demo_data.py

# 5. Initialize pgvector tables (in PostgreSQL)
# psql -U astrogeo_user -d astrogeo_db -f scripts/init_postgis.sql

# 6. Run database migrations
alembic upgrade head

# 7. Start API
uvicorn src.api.main:app --reload

# 8. Open Swagger UI
# Visit http://localhost:8000/docs
```

### 🎯 Demo Queries to Try

| Query | Domain | What it shows |
|-------|--------|---------------|
| "Will asteroid 2024 BX1 be visible from Mumbai?" | Astronomy | Agent 2: RF classifier + SHAP + MPC-verified RAG |
| "Is there deforestation in Western Ghats?" | Earth Obs | Agent 1: RF multi-class + Sentinel Hub RAG |
| "Drought risk in Marathwada this season?" | Climate | Agent 3: RF regressor + SMAP-based RAG |
| "Show ISRO mission status" | ISRO | GraphRAG cross-domain traversal |
| "Why is NDVI dropping in Maharashtra?" | Multi | Agent 5: GraphRAG BFS traversal |

### 📡 Key Demo Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/demo/query` | POST | **Main pipeline**: RAG + ML + SHAP + evidence chain |
| `/api/v1/demo/agents` | GET | List all 5 agents with architecture |
| `/api/v1/demo/model-cards` | GET | Public model cards for deployed models |
| `/api/v1/demo/pipeline-status` | GET | LangGraph pipeline node configuration |
| `/api/v1/demo/mlops-status` | GET | MLOps stack + retraining triggers |
| `/api/v1/demo/verify/{hash}` | GET | Verify prediction by SHA-256 hash |

---

**Built with ❤️ for the future of Geospatial AI**

