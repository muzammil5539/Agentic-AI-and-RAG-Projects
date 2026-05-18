# Ecosystem Architecture Overview

## System-Level Architecture

```mermaid
graph TB
    subgraph "User Layer"
        WEB[Web Dashboard]
        API_CLIENT[API Clients]
        VOICE[Voice Interface]
        BROWSER[Browser Agent]
    end

    subgraph "Application Layer"
        GATEWAY[API Gateway]
        AUTH[Auth Service]
        BILLING[Billing Service]
    end

    subgraph "AI Engine Layer"
        AGENTS[Agent Orchestrator]
        RAG[RAG Pipeline]
        MEMORY[Memory System]
        EVAL[Evaluation Engine]
    end

    subgraph "Model Layer"
        OPENAI[OpenAI API]
        OLLAMA[Ollama Local]
        FINETUNE[Fine-tuned Models]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL)]
        VECTOR[(Vector Store)]
        GRAPH[(Neo4j)]
        CACHE[(Redis)]
        SEARCH[(Elasticsearch)]
    end

    subgraph "Infrastructure"
        DOCKER[Docker]
        K8S[Kubernetes]
        CI[GitHub Actions]
        MONITOR[Monitoring]
    end

    WEB --> GATEWAY
    API_CLIENT --> GATEWAY
    VOICE --> GATEWAY
    BROWSER --> GATEWAY

    GATEWAY --> AUTH
    GATEWAY --> BILLING
    GATEWAY --> AGENTS
    GATEWAY --> RAG

    AGENTS --> MEMORY
    AGENTS --> EVAL
    RAG --> MEMORY

    AGENTS --> OPENAI
    AGENTS --> OLLAMA
    AGENTS --> FINETUNE
    RAG --> OPENAI

    AGENTS --> PG
    RAG --> VECTOR
    RAG --> GRAPH
    MEMORY --> CACHE
    AGENTS --> SEARCH

    DOCKER --> K8S
    K8S --> MONITOR
    CI --> DOCKER
```

## How Projects Connect

```mermaid
graph LR
    subgraph "Data Ingestion"
        DOC[Documents]
        WEB_DATA[Web Data]
        VOICE_IN[Voice Input]
        IMG[Images]
    end

    subgraph "Processing"
        CHUNK[Chunking]
        EMBED[Embedding]
        EXTRACT[Entity Extraction]
        TRANSCRIBE[Transcription]
    end

    subgraph "Storage"
        VEC_DB[Vector DB]
        GRAPH_DB[Graph DB]
        REL_DB[Relational DB]
    end

    subgraph "Retrieval"
        DENSE[Dense Search]
        SPARSE[BM25]
        HYBRID[Hybrid Fusion]
        GRAPH_TRAV[Graph Traversal]
    end

    subgraph "Generation"
        LLM_GEN[LLM Generation]
        SELF_RAG[Self-RAG Eval]
        STREAM[Streaming]
    end

    subgraph "Output"
        TEXT_OUT[Text Response]
        VOICE_OUT[Voice Output]
        ACTION[Tool Actions]
        REPORT[Reports]
    end

    DOC --> CHUNK --> EMBED --> VEC_DB
    DOC --> EXTRACT --> GRAPH_DB
    WEB_DATA --> CHUNK
    VOICE_IN --> TRANSCRIBE --> CHUNK
    IMG --> EXTRACT

    VEC_DB --> DENSE --> HYBRID
    REL_DB --> SPARSE --> HYBRID
    GRAPH_DB --> GRAPH_TRAV --> HYBRID

    HYBRID --> LLM_GEN
    LLM_GEN --> SELF_RAG
    SELF_RAG --> STREAM

    STREAM --> TEXT_OUT
    STREAM --> VOICE_OUT
    LLM_GEN --> ACTION
    LLM_GEN --> REPORT
```

## Shared Component Architecture

### Common Backend Pattern (All Projects)

```
┌──────────────────────────────────────────────┐
│                  FastAPI App                   │
├──────────────────────────────────────────────┤
│  Middleware: CORS, Auth, Rate Limit, Logging │
├──────────────────────────────────────────────┤
│  Routers: /api/v1/...                        │
├──────────────────────────────────────────────┤
│  Services: Business logic layer              │
├──────────────────────────────────────────────┤
│  AI Engine: LLM calls, embeddings, agents    │
├──────────────────────────────────────────────┤
│  Data Layer: DB, cache, vector store         │
└──────────────────────────────────────────────┘
```

### Common Frontend Pattern (Next.js Projects)

```
┌──────────────────────────────────────────────┐
│              Next.js 14 App Router            │
├──────────────────────────────────────────────┤
│  Pages: app/(routes)/page.tsx                │
├──────────────────────────────────────────────┤
│  Components: Reusable UI components          │
├──────────────────────────────────────────────┤
│  Hooks: Custom React hooks                   │
├──────────────────────────────────────────────┤
│  API Client: Fetch wrapper for backend       │
├──────────────────────────────────────────────┤
│  State: React Context / Zustand              │
└──────────────────────────────────────────────┘
```

## Deployment Topology

```mermaid
graph TB
    subgraph "Development"
        DEV_LOCAL[Local Machine]
        DEV_DOCKER[Docker Compose]
        DEV_OLLAMA[Ollama Local]
    end

    subgraph "Staging"
        STAGE_RAILWAY[Railway]
        STAGE_VERCEL[Vercel Preview]
    end

    subgraph "Production"
        PROD_AWS[AWS ECS/EKS]
        PROD_VERCEL[Vercel Production]
        PROD_CDN[CloudFront CDN]
    end

    subgraph "External Services"
        EXT_OPENAI[OpenAI API]
        EXT_PINECONE[Pinecone]
        EXT_STRIPE[Stripe]
        EXT_GITHUB[GitHub API]
    end

    DEV_LOCAL --> DEV_DOCKER
    DEV_DOCKER --> DEV_OLLAMA

    DEV_DOCKER -->|git push| STAGE_RAILWAY
    DEV_DOCKER -->|git push| STAGE_VERCEL

    STAGE_RAILWAY -->|promote| PROD_AWS
    STAGE_VERCEL -->|promote| PROD_VERCEL

    PROD_AWS --> EXT_OPENAI
    PROD_AWS --> EXT_PINECONE
    PROD_AWS --> EXT_STRIPE
    PROD_AWS --> EXT_GITHUB
    PROD_VERCEL --> PROD_CDN
```
