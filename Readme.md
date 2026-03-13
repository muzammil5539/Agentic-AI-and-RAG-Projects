# RAG Projects

A collection of **Retrieval-Augmented Generation (RAG)** projects exploring different retrieval strategies, memory architectures, and LLM integration patterns. Each sub-directory is a self-contained project with its own dependencies, configuration, and documentation.

---

## Projects

### 1. RAG HNSW App

> A production-ready conversational document assistant with **hybrid search** (HNSW vector + BM25), a **dual-layer memory system** (in-chat + cross-chat), and a browser-based chat UI — all served by a single FastAPI process.

**Key capabilities:**
- Upload PDF, DOCX, TXT, CSV, or Markdown files and chat with their content
- Hybrid retrieval: ChromaDB HNSW index fused with BM25 via `EnsembleRetriever`
- In-chat memory keeps the last 20 conversation turns in every prompt
- Cross-chat memory summarises closed sessions and semantically searches them on every new query
- Every answer includes inline `[Source: file, Chunk: N]` citations
- Full REST API documented at `/docs`

**Stack:** FastAPI · LangChain · ChromaDB · OpenAI · rank-bm25 · Vanilla JS

→ **[View full documentation](rag-hnsw-app/README.md)**

---

<!-- Add new projects below in the same format:

### N. Project Name
> One-line description.

...highlights...

→ **[View full documentation](project-folder/README.md)**

---
-->

## Repository Layout

```
RAG/
├── Readme.md              ← you are here
└── rag-hnsw-app/          ← Project 1: RAG HNSW App
```
