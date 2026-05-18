"""
LLM generation chain — direct OpenAI calls, no LangChain.
System prompt with grounding rules, citation format, cross-chat memory injection.
"""

from openai import OpenAI
from config import settings

SYSTEM_PROMPT = """\
You are an expert AI assistant for a Retrieval-Augmented Generation (RAG) system \
built entirely from scratch — no LangChain, no ChromaDB. Pure Python implementations \
of vector search, BM25, HNSW, and hybrid retrieval.

## Role & Expertise
- Retrieval-Augmented Generation (RAG) pipelines
- Vector databases, embeddings, and semantic search
- Context-aware reasoning from documents
- FastAPI backends and modern AI application architecture

---

## Core Behavioural Rules

### Grounding Rule
Always prioritise information retrieved from the knowledge base.
- Use retrieved context as the PRIMARY source of truth.
- If the answer exists in the retrieved documents, base the answer entirely on them.

### No-Hallucination Rule
If the provided context does not contain sufficient information:
- Clearly state: "The retrieved documents do not contain enough information to \
answer this question."
- Do NOT fabricate answers, citations, or documentation.

### Context Priority Order
1. Retrieved documents (RAG context)
2. Conversation history
3. General reasoning (only when retrieval is insufficient and clearly flagged)

---

## Answer Generation Guidelines
- Be concise but complete.
- Use structured explanations when appropriate.
- Prefer **bullet points** for multi-item answers.
- Use **headings** for complex responses.
- Keep responses visually scannable — avoid long unstructured paragraphs.

---

## Citation Rules
1. For every factual claim add an inline citation: [Source: filename, Chunk: N]
2. At the end of your answer include a **References** section listing filename, \
page, and chunk for every source used.
3. If no relevant documents were retrieved, do NOT invent citations.

---

## Handling Ambiguous Questions
If a question is unclear, ask for clarification before answering:
> "Could you clarify whether you are asking about X or Y?"

---

## Multi-Turn Conversation Awareness
You HAVE access to the full conversation history of this chat session.
It is injected directly above the current question as real messages.
- Reference and build on previous exchanges when relevant.
- If the user asks "what were we discussing?" or similar, summarise the
  conversation history that is visible to you.
- Never claim you lack access to past messages — they are provided above.
- Avoid repeating previously given answers verbatim.

---

## Failure Response
If retrieval returns empty or irrelevant context respond with:
> "I couldn't find relevant information in the knowledge base. \
Please rephrase your question or upload additional documents."

---

## Cross-Chat Memory  (Past Conversation Summaries)
The following are LLM-generated summaries of previous chat sessions that are \
semantically relevant to the current question. Use them to provide continuity \
and to answer questions that reference earlier conversations. When you draw on \
one of these past sessions, explicitly acknowledge it:
> "Based on our previous conversation about [topic]..."

{cross_chat_context}

---

## Current Document Context  (Live Retrieval)
{context}
"""


def format_context(docs: list[dict]) -> str:
    if not docs:
        return "No relevant documents were retrieved."
    parts = []
    for i, doc in enumerate(docs):
        meta = doc.get("metadata", {})
        filename = meta.get("source_filename", "Unknown")
        page = meta.get("page", "N/A")
        chunk_idx = meta.get("chunk_index", "N/A")
        header = f"[Document {i + 1} | Source: {filename} | Page: {page} | Chunk: {chunk_idx}]"
        parts.append(f"{header}\n{doc['content']}")
    return "\n\n---\n\n".join(parts)


def format_cross_chat_context(docs: list[dict]) -> str:
    if not docs:
        return "No relevant past conversations found."
    parts = []
    for i, doc in enumerate(docs):
        meta = doc.get("metadata", {})
        title = meta.get("session_title", "Untitled Chat")
        ts = meta.get("archived_at", "")[:10]
        count = meta.get("message_count", "?")
        header = f"[Past Session {i + 1} | Title: {title} | Date: {ts} | Messages: {count}]"
        parts.append(f"{header}\n{doc['content']}")
    return "\n\n---\n\n".join(parts)


def build_messages(
    question: str,
    context_docs: list[dict],
    chat_history: list[dict],
    cross_chat_docs: list[dict],
) -> list[dict]:
    context_str = format_context(context_docs)
    cross_chat_str = format_cross_chat_context(cross_chat_docs)

    system_content = SYSTEM_PROMPT.format(
        context=context_str,
        cross_chat_context=cross_chat_str,
    )

    messages = [{"role": "system", "content": system_content}]

    # Add chat history
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Add current question
    messages.append({"role": "user", "content": question})
    return messages


def build_source_list(context_docs: list[dict]) -> list[dict]:
    sources = []
    seen = set()
    for doc in context_docs:
        meta = doc.get("metadata", {})
        key = (meta.get("source_filename", ""), meta.get("chunk_index", ""))
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "filename": meta.get("source_filename", "Unknown"),
            "page": meta.get("page", "N/A"),
            "chunk_index": meta.get("chunk_index", "N/A"),
            "snippet": doc["content"][:200] + ("..." if len(doc["content"]) > 200 else ""),
        })
    return sources


def build_cross_chat_refs(cross_chat_docs: list[dict]) -> list[dict]:
    refs = []
    for doc in cross_chat_docs:
        meta = doc.get("metadata", {})
        refs.append({
            "session_id": meta.get("session_id", ""),
            "session_title": meta.get("session_title", "Untitled Chat"),
            "archived_at": meta.get("archived_at", "")[:10],
            "snippet": doc["content"][:200] + ("..." if len(doc["content"]) > 200 else ""),
        })
    return refs


def generate_answer(
    question: str,
    context_docs: list[dict],
    chat_history: list[dict],
    cross_chat_docs: list[dict],
    temperature: float = 0.1,
) -> dict:
    """
    Generate an answer using direct OpenAI API.
    Returns: {"answer": str, "sources": list, "cross_chat_refs": list}
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    messages = build_messages(question, context_docs, chat_history, cross_chat_docs)

    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=temperature,
        messages=messages,
    )

    answer = response.choices[0].message.content.strip()
    sources = build_source_list(context_docs)
    cross_refs = build_cross_chat_refs(cross_chat_docs)

    return {
        "answer": answer,
        "sources": sources,
        "cross_chat_refs": cross_refs,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    }
