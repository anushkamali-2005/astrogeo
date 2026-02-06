.PHONY: help install install-dev clean lint format test test-cov docker-build docker-run docker-push deploy

# Variables
PYTHON := python
PIP := pip
PROJECT_NAME := astrogeo-ai-mlops
DOCKER_IMAGE := $(PROJECT_NAME)
DOCKER_TAG := latest
AWS_REGION := us-east-1
ECR_REPO := $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com/$(PROJECT_NAME)

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)Available commands:$(NC)'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Production dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e .
	pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

clean: ## Clean up cache and temporary files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .eggs/
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

lint: ## Run linters
	@echo "$(BLUE)Running linters...$(NC)"
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/
	mypy src/
	pylint src/
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	black src/ tests/
	isort src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	pytest -v
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	pytest --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	pytest -v -m integration
	@echo "$(GREEN)✓ Integration tests complete$(NC)"

security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	bandit -r src/
	safety check
	@echo "$(GREEN)✓ Security check complete$(NC)"

db-upgrade: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)✓ Database upgraded$(NC)"

db-downgrade: ## Rollback database migration
	@echo "$(BLUE)Rolling back database migration...$(NC)"
	alembic downgrade -1
	@echo "$(GREEN)✓ Database downgraded$(NC)"

db-init: ## Initialize database
	@echo "$(BLUE)Initializing database...$(NC)"
	$(PYTHON) -m src.database.connection init
	@echo "$(GREEN)✓ Database initialized$(NC)"

dvc-pull: ## Pull data from DVC remote
	@echo "$(BLUE)Pulling data from DVC...$(NC)"
	dvc pull
	@echo "$(GREEN)✓ Data pulled$(NC)"

dvc-push: ## Push data to DVC remote
	@echo "$(BLUE)Pushing data to DVC...$(NC)"
	dvc push
	@echo "$(GREEN)✓ Data pushed$(NC)"

dvc-repro: ## Reproduce DVC pipeline
	@echo "$(BLUE)Reproducing DVC pipeline...$(NC)"
	dvc repro
	@echo "$(GREEN)✓ Pipeline reproduced$(NC)"

mlflow-ui: ## Start MLflow UI
	@echo "$(BLUE)Starting MLflow UI...$(NC)"
	mlflow ui --host 0.0.0.0 --port 5000

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-run: ## Run Docker container locally
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -p 8000:8000 --env-file .env $(DOCKER_IMAGE):$(DOCKER_TAG)

docker-push: ## Push Docker image to registry
	@echo "$(BLUE)Pushing Docker image to ECR...$(NC)"
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REPO)
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(ECR_REPO):$(DOCKER_TAG)
	docker push $(ECR_REPO):$(DOCKER_TAG)
	@echo "$(GREEN)✓ Docker image pushed$(NC)"

k8s-deploy: ## Deploy to Kubernetes
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	kubectl apply -f k8s/
	@echo "$(GREEN)✓ Deployed to Kubernetes$(NC)"

k8s-delete: ## Delete Kubernetes resources
	@echo "$(BLUE)Deleting Kubernetes resources...$(NC)"
	kubectl delete -f k8s/
	@echo "$(GREEN)✓ Kubernetes resources deleted$(NC)"

k8s-logs: ## Show logs from Kubernetes pods
	@echo "$(BLUE)Fetching logs...$(NC)"
	kubectl logs -l app=$(PROJECT_NAME) --tail=100 -f

k8s-status: ## Check Kubernetes deployment status
	@echo "$(BLUE)Checking deployment status...$(NC)"
	kubectl get all -l app=$(PROJECT_NAME)

run-dev: ## Run development server
	@echo "$(BLUE)Starting development server...$(NC)"
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run production server
	@echo "$(BLUE)Starting production server...$(NC)"
	gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(NC)"
	mkdocs serve

docs-build: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	mkdocs build
	@echo "$(GREEN)✓ Documentation built$(NC)"

pre-commit: ## Run pre-commit hooks
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit complete$(NC)"

setup-env: ## Setup environment variables
	@echo "$(BLUE)Setting up environment...$(NC)"
	cp .env.example .env
	@echo "$(GREEN)✓ Created .env file - please update with your values$(NC)"

all: clean install-dev lint test ## Run all checks
	@echo "$(GREEN)✓ All checks passed$(NC)"