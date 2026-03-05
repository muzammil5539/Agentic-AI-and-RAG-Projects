"""
Cross-chat (global) document sharing settings.

Documents marked as "shared" are pinned as part of the global knowledge base
and will always be included in retrieval context regardless of which chat
session is active.

Documents NOT marked as shared are still searchable (they exist in the same
vector store), but the UI distinguishes them clearly so users know which docs
are "global" vs. session-local.
"""

import json
from pathlib import Path

CROSS_CHAT_FILE = Path(__file__).parent.parent / "data" / "cross_chat_settings.json"


class CrossChatStore:
    def __init__(self):
        self._shared_docs: set[str] = set()
        self._load()

    # ------------------------------------------------------------------ I/O --
    def _load(self) -> None:
        if CROSS_CHAT_FILE.exists():
            try:
                with open(CROSS_CHAT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._shared_docs = set(data.get("shared_documents", []))
            except Exception:
                self._shared_docs = set()

    def _save(self) -> None:
        CROSS_CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CROSS_CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"shared_documents": sorted(self._shared_docs)},
                f,
                indent=2,
                ensure_ascii=False,
            )

    # ------------------------------------------------------- Public API ------
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
        """Called when a document is deleted from the vector store."""
        self._shared_docs.discard(filename)
        self._save()


# Singleton
cross_chat_store = CrossChatStore()
