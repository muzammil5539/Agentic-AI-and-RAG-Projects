from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from config import settings

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an expert AI assistant for a Retrieval-Augmented Generation (RAG) system \
built with LangChain. You specialize in answering questions by grounding every \
response in the retrieved knowledge sources provided below.

## Role & Expertise
- Retrieval-Augmented Generation (RAG) and LangChain pipelines
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
semantically relevant to the current question.  Use them to provide continuity \
and to answer questions that reference earlier conversations.  When you draw on \
one of these past sessions, explicitly acknowledge it:
> "Based on our previous conversation about [topic]..."

{cross_chat_context}

---

## Current Document Context  (Live Retrieval)
{context}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_cross_chat_context(docs: list[Document]) -> str:
    """Format retrieved past-conversation summaries for the prompt."""
    if not docs:
        return "No relevant past conversations found."
    parts = []
    for i, doc in enumerate(docs):
        meta  = doc.metadata
        title = meta.get("session_title", "Untitled Chat")
        ts    = meta.get("archived_at", "")[:10]   # YYYY-MM-DD
        count = meta.get("message_count", "?")
        header = (
            f"[Past Session {i + 1} | Title: {title} "
            f"| Date: {ts} | Messages: {count}]"
        )
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def format_context(docs: list[Document]) -> str:
    if not docs:
        return "No relevant documents were retrieved."
    parts = []
    for i, doc in enumerate(docs):
        filename = doc.metadata.get("source_filename", "Unknown")
        page = doc.metadata.get("page", "N/A")
        chunk_idx = doc.metadata.get("chunk_index", "N/A")
        header = (
            f"[Document {i + 1} | Source: {filename} "
            f"| Page: {page} | Chunk: {chunk_idx}]"
        )
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def build_cross_chat_refs(docs: list[Document]) -> list[dict]:
    """Return lightweight metadata about which past sessions were retrieved."""
    refs = []
    for doc in docs:
        meta = doc.metadata
        refs.append({
            "session_id":    meta.get("session_id", ""),
            "session_title": meta.get("session_title", "Untitled Chat"),
            "archived_at":   meta.get("archived_at", "")[:10],
            "snippet":       doc.page_content[:200] + ("..." if len(doc.page_content) > 200 else ""),
        })
    return refs


def build_source_list(docs: list[Document]) -> list[dict]:
    sources = []
    seen: set[str] = set()
    for doc in docs:
        filename = doc.metadata.get("source_filename", "Unknown")
        page = doc.metadata.get("page", "N/A")
        chunk_idx = doc.metadata.get("chunk_index", "N/A")
        key = f"{filename}_{page}_{chunk_idx}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "filename": filename,
                "page": page,
                "chunk_index": chunk_idx,
                "snippet": (
                    doc.page_content[:200] + "..."
                    if len(doc.page_content) > 200
                    else doc.page_content
                ),
            })
    return sources


def _build_history_messages(history: list[dict]) -> list:
    """
    Convert stored chat history dicts to LangChain message objects.

    Using concrete message objects (HumanMessage / AIMessage) instead of
    (role, string) tuples is critical: ChatPromptTemplate would try to
    format raw string tuples as templates, which breaks whenever past
    messages contain curly braces (e.g. code, JSON, citations).
    """
    result = []
    for msg in history:
        role    = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            result.append(HumanMessage(content=content))
        elif role == "assistant":
            result.append(AIMessage(content=content))
    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_answer(
    question: str,
    retrieved_docs: list[Document],
    chat_history: list[dict] | None = None,
    cross_chat_docs: list[Document] | None = None,
) -> dict:
    """
    Generate an answer using the RAG chain with optional multi-turn history.

    Parameters
    ----------
    question : str
        The current user question.
    retrieved_docs : list[Document]
        Documents returned by the retriever for this query.
    chat_history : list[dict] | None
        List of ``{"role": "user"|"assistant", "content": str}`` dicts
        representing the conversation history for the current session.
    """
    llm = ChatOpenAI(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    context            = format_context(retrieved_docs)
    cross_chat_context = format_cross_chat_context(cross_chat_docs or [])
    history_msgs       = _build_history_messages(chat_history or [])

    # MessagesPlaceholder safely expands HumanMessage/AIMessage objects into
    # the prompt without treating their content as format templates.
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    chain    = prompt | llm
    response = chain.invoke({
        "context":            context,
        "cross_chat_context": cross_chat_context,
        "question":           question,
        "chat_history":       history_msgs,
    })

    return {
        "answer":           response.content,
        "sources":          build_source_list(retrieved_docs),
        "cross_chat_refs":  build_cross_chat_refs(cross_chat_docs or []),
    }
