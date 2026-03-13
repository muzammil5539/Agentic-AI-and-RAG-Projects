# RAG HNSW App

A production-ready **Retrieval-Augmented Generation (RAG)** application built with FastAPI and LangChain, featuring **hybrid search** (HNSW vector search + BM25), a dual-layer **memory system**, and a clean single-page web UI.

---

## Table of Contents

- [Overview](#overview)
- [Screenshots](#screenshots)
- [Key Features](#key-features)
- [Architecture](#architecture)
  - [High-Level Diagram](#high-level-diagram)
  - [Module Breakdown](#module-breakdown)
- [Directory Structure](#directory-structure)
- [Memory System](#memory-system)
  - [Memory Type 1 — In-Chat (Session) Memory](#memory-type-1--in-chat-session-memory)
  - [Memory Type 2 — Cross-Chat Memory](#memory-type-2--cross-chat-memory)
- [Hybrid Retrieval](#hybrid-retrieval)
- [API Reference](#api-reference)
  - [Documents](#documents)
  - [Sessions](#sessions)
  - [Query](#query)
  - [Cross-Chat Memory](#cross-chat-memory)
- [Configuration](#configuration)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Supported Document Formats](#supported-document-formats)
- [Tech Stack](#tech-stack)
- [Data Storage](#data-storage)

---

## Overview

This application lets you upload documents, ask questions about them in a conversational interface, and receive grounded, cited answers powered by GPT-4o-mini. It maintains full conversation history within a session and automatically summarises and stores completed conversations so the AI can reference past discussions in future sessions.

---

## Screenshots

### 1 — Application UI Overview

![Application UI Overview](images/1-%20Page%20UI.png)

The screenshot above shows the complete single-page interface on first load. The numbered red boxes highlight each functional region:

| Box | Region | Description |
|---|---|---|
| **1** | **CHATS panel** (top-left) | Lists all chat sessions sorted newest-first. The **+ New Chat** button creates a new isolated session. Each session is auto-titled from the first user message and can be renamed, archived, or deleted via its context menu. |
| **2** | **Document upload area** | Drag-and-drop zone (or click **Browse Files**) for ingesting documents. Accepts PDF, TXT, DOCX, CSV, and Markdown files. On drop/select the file is sent to `POST /api/upload`, chunked, embedded, and stored in ChromaDB. |
| **3** | **Document list** | Displays every ingested document with its chunk count. Each entry has a **share toggle** (checkmark) to mark the document as *globally shared*, making it available as background context in every session regardless of which documents were uploaded per-chat. |
| **4** | **Inter-Chat Memory panel** (bottom-left) | Shows archived conversation summaries. Every time a session is deleted or archived, the full transcript is summarised by the LLM, embedded, and stored here. These summaries are automatically retrieved and injected into the system prompt on every new query to provide continuity across conversations. |
| **5** | **Chat input bar** | The main question input. Press **Enter** to send, **Shift + Enter** for a newline. The message is routed through the hybrid retriever (HNSW + BM25), cross-chat memory search, and the LLM chain before the grounded, cited answer is streamed back into the chat window. |

---

### 2 — RAG in Action (Part A): Uploading a Document & Asking a Question

![RAG in Action – Part A](images/2-%20RAG%20in%20action%20a.png)

This screenshot captures the first stage of a live RAG interaction:

- A document has been uploaded and ingested — the **Document list** (Box 3 area) shows the file name and its chunk count.
- The user has typed a question in the chat input and submitted it.
- The **CHATS panel** now shows the active session, auto-titled from the first user message.
- The hybrid retriever begins searching both the HNSW vector index and the BM25 keyword index in parallel to locate the most relevant chunks.

---

### 2 — RAG in Action (Part B): Grounded Answer with Source Citations

![RAG in Action – Part B](images/2-%20RAG%20in%20action%20b.png)

This screenshot shows the assistant's response after the retrieval and generation pipeline has completed:

- The **chat window** displays the LLM-generated answer, grounded exclusively in the uploaded document.
- Inline `[Source: filename, Chunk: N]` citations are embedded directly in the answer text so every factual claim is traceable.
- A **References** section at the end of the response lists all source chunks used, including the filename, page number (where available), and a short snippet.
- The **In-Chat Memory** and **Cross-Chat Memory** badges in the top-right header update to reflect the current session's memory state.

---

### 2 — RAG in Action (Part C): Multi-Turn Conversation & Memory

![RAG in Action – Part C](images/2-%20RAG%20in%20action%20c.png)

This screenshot demonstrates the multi-turn and cross-session memory capabilities:

- The chat history shows multiple back-and-forth turns; the **In-Chat Memory** retains the last 20 user/assistant pairs (40 messages) and injects them into every prompt so the assistant maintains full conversational context.
- If a previous session was archived, the **Inter-Chat Memory panel** shows the stored summary and the **Cross-Chat Memory** badge in the header reflects the count of archived memories.
- The assistant's follow-up answers reference earlier turns naturally, demonstrating that the session memory is correctly threaded into the LLM context.
- Source citations continue to appear in every response, ensuring answers remain grounded even across multi-turn exchanges.

---

## Key Features

| Feature | Description |
|---|---|
| **Hybrid Retrieval** | Combines HNSW vector search with BM25 keyword search via an ensemble retriever for higher recall |
| **HNSW Vector Index** | ChromaDB configured with tunable HNSW parameters (`M`, `ef_construction`, `ef_search`, cosine space) |
| **In-Chat Memory** | Full multi-turn conversation history per session, persisted to disk and injected into every prompt |
| **Cross-Chat Memory** | LLM-generated summaries of past sessions are embedded and semantically searched to provide continuity across conversations |
| **Document Sharing** | Mark documents as "globally shared" so they are always available across all chat sessions |
| **Multi-format Ingestion** | Supports PDF, DOCX, TXT, Markdown, and CSV files |
| **Source Citations** | Every answer includes inline `[Source: filename, Chunk: N]` citations and a References section |
| **Session Management** | Create, rename, delete, archive, and list chat sessions via REST API |
| **Web UI** | Single-page app served as static files — no separate frontend build step required |
| **Configurable** | All key parameters (chunk size, HNSW tuning, retrieval weights, models) controlled via `.env` |

---

## Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser (SPA)                              │
│                    static/index.html + app.js                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │  HTTP / REST
┌────────────────────────────▼────────────────────────────────────────┐
│                     FastAPI Application                             │
│                         main.py                                     │
│                                                                     │
│  ┌──────────────┐    ┌──────────────────────────────────────────┐  │
│  │  api/routes  │    │              api/models.py               │  │
│  │  (REST API)  │    │          (Pydantic schemas)              │  │
│  └──────┬───────┘    └──────────────────────────────────────────┘  │
│         │                                                           │
│   ┌─────▼──────────────────────────────────────────────────────┐   │
│   │                    Query Pipeline                           │   │
│   │                                                             │   │
│   │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│   │  │  ingestion/ │  │  retrieval/  │  │   generation/    │  │   │
│   │  │  loader.py  │  │  hybrid_ret  │  │    chain.py      │  │   │
│   │  │  chunker.py │  │  retriever   │  │  (LLM + prompt)  │  │   │
│   │  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘  │   │
│   │         │                │                    │            │   │
│   └─────────┼────────────────┼────────────────────┼────────────┘   │
│             │                │                    │                │
│   ┌─────────▼────────┐  ┌────▼──────────────┐    │                │
│   │  vectorstore/    │  │  Hybrid Retriever  │    │                │
│   │  chroma_store.py │  │  Vector + BM25     │    │                │
│   │  (HNSW index)    │  │  EnsembleRetriever │    │                │
│   └─────────┬────────┘  └────────────────────┘    │                │
│             │                                      │                │
│   ┌─────────▼──────────────────────────────────────▼────────────┐  │
│   │                       memory/                                │  │
│   │  session_store.py     cross_chat_store.py   chat_memory_    │  │
│   │  (In-Chat history)    (doc sharing flags)   store.py        │  │
│   │                                             (Cross-Chat LLM │  │
│   │                                              summaries)      │  │
│   └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                             │
          ┌──────────────────┼─────────────────┐
          ▼                  ▼                  ▼
   ┌─────────────┐   ┌──────────────┐   ┌─────────────┐
   │  ChromaDB   │   │  OpenAI API  │   │  Disk (JSON)│
   │  (HNSW)     │   │  Embeddings  │   │  sessions   │
   │  2 colls    │   │  + GPT-4o    │   │  + sharing  │
   └─────────────┘   └──────────────┘   └─────────────┘
```

### Module Breakdown

| Module | File(s) | Responsibility |
|---|---|---|
| **Entry Point** | `main.py` | FastAPI app setup, lifespan hooks, static file serving |
| **Configuration** | `config.py` | Pydantic `Settings` class; loads `.env`; exposes all tunable parameters |
| **API Layer** | `api/routes.py`, `api/models.py` | All REST endpoints; Pydantic request/response schemas |
| **Ingestion** | `ingestion/loader.py` | Loads raw documents using format-specific LangChain loaders |
| **Ingestion** | `ingestion/chunker.py` | Recursive character text splitter; attaches `chunk_index` metadata |
| **Vector Store** | `vectorstore/chroma_store.py` | Singleton ChromaDB client; HNSW collection setup; document add/retrieve |
| **Retrieval** | `retrieval/hybrid_retriever.py` | Builds BM25 retriever from ChromaDB contents; creates `EnsembleRetriever` |
| **Generation** | `generation/chain.py` | System prompt; context + cross-chat formatting; LLM call; source extraction |
| **Session Memory** | `memory/session_store.py` | Per-session message history; persisted to `data/sessions.json` |
| **Sharing Flags** | `memory/cross_chat_store.py` | Tracks which documents are globally shared; persisted to `data/cross_chat_settings.json` |
| **Cross-Chat Memory** | `memory/chat_memory_store.py` | LLM summarisation of closed sessions; upserts embeddings into `chat_memory` ChromaDB collection |
| **Frontend** | `static/` | Single-page application (HTML + CSS + vanilla JS) |

---

## Directory Structure

```
rag-hnsw-app/
├── main.py                    # FastAPI app entry point
├── config.py                  # All configuration via pydantic-settings
├── requirements.txt           # Python dependencies
├── .env                       # Secret keys and overrides (not committed)
│
├── api/
│   ├── models.py              # Pydantic request/response schemas
│   └── routes.py              # All REST API endpoints
│
├── ingestion/
│   ├── loader.py              # Document loading (PDF, DOCX, TXT, CSV, MD)
│   └── chunker.py             # Recursive text splitter
│
├── vectorstore/
│   └── chroma_store.py        # ChromaDB singleton with HNSW configuration
│
├── retrieval/
│   └── hybrid_retriever.py    # BM25 + vector ensemble retriever
│
├── generation/
│   └── chain.py               # LLM chain, prompt template, answer generation
│
├── memory/
│   ├── session_store.py       # In-chat multi-turn memory (JSON persistence)
│   ├── cross_chat_store.py    # Document sharing flags (JSON persistence)
│   └── chat_memory_store.py   # Cross-chat LLM summaries (ChromaDB persistence)
│
├── static/
│   ├── index.html             # Main SPA shell
│   ├── css/
│   │   └── style.css          # Application styles
│   └── js/
│       └── app.js             # Frontend logic
│
└── data/                      # Runtime data (auto-created, not committed)
    ├── sessions.json          # Persisted session histories
    ├── cross_chat_settings.json  # Shared document flags
    ├── uploads/               # Uploaded document files
    └── chroma_db/             # ChromaDB persistent storage
        ├── chroma.sqlite3
        └── <collection-uuid>/
```

---

## Memory System

The application implements a **two-tier memory architecture**:

### Memory Type 1 — In-Chat (Session) Memory

- Each chat session maintains its own isolated message history.
- The last 20 user/assistant turn pairs (40 messages) are injected into every prompt as LangChain `HumanMessage` / `AIMessage` objects.
- Sessions are persisted to `data/sessions.json` so history survives server restarts.
- Sessions are auto-titled from the first user message.

```
User asks question
      │
      ▼
session_store.get_history(session_id)   ─►  last 40 messages
      │
      ▼
Injected into ChatPromptTemplate as MessagesPlaceholder
      │
      ▼
LLM sees full prior conversation context
```

### Memory Type 2 — Cross-Chat Memory

When a session is deleted (or manually archived), its full message transcript is:

1. Sent to the LLM with a summarisation prompt requesting a 200–400 word dense prose summary.
2. The summary is embedded with `text-embedding-3-small`.
3. Stored/upserted in a dedicated ChromaDB collection `chat_memory` with metadata (`session_id`, `session_title`, `message_count`, `archived_at`).

On every new query, the top-3 most semantically similar past-session summaries are retrieved and injected into the system prompt so the assistant can reference previous conversations.

```
Query arrives
      │
      ▼
chat_memory_store.search_relevant(question, k=3)
      │
      ▼
Top-3 semantically matching past session summaries
      │
      ▼
Formatted and injected into system prompt under "Cross-Chat Memory" section
```

---

## Hybrid Retrieval

Retrieval combines two complementary strategies via LangChain's `EnsembleRetriever`:

| Retriever | Mechanism | Strength |
|---|---|---|
| **Vector (HNSW)** | Approximate nearest-neighbour search on OpenAI embeddings stored in ChromaDB | Semantic similarity; paraphrase matching |
| **BM25** | Keyword-based TF-IDF ranking over all document chunks in memory | Exact term matching; rare words |

Results are merged using configurable weights (default 50/50) and deduplicated.

**HNSW parameters** (tunable in `.env`):

| Parameter | Default | Effect |
|---|---|---|
| `HNSW_SPACE` | `cosine` | Distance metric |
| `HNSW_EF_CONSTRUCTION` | `200` | Index build quality (higher = better index, slower build) |
| `HNSW_EF_SEARCH` | `150` | Query-time recall (higher = better recall, slower query) |
| `HNSW_MAX_NEIGHBORS` (M) | `16` | Graph connectivity (higher = better recall, more memory) |

---

## API Reference

All endpoints are prefixed with `/api`.

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a document file for ingestion |
| `GET` | `/api/documents` | List all ingested documents with chunk counts |
| `DELETE` | `/api/documents/{filename}` | Delete a document and all its chunks |
| `PUT` | `/api/documents/{filename}/shared` | Toggle global sharing for a document |
| `GET` | `/api/shared-documents` | List all globally shared documents |

**Upload request:** `multipart/form-data` with field `file`.

**Upload response:**
```json
{
  "filename": "report.pdf",
  "num_chunks": 42,
  "message": "Successfully ingested 42 chunks from report.pdf."
}
```

---

### Sessions

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/sessions` | Create a new chat session |
| `GET` | `/api/sessions` | List all sessions (sorted newest first) |
| `GET` | `/api/sessions/{session_id}` | Get a session's full message history |
| `PUT` | `/api/sessions/{session_id}/rename` | Rename a session |
| `DELETE` | `/api/sessions/{session_id}` | Delete session (auto-archives to Cross-Chat Memory) |
| `POST` | `/api/sessions/{session_id}/clear` | Clear message history without deleting session |
| `POST` | `/api/sessions/{session_id}/archive` | Manually archive session to Cross-Chat Memory |

---

### Query

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/query` | Submit a question and receive a grounded, cited answer |

**Request body:**
```json
{
  "question": "What is HNSW?",
  "session_id": "optional-uuid",
  "vector_weight": 0.5,
  "num_results": 5
}
```

**Response:**
```json
{
  "answer": "HNSW (Hierarchical Navigable Small World)...",
  "sources": [
    {
      "filename": "report.pdf",
      "page": 3,
      "chunk_index": 12,
      "snippet": "HNSW is a graph-based approximate..."
    }
  ],
  "session_id": "abc-123",
  "cross_chat_refs": [
    {
      "session_id": "prev-session-id",
      "session_title": "HNSW discussion",
      "archived_at": "2026-03-01",
      "snippet": "We previously discussed HNSW parameters..."
    }
  ]
}
```

---

### Cross-Chat Memory

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/chat-memory` | List all archived conversation summaries |
| `DELETE` | `/api/chat-memory/{session_id}` | Delete a specific archived memory entry |

---

## Configuration

All configuration is managed through `config.py` using `pydantic-settings`. Create a `.env` file in the `rag-hnsw-app/` directory:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional — override defaults below
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini

# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=rag_documents

# HNSW index tuning
HNSW_SPACE=cosine
HNSW_EF_CONSTRUCTION=200
HNSW_EF_SEARCH=150
HNSW_MAX_NEIGHBORS=16

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Retrieval
VECTOR_SEARCH_K=5
BM25_SEARCH_K=5
VECTOR_WEIGHT=0.5
BM25_WEIGHT=0.5
```

> The application will raise a `RuntimeError` at startup if `OPENAI_API_KEY` is not set.

---

## Prerequisites

- **Python 3.11+**
- An **OpenAI API key** with access to:
  - `text-embedding-3-small` (or your chosen embedding model)
  - `gpt-4o-mini` (or your chosen chat model)

---

## Installation & Setup

**1. Clone or download the project:**

```bash
cd rag-hnsw-app
```

**2. Create and activate a virtual environment:**

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Create the `.env` file:**

```bash
# Windows PowerShell
Set-Content .env "OPENAI_API_KEY=sk-your-key-here"

# macOS / Linux
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

---

## Running the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at:

- **Web UI:** [http://localhost:8000](http://localhost:8000)
- **Interactive API docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API docs:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

The `data/uploads/` and `data/chroma_db/` directories are created automatically on first run.

---

## Supported Document Formats

| Format | Extension | Loader |
|---|---|---|
| PDF | `.pdf` | `PyPDFLoader` |
| Word Document | `.docx` | `Docx2txtLoader` |
| Plain Text | `.txt` | `TextLoader` |
| Markdown | `.md` | `TextLoader` |
| CSV | `.csv` | `CSVLoader` |

---

## Tech Stack

| Component | Technology |
|---|---|
| **Web Framework** | [FastAPI](https://fastapi.tiangolo.com/) |
| **ASGI Server** | [Uvicorn](https://www.uvicorn.org/) |
| **LLM Orchestration** | [LangChain](https://python.langchain.com/) |
| **Embeddings** | OpenAI `text-embedding-3-small` |
| **Chat Model** | OpenAI `gpt-4o-mini` |
| **Vector Database** | [ChromaDB](https://www.trychroma.com/) (HNSW index) |
| **Keyword Search** | [rank-bm25](https://github.com/dorianbrown/rank_bm25) via `BM25Retriever` |
| **Hybrid Retrieval** | LangChain `EnsembleRetriever` |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) + pydantic-settings |
| **Document Parsing** | pypdf, docx2txt |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript (no build step) |
| **Persistence** | ChromaDB (vectors) + JSON files (sessions, settings) |

---

## Data Storage

| Data | Location | Format |
|---|---|---|
| Uploaded documents | `data/uploads/` | Original files |
| Document embeddings (RAG) | `data/chroma_db/` collection: `rag_documents` | ChromaDB (HNSW) |
| Cross-chat memory embeddings | `data/chroma_db/` collection: `chat_memory` | ChromaDB (HNSW) |
| Session histories | `data/sessions.json` | JSON |
| Document sharing settings | `data/cross_chat_settings.json` | JSON |

> The `data/` directory is auto-created at runtime. It is recommended to add it to `.gitignore` to avoid committing sensitive conversation data or large vector index files.

**Recommended `.gitignore` entries:**

```gitignore
.env
data/
__pycache__/
*.pyc
.venv/
```
