# 🚀 AstroGeo Deployment Guide

## Overview

This guide explains how to deploy AstroGeo in different environments:
- **Local Development**: Docker Compose
- **Production**: Kubernetes (AWS EKS)

---

## 🏠 Local Development with Docker Compose

### Prerequisites
- Docker Desktop installed and running
- Docker Compose installed

### Quick Start

1. **Create `.env` file** (copy from `.env.example`):
```bash
cp .env.example .env
```

2. **Edit `.env` file** with your credentials:
```env
SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=your-secure-password
OPENAI_API_KEY=your-openai-api-key
```

3. **Start all services**:
```bash
docker-compose up -d
```

4. **Check service status**:
```bash
docker-compose ps
```

5. **View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
```

### Access Points

Once running, access:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MLflow UI**: http://localhost:5000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Common Commands

```bash
# Stop all services
docker-compose down

# Rebuild and restart API
docker-compose build api
docker-compose up -d api

# Remove all data (WARNING: deletes volumes)
docker-compose down -v

# Start with monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d
```

### Troubleshooting

**Issue**: Services won't start
```bash
# Check Docker is running
docker --version

# Check logs for errors
docker-compose logs
```

**Issue**: Port already in use
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process or change port in docker-compose.yaml
```

---

## ☁️ Production Deployment with Kubernetes (AWS EKS)

### Prerequisites

1. **AWS Account** with EKS access
2. **kubectl** installed
3. **AWS CLI** configured
4. **eksctl** (optional, for cluster creation)

### Step 1: Create EKS Cluster

```bash
# Using eksctl (recommended)
eksctl create cluster \
  --name astrogeo-cluster \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed
```

### Step 2: Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name astrogeo-cluster

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### Step 3: Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name astrogeo-ai --region us-east-1

# Build image
docker build -t astrogeo-ai:latest .

# Tag image
docker tag astrogeo-ai:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/astrogeo-ai:latest

# Push to ECR
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/astrogeo-ai:latest
```

### Step 4: Update Kubernetes Secrets

Edit `k8s/deployment-complete.yaml` and replace:
- `${AWS_ACCOUNT_ID}` with your AWS account ID
- `${AWS_REGION}` with your region
- Update all secret values in the `astrogeo-secrets` section

### Step 5: Deploy to Kubernetes

```bash
# Apply the complete configuration
kubectl apply -f k8s/deployment-complete.yaml

# Or apply individual files
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

### Step 6: Verify Deployment

```bash
# Check all resources
kubectl get all -n astrogeo

# Check pods
kubectl get pods -n astrogeo

# Check services
kubectl get svc -n astrogeo

# Check autoscaler
kubectl get hpa -n astrogeo

# View logs
kubectl logs -f deployment/astrogeo-api -n astrogeo
```

### Step 7: Get Load Balancer URL

```bash
# Get the external URL
kubectl get svc astrogeo-service -n astrogeo -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Test health endpoint
curl http://<load-balancer-url>/api/v1/health
```

### Monitoring

```bash
# Watch pod status
kubectl get pods -n astrogeo -w

# Describe pod for details
kubectl describe pod <pod-name> -n astrogeo

# Check HPA status
kubectl get hpa -n astrogeo -w
```

### Updating the Application

```bash
# Build and push new image
docker build -t astrogeo-ai:v1.1.0 .
docker tag astrogeo-ai:v1.1.0 ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/astrogeo-ai:v1.1.0
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/astrogeo-ai:v1.1.0

# Update deployment
kubectl set image deployment/astrogeo-api astrogeo-api=${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/astrogeo-ai:v1.1.0 -n astrogeo

# Watch rollout
kubectl rollout status deployment/astrogeo-api -n astrogeo
```

### Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/deployment-complete.yaml

# Delete cluster (WARNING: this deletes everything)
eksctl delete cluster --name astrogeo-cluster --region us-east-1
```

---

## 🔐 Security Best Practices

### For Production:

1. **Use AWS Secrets Manager** instead of hardcoded secrets:
```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

2. **Enable HTTPS** with ACM certificate (update ingress.yaml)

3. **Use IAM roles** for service accounts (IRSA)

4. **Enable network policies** for pod-to-pod communication

5. **Regular security scanning**:
```bash
# Scan Docker image
docker scan astrogeo-ai:latest

# Scan Kubernetes manifests
kubesec scan k8s/deployment.yaml
```

---

## 📊 CI/CD Integration

The project includes GitHub Actions workflows in `.github/workflows/`:
- **CI**: Runs tests, linting, and builds Docker image
- **CD**: Deploys to EKS on merge to main

Configure GitHub Secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `ECR_REPOSITORY`
- `EKS_CLUSTER_NAME`

---

## 🆘 Troubleshooting

### Kubernetes Issues

**Pods not starting:**
```bash
kubectl describe pod <pod-name> -n astrogeo
kubectl logs <pod-name> -n astrogeo
```

**Service not accessible:**
```bash
kubectl get svc -n astrogeo
kubectl describe svc astrogeo-service -n astrogeo
```

**HPA not scaling:**
```bash
kubectl describe hpa astrogeo-api-hpa -n astrogeo
kubectl top pods -n astrogeo
```

### Docker Compose Issues

**Database connection failed:**
```bash
# Check if postgres is healthy
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

**API won't start:**
```bash
# Rebuild image
docker-compose build api

# Check environment variables
docker-compose config
```

---

## 📝 Next Steps

1. **Local Development**: Start with Docker Compose
2. **Test Locally**: Ensure everything works
3. **Set up AWS**: Create EKS cluster
4. **Deploy to Production**: Use Kubernetes manifests
5. **Monitor**: Set up Prometheus + Grafana
6. **Scale**: Adjust HPA settings based on load

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
