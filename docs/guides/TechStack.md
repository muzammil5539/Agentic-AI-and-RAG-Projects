# Technology Stack Reference

## Overview

This document catalogs every technology used across the AI Engineering Universe ecosystem, organized by category with version requirements and usage notes.

---

## Core Stack (Used in Most Projects)

| Technology | Category | Version | Usage |
|-----------|----------|---------|-------|
| Python | Language | 3.11+ | Backend, AI logic |
| FastAPI | Backend Framework | 0.100+ | REST API + WebSocket server |
| OpenAI SDK | LLM Provider | 1.0+ | GPT-4o, embeddings, Whisper, TTS |
| LangChain | AI Framework | 0.2+ | Chains, agents, retrievers |
| LangGraph | Orchestration | 0.1+ | State machine agent workflows |
| Next.js | Frontend | 14+ | React SSR framework |
| Tailwind CSS | Styling | 3.4+ | Utility-first CSS |
| Docker | Containerization | 24+ | Development + production |
| PostgreSQL | Database | 15+ | Primary relational database |
| Redis | Cache/Queue | 7+ | Caching, rate limiting, pub/sub |

---

## AI/ML Frameworks

### LLM Providers & Interfaces

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **OpenAI SDK** | GPT-4o, embeddings, fine-tuning | Primary LLM for all projects |
| **Ollama** | Local LLM inference | Development, privacy-sensitive, cost reduction |
| **vLLM** | High-performance LLM serving | Production local deployment (Project 17) |
| **llama.cpp** | CPU/edge inference | Edge deployment (Project 24) |
| **LiteLLM** | Unified LLM interface | Multi-provider routing |

### Agent Frameworks

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **LangGraph** | State machine agents | Complex multi-step agents with branching logic |
| **LangChain** | Chains, tools, retrievers | Simple chains, RAG, tool calling |
| **CrewAI** | Multi-agent teams | Role-based agent collaboration (Project 6) |

### RAG & Retrieval

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **ChromaDB** | Vector database | Development, single-node deployments |
| **Pinecone** | Managed vector DB | Production, scalable, serverless |
| **Weaviate** | Vector + hybrid search | When you need built-in hybrid search |
| **LlamaIndex** | Data framework | Complex data connectors, indexing |
| **Cohere Reranker** | Result reranking | Improving retrieval precision |
| **rank-bm25** | Sparse retrieval | BM25 keyword search |

### Knowledge Graphs

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **Neo4j** | Graph database | Entity relationships, multi-hop reasoning |
| **NetworkX** | Graph algorithms | In-memory graph analysis |

---

## Backend Technologies

### Web Frameworks & APIs

| Tool | Purpose | Projects |
|------|---------|----------|
| **FastAPI** | REST + WebSocket API | All projects |
| **Celery** | Distributed task queue | 10, 15, 16, 18, 19, 20 |
| **WebSockets** | Real-time communication | 8, 10, 20 |
| **gRPC** | High-performance RPC | 24 (edge communication) |

### Databases

| Tool | Purpose | Projects |
|------|---------|----------|
| **PostgreSQL** | Primary relational DB | Most projects |
| **SQLite** | Lightweight local DB | 3, development |
| **Redis** | Cache, queue, sessions | 5, 7, 10, 13, 17, 18, 20 |
| **Elasticsearch** | Full-text search, logs | 16, 21 |
| **TimescaleDB** | Time-series data | 25 (financial data) |
| **Supabase** | Managed PostgreSQL + Auth | 4, 5, 13 |

### Authentication & Security

| Tool | Purpose | Projects |
|------|---------|----------|
| **NextAuth.js** | Frontend auth | 13, 23 |
| **JWT** | Token-based auth | All authenticated projects |
| **OAuth2** | Third-party auth | 13, 18, 23 |
| **bcrypt** | Password hashing | 13 |

### Payments

| Tool | Purpose | Projects |
|------|---------|----------|
| **Stripe** | Subscriptions + metering | 13, 23 |

---

## Frontend Technologies

| Tool | Purpose | Projects |
|------|---------|----------|
| **Next.js 14** | React framework | 3-25 (all new projects) |
| **Tailwind CSS** | Styling | All |
| **shadcn/ui** | Component library | 5, 13, 18, 23 |
| **React Flow** | Node-based editors | 6, 10, 20 |
| **D3.js** | Data visualization | 9, 20, 25 |
| **Cytoscape.js** | Graph visualization | 9 |
| **Monaco Editor** | Code editor | 5, 7 |
| **Chart.js** | Charts and metrics | 15, 19, 25 |
| **Web Audio API** | Audio processing | 8 |
| **TradingView** | Financial charts | 25 |

---

## DevOps & Infrastructure

| Tool | Purpose | Projects |
|------|---------|----------|
| **Docker** | Containerization | All projects |
| **Docker Compose** | Multi-service orchestration | All projects |
| **Kubernetes** | Container orchestration | 16, 20, 23 |
| **GitHub Actions** | CI/CD | All projects |
| **Nginx** | Reverse proxy | Production deployments |
| **Prometheus** | Metrics collection | 16, 20 |
| **Grafana** | Metrics visualization | 16, 20 |

### Cloud Providers

| Provider | Services Used | When |
|----------|--------------|------|
| **AWS** | EC2, S3, Lambda, ECS | Production deployments |
| **Vercel** | Frontend hosting | Next.js deployments |
| **Railway** | Backend hosting | Simple backend deployments |
| **Render** | Full-stack hosting | Alternative to Railway |

---

## External APIs

| API | Purpose | Projects |
|-----|---------|----------|
| **Tavily Search** | Web search for agents | 3, 6, 25 |
| **GitHub API** | Code operations | 7 |
| **Twilio** | Phone/SMS | 8 (stretch) |
| **Alpha Vantage** | Market data | 25 |
| **SEC EDGAR** | Financial filings | 25 |
| **Brave Search** | Alternative web search | 6 |

---

## Development Tools

| Tool | Purpose |
|------|---------|
| **uv** | Fast Python package manager |
| **Ruff** | Python linting + formatting |
| **Pytest** | Python testing |
| **ESLint** | JavaScript/TypeScript linting |
| **Prettier** | Code formatting |
| **Pre-commit** | Git hooks |

---

## Version Pinning Strategy

```toml
# pyproject.toml example
[tool.poetry.dependencies]
python = "^3.11"
fastapi = ">=0.100,<1.0"
langchain = ">=0.2,<1.0"
langgraph = ">=0.1"
openai = ">=1.0,<2.0"
chromadb = ">=0.4"
```

**Rules:**
1. Pin major versions to avoid breaking changes
2. Allow minor/patch updates for bug fixes
3. Lock exact versions in `requirements.txt` for reproducibility
4. Update dependencies monthly
