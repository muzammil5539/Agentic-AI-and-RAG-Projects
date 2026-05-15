from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from vector_store.chromadb_store import get_vectorstore, get_retriever
from config import settings

_bm25_retriever = None
_ensemble_retriever = None


def build_bm25_retriever():
    global _bm25_retriever
    store = get_vectorstore()
    all_data = store.get(include=["documents", "metadatas"])

    if not all_data["documents"]:
        return None

    docs = []
    for text, meta in zip(all_data["documents"], all_data["metadatas"]):
        docs.append(Document(page_content=text, metadata=meta))

    _bm25_retriever = BM25Retriever.from_documents(docs, k=settings.BM25_SEARCH_K)
    return _bm25_retriever


def get_ensemble_retriever():
    global _ensemble_retriever
    vector_retriever = get_retriever(search_k=settings.VECTOR_SEARCH_K)
    bm25 = build_bm25_retriever()

    if bm25 is None:
        return vector_retriever

    _ensemble_retriever = EnsembleRetriever(
        retrievers=[vector_retriever, bm25],
        weights=[settings.VECTOR_WEIGHT, settings.BM25_WEIGHT],
    )
    return _ensemble_retriever


def refresh_bm25():
    global _ensemble_retriever
    _ensemble_retriever = None
