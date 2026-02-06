# 🚀 AstroGeo AI - Enterprise MLOps Platform

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Production-ready MLOps platform combining Agentic AI, Geospatial Analytics, and Modern ML Infrastructure**

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Project Structure](#-project-structure)
- [Development](#-development)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## ✨ Features

### 🤖 **Agentic AI**
- LangChain/AutoGen intelligent agents
- Multi-agent orchestration
- Tool usage and function calling
- Conversation memory
- Performance tracking

### 🌍 **Geospatial Analytics**
- PostGIS integration
- Spatial queries and analysis
- Geographic data visualization
- Location-based ML predictions

### 🔬 **MLOps Pipeline**
- MLflow experiment tracking
- DVC data versioning
- Model registry and versioning
- Automated training pipelines
- A/B testing support

### ⚡ **High-Performance API**
- FastAPI async endpoints
- PostgreSQL connection pooling
- Redis caching
- Rate limiting
- JWT authentication

### 🐳 **Production Ready**
- Docker & Kubernetes
- AWS EKS deployment
- CI/CD with GitHub Actions
- Prometheus + Grafana monitoring
- Comprehensive logging

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Load Balancer                          │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼────┐            ┌────▼────┐
    │ FastAPI │            │ FastAPI │
    │  Pod 1  │            │  Pod 2  │
    └────┬────┘            └────┬────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────┐
    │PostgreSQL│          │  Redis   │
    │ + PostGIS│          │  Cache   │
    └──────────┘          └──────────┘
         │
    ┌────▼─────┐          ┌──────────┐
    │  MLflow  │          │ Agentic  │
    │ Tracking │          │   AI     │
    └──────────┘          └──────────┘
```

**Tech Stack:**
- **API**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL 15 + PostGIS 3.3
- **Cache**: Redis 7
- **ML**: MLflow, DVC, Scikit-learn, TensorFlow
- **AI**: LangChain, OpenAI GPT-4
- **Infrastructure**: Docker, Kubernetes, AWS EKS
- **Monitoring**: Prometheus, Grafana
- **CI/CD**: GitHub Actions

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- PostgreSQL 15+ (local) or Docker
- AWS Account (for deployment)

### 1. Clone Repository
```bash
git clone https://github.com/your-org/astrogeo-ai-mlops.git
cd astrogeo-ai-mlops
```

### 2. Run PowerShell Script (Windows)
```powershell
# Creates complete project structure
.\CREATE_PROJECT_STRUCTURE.ps1
```

### 3. Setup Environment
```bash
# Create virtual environment
conda create -n astrogeo python=3.10 -y
conda activate astrogeo

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 4. Start with Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Access:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - MLflow: http://localhost:5000
```

### 5. Run Locally (Development)
```bash
# Start PostgreSQL & Redis
docker-compose up -d postgres redis

# Run API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Access API Documentation:** http://localhost:8000/docs

---

## 📚 Documentation

Comprehensive guides available in `/docs`:

- **[Setup Guide](docs/COMPLETE_SETUP_GUIDE.md)** - Complete installation walkthrough
- **[API Documentation](docs/API.md)** - Endpoint reference
- **[MLOps Guide](docs/MLOPS.md)** - ML pipeline setup
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Agent Guide](docs/AGENTS.md)** - Agentic AI usage
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues

### Quick Links

| Guide | Description |
|-------|-------------|
| [MLflow Setup](docs/guides/SETUP_MLFLOW.md) | Configure experiment tracking |
| [DagsHub Setup](docs/guides/SETUP_DAGSHUB.md) | Connect to DagsHub |
| [AWS Setup](docs/guides/SETUP_AWS.md) | Configure AWS services |
| [EKS Deployment](docs/guides/SETUP_EKS.md) | Deploy to Kubernetes |
| [Monitoring](docs/guides/SETUP_PROMETHEUS.md) | Setup Prometheus & Grafana |

---

## 📁 Project Structure

```
astrogeo-ai-mlops/
├── src/                      # Source code
│   ├── api/                  # FastAPI application
│   │   ├── routes/           # API endpoints
│   │   └── main.py           # App factory
│   ├── agents/               # AI agents
│   │   ├── base_agent.py     # Base agent class
│   │   ├── ml_agent.py       # ML operations agent
│   │   └── geo_agent.py      # Geospatial agent
│   ├── core/                 # Core utilities
│   │   ├── config.py         # Configuration
│   │   ├── logging.py        # Logging setup
│   │   └── security.py       # Auth & security
│   ├── database/             # Database layer
│   │   ├── models.py         # SQLAlchemy models
│   │   └── connection.py     # DB connection
│   ├── models/               # ML models
│   │   ├── training.py       # Model training
│   │   └── serving.py        # Model serving
│   └── services/             # Business logic
├── tests/                    # Test suite
├── k8s/                      # Kubernetes manifests
├── docs/                     # Documentation
├── configs/                  # Configuration files
├── data/                     # Data storage
├── models/                   # Model artifacts
├── notebooks/                # Jupyter notebooks
├── scripts/                  # Automation scripts
├── .github/workflows/        # CI/CD pipelines
├── docker-compose.yaml       # Local development
├── Dockerfile                # Production image
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## 💻 Development

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_api/test_health.py -v
```

### Code Quality
```bash
# Format code
black src tests
isort src tests

# Lint
flake8 src
mypy src

# Security scan
bandit -r src
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### MLflow Experiments
```bash
# Start MLflow UI
mlflow ui --host 0.0.0.0 --port 5000

# Track experiment
python scripts/train_model.py
```

---

## 🚢 Deployment

### Docker Build
```bash
# Build image
docker build -t astrogeo-ai:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  astrogeo-ai:latest
```

### AWS EKS Deployment

**Prerequisites:**
- AWS CLI configured
- kubectl installed
- eksctl installed

```bash
# Create EKS cluster
eksctl create cluster \
  --name astrogeo-cluster \
  --region us-east-1 \
  --nodegroup-name astrogeo-nodes \
  --node-type t3.medium \
  --nodes 2

# Deploy application
kubectl apply -f k8s/

# Get service URL
kubectl get svc astrogeo-service -n astrogeo
```

**Automated Deployment:**
Push to `main` branch triggers GitHub Actions CI/CD:
1. Run tests
2. Build Docker image
3. Push to ECR
4. Deploy to EKS
5. Run smoke tests

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Ensure all tests pass (`pytest`)
5. Format code (`black`, `isort`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- FastAPI for the amazing framework
- LangChain for agent capabilities
- MLflow for experiment tracking
- PostGIS for geospatial support
- The open-source community

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/astrogeo-ai-mlops/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/astrogeo-ai-mlops/discussions)

---

**Built with ❤️ for production ML systems**

*AstroGeo AI - Where Intelligence Meets Infrastructure*