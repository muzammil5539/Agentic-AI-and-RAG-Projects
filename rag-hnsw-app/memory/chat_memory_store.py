"""
Cross-Chat (Inter-Chat) Memory Store
=====================================

Architecture
------------
Memory Type 1 — In-Chat Memory  : per-session multi-turn history (SessionStore).
Memory Type 2 — Cross-Chat Memory: this module.

Every completed conversation is automatically summarised by an LLM and the
summary is stored as a vector embedding in a dedicated ChromaDB collection
("chat_memory").  When a new query arrives the collection is searched
semantically so that relevant context from *past* conversations can be
injected into the prompt – giving the assistant awareness across sessions.

Storage layout
--------------
ChromaDB collection : "chat_memory"
Document ID format  : "cm_<session_id>"     (one entry per session)
Document content    : LLM-generated summary (200–400 words)
Metadata fields     : session_id, session_title, message_count, archived_at

Public API
----------
chat_memory_store.summarize_and_store(session_id, title, messages)
    → summarises the session with an LLM and upserts it into the collection.

chat_memory_store.search_relevant(query, k=3)
    → returns up to k Document objects whose summaries are most similar
      to `query`.

chat_memory_store.list_all()
    → returns all stored summaries as a list of dicts (for the UI).

chat_memory_store.delete_by_session(session_id)
    → removes the stored memory for one session.

chat_memory_store.get_count()
    → number of summaries currently stored.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHAT_MEMORY_COLLECTION = "chat_memory"
_ID_PREFIX = "cm_"

# ---------------------------------------------------------------------------
# Summarisation prompt
# ---------------------------------------------------------------------------
_SUMMARISE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are a conversation archivist. "
            "Your sole task is to produce a dense, semantically rich summary of "
            "the conversation below so it can be stored in a vector database and "
            "retrieved in future sessions.\n\n"
            "Include:\n"
            "  - Main topics and themes discussed\n"
            "  - Every question the user asked\n"
            "  - Key answers, facts, and decisions\n"
            "  - Any unresolved questions or follow-up items\n\n"
            "Write 200–400 words. Use plain prose — no bullet lists, no headers. "
            "Do NOT add commentary; only summarise what was actually said."
        ),
    ),
    (
        "human",
        "Conversation to summarise:\n\n{conversation}\n\nSummary:",
    ),
])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_conversation(messages: list[dict]) -> str:
    """Convert stored message dicts to a readable transcript."""
    lines = []
    for msg in messages:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def _doc_id(session_id: str) -> str:
    return f"{_ID_PREFIX}{session_id}"


# ---------------------------------------------------------------------------
# ChatMemoryStore
# ---------------------------------------------------------------------------

class ChatMemoryStore:
    """
    Manages long-term cross-chat memory backed by a dedicated ChromaDB
    collection.  One summary entry per session; upserted on archive so
    re-archiving a session always reflects the latest state.
    """

    def __init__(self) -> None:
        self._embeddings = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        # Separate collection from the document RAG store
        self._store = Chroma(
            collection_name=CHAT_MEMORY_COLLECTION,
            embedding_function=self._embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def summarize_and_store(
        self,
        session_id: str,
        session_title: str,
        messages: list[dict],
    ) -> Optional[str]:
        """
        Summarise a conversation with an LLM and upsert its embedding.

        Returns the summary text so callers can log or display it.
        Returns None if `messages` is empty (nothing to archive).
        """
        if not messages:
            return None

        conversation_text = _format_conversation(messages)
        if not conversation_text.strip():
            return None

        try:
            llm = ChatOpenAI(
                model=settings.OPENAI_CHAT_MODEL,
                temperature=0.0,
                openai_api_key=settings.OPENAI_API_KEY,
            )
            chain = _SUMMARISE_PROMPT | llm
            response = chain.invoke({"conversation": conversation_text})
            summary = response.content.strip()
        except Exception as exc:
            logger.warning("ChatMemoryStore: summarisation failed – %s", exc)
            # Fallback: store the raw transcript (truncated) so at least
            # something is persisted.
            summary = conversation_text[:2000]

        # Upsert: delete old entry then add fresh one
        self.delete_by_session(session_id)

        doc = Document(
            page_content=summary,
            metadata={
                "session_id": session_id,
                "session_title": session_title or "Untitled Chat",
                "message_count": len(messages),
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "type": "chat_summary",
            },
        )
        self._store.add_documents([doc], ids=[_doc_id(session_id)])
        logger.info(
            "ChatMemoryStore: archived session '%s' (%d messages)",
            session_title, len(messages),
        )
        return summary

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search_relevant(self, query: str, k: int = 3) -> list[Document]:
        """
        Semantic search over stored conversation summaries.
        Returns up to *k* most relevant Document objects.
        Returns [] if the collection is empty or the search fails.
        """
        try:
            count = self.get_count()
            if count == 0:
                return []
            actual_k = min(k, count)
            return self._store.similarity_search(query, k=actual_k)
        except Exception as exc:
            logger.warning("ChatMemoryStore: search failed – %s", exc)
            return []

    def list_all(self) -> list[dict]:
        """
        Return every stored summary as a plain dict for the REST API / UI.
        Sorted by archived_at descending (most recent first).
        """
        try:
            data = self._store.get(include=["documents", "metadatas"])
            results: list[dict] = []
            for doc_id, content, meta in zip(
                data["ids"],
                data["documents"],
                data["metadatas"],
            ):
                results.append({
                    "id": doc_id,
                    "session_id": meta.get("session_id", ""),
                    "session_title": meta.get("session_title", "Untitled Chat"),
                    "summary": content,
                    "message_count": meta.get("message_count", 0),
                    "archived_at": meta.get("archived_at", ""),
                })
            results.sort(key=lambda x: x["archived_at"], reverse=True)
            return results
        except Exception as exc:
            logger.warning("ChatMemoryStore: list_all failed – %s", exc)
            return []

    def get_by_session(self, session_id: str) -> Optional[dict]:
        """Retrieve the stored memory entry for a specific session."""
        all_entries = self.list_all()
        for entry in all_entries:
            if entry["session_id"] == session_id:
                return entry
        return None

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_by_session(self, session_id: str) -> bool:
        """
        Remove the stored memory for a session.
        Safe to call even if no entry exists.
        """
        try:
            self._store.delete(ids=[_doc_id(session_id)])
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_count(self) -> int:
        """Number of archived conversation summaries."""
        try:
            data = self._store.get()
            return len(data["ids"])
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
chat_memory_store = ChatMemoryStore()
