from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from config import settings

_embedding_fn = None
_vectorstore = None


def get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = OpenAIEmbeddings(
            model=settings.OPENAI_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
    return _embedding_fn


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=get_embedding_function(),
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_metadata={
                "hnsw:space": settings.HNSW_SPACE,
                "hnsw:construction_ef": settings.HNSW_EF_CONSTRUCTION,
                "hnsw:search_ef": settings.HNSW_EF_SEARCH,
                "hnsw:M": settings.HNSW_MAX_NEIGHBORS,
            },
        )
    return _vectorstore


def add_documents(chunks: list):
    store = get_vectorstore()
    store.add_documents(chunks)


def get_retriever(search_k: int = None):
    k = search_k or settings.VECTOR_SEARCH_K
    return get_vectorstore().as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
