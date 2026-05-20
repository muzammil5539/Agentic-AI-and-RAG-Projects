# 🤖 Conversational AI Agent

> **Project 3** in the AI Engineering Universe — a ReAct-style AI agent with tool calling, visible thought process, and real-time streaming.

## Architecture

```
┌─────────────────────────────────────────────┐
│          Next.js Frontend (Port 3000)        │
│  Chat UI • Thinking Panel • Model Selector  │
│           WebSocket + REST API               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         FastAPI Backend (Port 8002)          │
│  REST /api/v1/* • WebSocket /ws/chat        │
│  Auth: X-API-Key header (user's OpenAI key) │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│         LangGraph ReAct Agent               │
│  StateGraph: agent → tools → agent → END    │
│  SQLite Checkpointer (persistent memory)    │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┼──────────────┐
    │             │              │
┌───▼──┐   ┌─────▼────┐   ┌────▼────┐
│Custom │   │  OpenAI  │   │  Chroma │
│Tools  │   │ Built-in │   │  RAG    │
│       │   │  Tools   │   │        │
└───────┘   └──────────┘   └────────┘
```

## Features

- **ReAct Agent**: Reasons step-by-step, calls tools, reflects on results
- **6 Tools**: Calculator, Weather, DateTime, Web Search, Code Interpreter, RAG Search
- **Visible Thought Process**: Collapsible panel showing Thought → Tool Call → Observation → Answer
- **Real-time Streaming**: WebSocket streaming with token-by-token output
- **Session Management**: Persistent chat history via SQLite checkpointer
- **User-selectable Models**: Switch between gpt-4o-mini, gpt-4o, gpt-4.1, o4-mini
- **Document Upload**: Upload files for RAG search via Chroma vector DB
- **Modern UI**: Dark theme, responsive design, markdown rendering

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Orchestration** | LangGraph (StateGraph, ReAct pattern) |
| **Backend** | FastAPI + Uvicorn (REST + WebSocket) |
| **Frontend** | Next.js 16 + TypeScript + Tailwind CSS |
| **State Management** | Zustand (persisted to localStorage) |
| **LLM** | OpenAI (gpt-4o-mini, gpt-4o, gpt-4.1) |
| **Memory** | LangGraph SQLite Checkpointer |
| **Vector DB** | ChromaDB (for RAG search tool) |
| **Validation** | Pydantic v2 (everywhere) |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- OpenAI API key

### 1. Backend Setup

```bash
cd projects/beginner/conversational-ai-agent

# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
# → Running at http://localhost:8002
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# → Running at http://localhost:3000
```

### 3. Use the App

1. Open http://localhost:3000
2. Click **Settings** in the sidebar
3. Enter your OpenAI API key
4. Select a model (default: gpt-4o-mini)
5. Start chatting!

## API Reference

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check with available models |
| `GET` | `/api/v1/tools` | List all available tools |
| `POST` | `/api/v1/chat` | Send message (non-streaming) |
| `GET` | `/api/v1/sessions` | List user sessions |
| `POST` | `/api/v1/sessions` | Create new session |
| `GET` | `/api/v1/sessions/:id` | Get session details |
| `PATCH` | `/api/v1/sessions/:id` | Update session title |
| `DELETE` | `/api/v1/sessions/:id` | Delete session |
| `POST` | `/api/v1/documents/upload` | Upload document for RAG |

### WebSocket

Connect to `ws://localhost:8002/ws/chat`

**Send:**
```json
{
  "type": "chat",
  "query": "What's the weather in London?",
  "session_id": null,
  "model": "gpt-4o-mini",
  "api_key": "sk-..."
}
```

**Receive (stream of events):**
```json
{"type": "thought", "content": "I need to check the weather..."}
{"type": "tool_call", "tool_name": "weather", "tool_args": {"location": "London"}}
{"type": "tool_result", "tool_name": "weather", "content": "Temperature: 15°C..."}
{"type": "token", "content": "The"}
{"type": "token", "content": " weather"}
{"type": "done", "session_id": "abc123", "model": "gpt-4o-mini"}
```

## Tools

| Tool | Type | Description |
|------|------|-------------|
| **Calculator** | Custom | Safe math evaluation (arithmetic, sqrt, log, trig) |
| **Weather** | Custom | Current weather + 3-day forecast via Open-Meteo API |
| **DateTime** | Custom | Current time, timezone conversion, date arithmetic |
| **Web Search** | OpenAI | Web search via OpenAI's built-in capability |
| **Code Interpreter** | OpenAI | Python code execution via OpenAI |
| **RAG Search** | Custom | Semantic search on uploaded documents via Chroma |

## Project Structure

```
conversational-ai-agent/
├── main.py                    # FastAPI app entry point
├── config.py                  # Pydantic BaseSettings
├── requirements.txt
├── agent/                     # LangGraph ReAct agent
│   ├── graph.py               # StateGraph definition
│   ├── state.py               # Agent state schema
│   ├── nodes.py               # Graph nodes (agent, tools)
│   └── prompts.py             # System prompts
├── tools/                     # Agent tools
│   ├── registry.py            # Tool catalog
│   ├── calculator.py          # Math evaluator
│   ├── weather.py             # Open-Meteo integration
│   ├── datetime_tool.py       # Date/time utility
│   ├── web_search.py          # OpenAI web search
│   ├── code_interpreter.py    # OpenAI code interpreter
│   └── rag_search.py          # Chroma vector search
├── api/                       # FastAPI routes & models
│   ├── routes/                # Endpoint handlers
│   ├── models/                # Pydantic schemas
│   └── dependencies.py        # DI (auth, checkpointer)
├── services/                  # Business logic layer
│   ├── agent_service.py       # Graph invocation & streaming
│   └── session_service.py     # Session CRUD
├── memory/                    # Persistence
│   ├── checkpointer.py        # SQLite checkpointer
│   └── session_store.py       # Session metadata (JSON)
├── tests/                     # Test suite (32 tests)
└── frontend/                  # Next.js app
    └── src/
        ├── app/               # App router pages
        ├── components/        # React components
        │   ├── chat/          # ChatContainer, MessageBubble, ThinkingPanel
        │   ├── sidebar/       # Sidebar, SessionList
        │   └── settings/      # ModelSelector, ApiKeyInput
        ├── stores/            # Zustand state management
        └── lib/               # API client, WebSocket, types
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# 32 tests covering:
# - Calculator (10 tests): arithmetic, functions, edge cases
# - DateTime (7 tests): now, convert, add, diff, list
# - API (7 tests): health, tools, sessions, auth
# - Agent (5 tests): routing, compilation, state schema
# - Chat auth (2 tests): missing/invalid API key
```

## Security

- **API key never stored server-side** — forwarded to OpenAI per-request only
- SHA-256 hash of API key used as `user_id` for session isolation
- Safe math evaluation via AST parsing (no `eval`)
- Pydantic validation on all inputs
- Session access control (user can only see their own sessions)
