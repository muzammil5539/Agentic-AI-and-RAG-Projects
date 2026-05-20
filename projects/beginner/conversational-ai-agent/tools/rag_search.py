"""RAG Search tool — similarity search against Chroma vector store."""

from __future__ import annotations

from typing import Annotated, Optional

import chromadb
from langchain_core.tools import tool

from config import settings

_client: Optional[chromadb.HttpClient] = None


def _get_chroma_client() -> chromadb.HttpClient:
    """Lazy-init a persistent Chroma HTTP client."""
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.CHROMA_URL.replace("http://", "").split(":")[0],
            port=int(settings.CHROMA_URL.split(":")[-1]),
        )
    return _client


@tool
def rag_search(
    query: Annotated[str, "The search query to find relevant documents"],
    collection_name: Annotated[str, "Chroma collection to search in"] = "agent_docs",
    top_k: Annotated[int, "Number of results to return (1-10)"] = 5,
) -> str:
    """Search uploaded documents for relevant information.

    This searches a Chroma vector database for document chunks that are
    semantically similar to the query. Use this when the user asks about
    content from documents they've uploaded.

    Returns the most relevant text passages with their source metadata.
    """
    try:
        client = _get_chroma_client()
        collection = client.get_or_create_collection(name=collection_name)

        if collection.count() == 0:
            return "No documents have been uploaded yet. Ask the user to upload documents first."

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, 10),
        )

        if not results["documents"] or not results["documents"][0]:
            return f"No relevant results found for: '{query}'"

        chunks = []
        docs = results["documents"][0]
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for i, (doc, meta, dist) in enumerate(zip(docs, metadatas, distances), 1):
            source = meta.get("source", "unknown")
            page = meta.get("page", "?")
            chunks.append(
                f"[{i}] (source: {source}, page: {page}, score: {1 - dist:.3f})\n{doc}"
            )

        return f"Found {len(chunks)} relevant passages:\n\n" + "\n\n---\n\n".join(chunks)

    except Exception as e:
        return f"RAG search error: {e}. Is Chroma running at {settings.CHROMA_URL}?"
