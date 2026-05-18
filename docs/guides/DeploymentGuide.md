# Deployment Guide

## Overview

This guide covers deployment strategies for all projects in the AI Engineering Universe — from local development to production Kubernetes clusters.

---

## Deployment Tiers

```mermaid
graph LR
    L[Local Dev] --> S[Single Server]
    S --> C[Docker Compose]
    C --> K[Kubernetes]

    style L fill:#4ade80
    style S fill:#60a5fa
    style C fill:#f59e0b
    style K fill:#ef4444
```

| Tier | When to Use | Cost | Complexity |
|------|-------------|------|------------|
| Local | Development, testing | Free | Low |
| Single Server | Demos, personal use | $5-20/mo | Low |
| Docker Compose | Small production, demos | $20-50/mo | Medium |
| Kubernetes | Enterprise, scaling | $100+/mo | High |

---

## Tier 1: Local Development

### Standard Setup (All Projects)

```bash
# 1. Clone and navigate
git clone https://github.com/muzammil5539/RAG-Projects.git
cd RAG-Projects/projects/[phase]/[project]

# 2. Python environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Environment variables
cp .env.example .env
# Edit .env with your keys

# 5. Run
python main.py
# or
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js Projects)

```bash
cd frontend
npm install
npm run dev
# Available at http://localhost:3000
```

### Local LLM (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.1
ollama pull nomic-embed-text

# Set in .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Tier 2: Single Server (Railway/Render)

### Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Set environment variables
railway variables set OPENAI_API_KEY=sk-...
railway variables set DATABASE_URL=postgresql://...
```

### Render Deployment

1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables

### Vercel (Frontend Only)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel --prod
```

---

## Tier 3: Docker Compose (Recommended for Most Projects)

### Standard docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=app
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  # Optional: Ollama for local models
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

volumes:
  pgdata:
  redisdata:
  ollama:
```

### Standard Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Deploy to VPS

```bash
# SSH to server
ssh user@server

# Clone repo
git clone https://github.com/muzammil5539/RAG-Projects.git
cd RAG-Projects/projects/[phase]/[project]

# Create .env file
nano .env

# Build and run
docker compose up -d --build

# Check status
docker compose ps
docker compose logs -f app
```

---

## Tier 4: Kubernetes (Enterprise Projects)

### Basic K8s Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ai-app
  template:
    metadata:
      labels:
        app: ai-app
    spec:
      containers:
      - name: app
        image: ghcr.io/muzammil5539/ai-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-secrets
              key: openai-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ai-app-service
spec:
  selector:
    app: ai-app
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
    paths:
      - 'projects/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # Railway/Render/K8s deploy command
          echo "Deploying..."
```

---

## Environment Variable Management

### Development (.env file)
```bash
# .env (NEVER commit this file)
OPENAI_API_KEY=sk-proj-...
DATABASE_URL=postgresql://user:pass@localhost:5432/app
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
DEBUG=true
```

### Production (Secrets Manager)
```bash
# Use platform-specific secrets:
# - Railway: railway variables set KEY=value
# - AWS: AWS Secrets Manager
# - K8s: kubectl create secret
```

---

## Monitoring & Observability

### Health Check Endpoint (Add to Every Project)

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": await check_db(),
            "redis": await check_redis(),
            "llm": await check_llm_api()
        }
    }
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

logger.info("request_processed",
    endpoint="/api/v1/chat",
    latency_ms=245,
    tokens_used=150,
    user_id="usr_123"
)
```

---

## Cost Optimization

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Response caching (Redis) | 40-60% API cost | Cache repeated queries |
| Model routing (GPT-4o-mini for simple) | 30-50% | Classify complexity first |
| Batch processing | 20-30% | Queue non-urgent requests |
| Ollama for dev/test | 100% dev cost | Use local during development |
| Embedding caching | 20-40% | Cache document embeddings |
