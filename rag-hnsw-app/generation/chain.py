from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from config import settings

SYSTEM_PROMPT = """You are a helpful research assistant. Answer the user's question \
based ONLY on the provided context. If the context does not contain enough information \
to answer the question, say so explicitly -- do not make up information.

IMPORTANT CITATION RULES:
1. For every claim or piece of information, add an inline citation in the format \
[Source: filename, Page/Chunk: N].
2. At the end of your answer, include a "References" section listing all sources used \
with their filenames and page/chunk numbers.

Context:
{context}
"""

USER_PROMPT = """{question}"""


def format_context(docs: list[Document]) -> str:
    parts = []
    for i, doc in enumerate(docs):
        filename = doc.metadata.get("source_filename", "Unknown")
        page = doc.metadata.get("page", "N/A")
        chunk_idx = doc.metadata.get("chunk_index", "N/A")
        header = f"[Document {i+1} | Source: {filename} | Page: {page} | Chunk: {chunk_idx}]"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def build_source_list(docs: list[Document]) -> list[dict]:
    sources = []
    seen = set()
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
                "snippet": (doc.page_content[:200] + "...")
                if len(doc.page_content) > 200
                else doc.page_content,
            })
    return sources


def generate_answer(question: str, retrieved_docs: list[Document]) -> dict:
    llm = ChatOpenAI(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.1,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    context = format_context(retrieved_docs)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ])

    chain = prompt | llm
    response = chain.invoke({"context": context, "question": question})

    return {
        "answer": response.content,
        "sources": build_source_list(retrieved_docs),
    }
