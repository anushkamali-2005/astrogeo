# ============================================================================
# Makefile - AstroGeo AI MLOps
# Common development and deployment tasks
# ============================================================================

.PHONY: help install install-dev test lint format clean docker-build docker-run deploy-local deploy-eks

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
PIP := pip
DOCKER := docker
KUBECTL := kubectl
PROJECT_NAME := astrogeo-ai-mlops
DOCKER_IMAGE := astrogeo-ai
DOCKER_TAG := latest

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ============================================================================
# HELP
# ============================================================================

help: ## Show this help message
	@echo "$(CYAN)AstroGeo AI MLOps - Makefile Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================================================
# INSTALLATION & SETUP
# ============================================================================

install: ## Install production dependencies
	@echo "$(CYAN)Installing production dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Production dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(CYAN)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

setup: ## Initial project setup
	@echo "$(CYAN)Setting up project...$(NC)"
	cp .env.example .env
	@echo "$(YELLOW)⚠ Please edit .env with your credentials$(NC)"
	$(PYTHON) -m pip install --upgrade pip
	make install
	make install-dev
	@echo "$(GREEN)✓ Project setup complete$(NC)"

# ============================================================================
# DEVELOPMENT
# ============================================================================

run: ## Run development server
	@echo "$(CYAN)Starting development server...$(NC)"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server
	@echo "$(CYAN)Starting production server...$(NC)"
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

shell: ## Open Python shell with app context
	@echo "$(CYAN)Opening Python shell...$(NC)"
	$(PYTHON) -i -c "from src.api.main import app; from src.database.connection import db_manager"

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: ## Run linting checks
	@echo "$(CYAN)Running linters...$(NC)"
	flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src tests --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	@echo "$(GREEN)✓ Linting complete$(NC)"

type-check: ## Run type checking
	@echo "$(CYAN)Running type checks...$(NC)"
	mypy src --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking complete$(NC)"

format: ## Format code with black and isort
	@echo "$(CYAN)Formatting code...$(NC)"
	black src tests
	isort src tests
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-check: ## Check code formatting
	@echo "$(CYAN)Checking code format...$(NC)"
	black --check src tests
	isort --check-only src tests

security: ## Run security checks
	@echo "$(CYAN)Running security checks...$(NC)"
	bandit -r src -f json -o bandit-report.json
	@echo "$(GREEN)✓ Security scan complete$(NC)"

quality: lint type-check security ## Run all quality checks
	@echo "$(GREEN)✓ All quality checks passed$(NC)"

# ============================================================================
# TESTING
# ============================================================================

test: ## Run all tests
	@echo "$(CYAN)Running tests...$(NC)"
	pytest tests/ -v

test-cov: ## Run tests with coverage
	@echo "$(CYAN)Running tests with coverage...$(NC)"
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing -v
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)"

test-fast: ## Run tests without slow tests
	@echo "$(CYAN)Running fast tests...$(NC)"
	pytest tests/ -v -m "not slow"

test-integration: ## Run integration tests only
	@echo "$(CYAN)Running integration tests...$(NC)"
	pytest tests/integration/ -v

# ============================================================================
# DATABASE
# ============================================================================

db-init: ## Initialize database
	@echo "$(CYAN)Initializing database...$(NC)"
	alembic init src/database/migrations
	@echo "$(GREEN)✓ Database migrations initialized$(NC)"

db-migrate: ## Create new migration
	@echo "$(CYAN)Creating migration...$(NC)"
	alembic revision --autogenerate -m "$(msg)"
	@echo "$(GREEN)✓ Migration created$(NC)"

db-upgrade: ## Apply migrations
	@echo "$(CYAN)Applying migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)✓ Migrations applied$(NC)"

db-downgrade: ## Rollback last migration
	@echo "$(CYAN)Rolling back migration...$(NC)"
	alembic downgrade -1
	@echo "$(GREEN)✓ Migration rolled back$(NC)"

db-reset: ## Reset database (WARNING: destructive)
	@echo "$(RED)⚠ This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		echo "$(GREEN)✓ Database reset complete$(NC)"; \
	fi

# ============================================================================
# DOCKER
# ============================================================================

docker-build: ## Build Docker image
	@echo "$(CYAN)Building Docker image...$(NC)"
	$(DOCKER) build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✓ Docker image built: $(DOCKER_IMAGE):$(DOCKER_TAG)$(NC)"

docker-build-no-cache: ## Build Docker image without cache
	@echo "$(CYAN)Building Docker image (no cache)...$(NC)"
	$(DOCKER) build --no-cache -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-run: ## Run Docker container
	@echo "$(CYAN)Running Docker container...$(NC)"
	$(DOCKER) run -p 8000:8000 --env-file .env $(DOCKER_IMAGE):$(DOCKER_TAG)

