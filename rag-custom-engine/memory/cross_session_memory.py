"""
Cross-chat memory + document sharing settings.
- Conversation summaries: stored in the vector store (namespaced)
- Document sharing flags: JSON persisted

No LangChain, no ChromaDB. Uses our from-scratch vector store.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from openai import OpenAI
from config import settings
from indexing.openai_embeddings import embed_texts
from indexing.hnsw_vector_store import get_vector_store

MEMORY_NAMESPACE = "mem_"


def _format_conversation(messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        role = "User" if msg.get("role") == "user" else "Assistant"
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


class ChatMemoryStore:
    """Manages cross-chat memory: LLM-summarized conversations stored as embeddings."""

    def __init__(self):
        self._store = get_vector_store()

    def summarize_and_store(
        self,
        session_id: str,
        session_title: str,
        messages: list[dict],
    ) -> Optional[str]:
        if not messages:
            return None

        conversation_text = _format_conversation(messages)
        if not conversation_text.strip():
            return None

        # Summarize with LLM
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a conversation archivist. "
                        "Produce a dense, semantically rich summary of the conversation below "
                        "so it can be stored in a vector database and retrieved in future sessions.\n\n"
                        "Include:\n"
                        "  - Main topics and themes discussed\n"
                        "  - Every question the user asked\n"
                        "  - Key answers, facts, and decisions\n"
                        "  - Any unresolved questions or follow-up items\n\n"
                        "Write 200-400 words. Use plain prose. Do NOT add commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Conversation to summarise:\n\n{conversation_text}\n\nSummary:",
                },
            ],
        )

        summary = response.choices[0].message.content.strip()

        # Delete old entry if exists (upsert)
        doc_id = f"{MEMORY_NAMESPACE}cm_{session_id}"
        self._store.delete_by_ids([doc_id])

        # Embed and store
        embedding = embed_texts([summary])[0]
        metadata = {
            "session_id": session_id,
            "session_title": session_title,
            "message_count": len(messages),
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "type": "chat_memory",
        }

        self._store.add(
            vectors=[embedding],
            contents=[summary],
            metadatas=[metadata],
            ids=[doc_id],
        )

        return summary

    def search_relevant(self, query: str, k: int = 3) -> list[dict]:
        from indexing.openai_embeddings import embed_query
        query_vec = embed_query(query)
        results = self._store.search(query_vec, k=k, namespace=MEMORY_NAMESPACE)
        return [
            {"content": r.content, "metadata": r.metadata, "score": r.score}
            for r in results
            if r.metadata.get("type") == "chat_memory"
        ]

    def list_all(self) -> list[dict]:
        entries = self._store.get_all(namespace=MEMORY_NAMESPACE)
        result = []
        for e in entries:
            if e.metadata.get("type") == "chat_memory":
                result.append({
                    "id": e.id,
                    "session_id": e.metadata.get("session_id", ""),
                    "session_title": e.metadata.get("session_title", "Untitled"),
                    "summary": e.content,
                    "message_count": e.metadata.get("message_count", 0),
                    "archived_at": e.metadata.get("archived_at", ""),
                })
        result.sort(key=lambda x: x["archived_at"], reverse=True)
        return result

    def delete_by_session(self, session_id: str) -> bool:
        doc_id = f"{MEMORY_NAMESPACE}cm_{session_id}"
        count = self._store.delete_by_ids([doc_id])
        return count > 0

    def get_count(self) -> int:
        return len(self.list_all())


class CrossChatDocStore:
    """Document sharing flags — JSON persisted."""

    def __init__(self):
        self._shared_docs: set[str] = set()
        self._path = Path(settings.CROSS_CHAT_FILE)
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._shared_docs = set(data.get("shared_documents", []))
            except Exception:
                self._shared_docs = set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(self._path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"shared_documents": sorted(self._shared_docs)},
                f, indent=2, ensure_ascii=False,
            )
        Path(tmp).replace(self._path)

    def set_shared(self, filename: str, shared: bool) -> None:
        if shared:
            self._shared_docs.add(filename)
        else:
            self._shared_docs.discard(filename)
        self._save()

    def is_shared(self, filename: str) -> bool:
        return filename in self._shared_docs

    def get_shared_documents(self) -> list[str]:
        return sorted(self._shared_docs)

    def remove_document(self, filename: str) -> None:
        self._shared_docs.discard(filename)
        self._save()


# Singletons — lazy init to avoid circular imports
_chat_memory_store: Optional[ChatMemoryStore] = None
_cross_chat_doc_store: Optional[CrossChatDocStore] = None


def get_chat_memory_store() -> ChatMemoryStore:
    global _chat_memory_store
    if _chat_memory_store is None:
        _chat_memory_store = ChatMemoryStore()
    return _chat_memory_store


def get_cross_chat_doc_store() -> CrossChatDocStore:
    global _cross_chat_doc_store
    if _cross_chat_doc_store is None:
        _cross_chat_doc_store = CrossChatDocStore()
    return _cross_chat_doc_store