docker-run-daemon: ## Run Docker container in background
	@echo "$(CYAN)Running Docker container in daemon mode...$(NC)"
	$(DOCKER) run -d -p 8000:8000 --env-file .env --name $(PROJECT_NAME) $(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "$(GREEN)✓ Container started: $(PROJECT_NAME)$(NC)"

docker-stop: ## Stop Docker container
	@echo "$(CYAN)Stopping Docker container...$(NC)"
	$(DOCKER) stop $(PROJECT_NAME)
	$(DOCKER) rm $(PROJECT_NAME)
	@echo "$(GREEN)✓ Container stopped$(NC)"

docker-logs: ## Show Docker container logs
	$(DOCKER) logs -f $(PROJECT_NAME)

docker-compose-up: ## Start all services with docker-compose
	@echo "$(CYAN)Starting docker-compose services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"

docker-compose-down: ## Stop all docker-compose services
	@echo "$(CYAN)Stopping docker-compose services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-compose-logs: ## Show docker-compose logs
	docker-compose logs -f

# ============================================================================
# DEPLOYMENT
# ============================================================================

deploy-local: docker-compose-up ## Deploy locally with docker-compose
	@echo "$(GREEN)✓ Local deployment complete$(NC)"
	@echo "$(CYAN)API: http://localhost:8000$(NC)"
	@echo "$(CYAN)Docs: http://localhost:8000/docs$(NC)"

deploy-eks: ## Deploy to EKS
	@echo "$(CYAN)Deploying to EKS...$(NC)"
	$(KUBECTL) apply -f k8s/
	@echo "$(GREEN)✓ Deployed to EKS$(NC)"

k8s-status: ## Check Kubernetes deployment status
	@echo "$(CYAN)Checking deployment status...$(NC)"
	$(KUBECTL) get pods -n astrogeo
	$(KUBECTL) get svc -n astrogeo

k8s-logs: ## Show Kubernetes pod logs
	$(KUBECTL) logs -f -l app=astrogeo-api -n astrogeo

k8s-delete: ## Delete Kubernetes deployment
	@echo "$(RED)⚠ Deleting Kubernetes deployment$(NC)"
	$(KUBECTL) delete -f k8s/

# ============================================================================
# MLOPS
# ============================================================================

mlflow-ui: ## Start MLflow UI
	@echo "$(CYAN)Starting MLflow UI...$(NC)"
	mlflow ui --host 0.0.0.0 --port 5000

dvc-pull: ## Pull data from DVC remote
	@echo "$(CYAN)Pulling data from DVC...$(NC)"
	dvc pull
	@echo "$(GREEN)✓ Data pulled$(NC)"

dvc-push: ## Push data to DVC remote
	@echo "$(CYAN)Pushing data to DVC...$(NC)"
	dvc push
	@echo "$(GREEN)✓ Data pushed$(NC)"

dvc-repro: ## Reproduce DVC pipeline
	@echo "$(CYAN)Reproducing DVC pipeline...$(NC)"
	dvc repro
	@echo "$(GREEN)✓ Pipeline reproduced$(NC)"

# ============================================================================
# CLEANUP
# ============================================================================

clean: ## Clean temporary files
	@echo "$(CYAN)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-docker: ## Clean Docker images and containers
	@echo "$(CYAN)Cleaning Docker resources...$(NC)"
	$(DOCKER) system prune -af
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

# ============================================================================
# CI/CD
# ============================================================================

ci: quality test ## Run CI checks (quality + tests)
	@echo "$(GREEN)✓ CI checks passed$(NC)"

pre-commit: format quality test ## Run pre-commit checks
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

# ============================================================================
# MONITORING
# ============================================================================

logs: ## Show application logs
	tail -f logs/app.log

metrics: ## Show application metrics
	@echo "$(CYAN)Application metrics:$(NC)"
	@echo "Visit: http://localhost:8000/metrics"

# ============================================================================
# UTILITIES
# ============================================================================

requirements: ## Generate requirements.txt from installed packages
	@echo "$(CYAN)Generating requirements.txt...$(NC)"
	$(PIP) freeze > requirements.txt
	@echo "$(GREEN)✓ requirements.txt updated$(NC)"

tree: ## Show project structure
	@echo "$(CYAN)Project structure:$(NC)"
	tree -I '__pycache__|*.pyc|.git|.pytest_cache|htmlcov|.mypy_cache' -L 3

version: ## Show version information
	@echo "$(CYAN)Version Information:$(NC)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Pip: $(shell $(PIP) --version | cut -d' ' -f2)"
	@echo "Docker: $(shell $(DOCKER) --version | cut -d' ' -f3 | sed 's/,//')"
	@echo "Kubectl: $(shell $(KUBECTL) version --client --short 2>/dev/null | cut -d' ' -f3)"

# ============================================================================
# DEVELOPMENT SHORTCUTS
# ============================================================================

dev: install-dev format test ## Full development setup
	@echo "$(GREEN)✓ Development environment ready$(NC)"

build: clean docker-build ## Clean and build Docker image

full-test: clean quality test-cov ## Run full test suite with coverage

# ============================================================================
# END
# ============================================================================