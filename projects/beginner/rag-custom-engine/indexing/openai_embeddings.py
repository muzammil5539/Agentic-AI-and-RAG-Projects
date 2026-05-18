"""
OpenAI embeddings wrapper — direct API calls, no LangChain.
Supports batch embedding with retry/backoff.
"""

import time
from openai import OpenAI
from config import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    client = _get_client()
    model = model or settings.OPENAI_EMBEDDING_MODEL
    all_embeddings: list[list[float]] = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for attempt in range(5):
            try:
                response = client.embeddings.create(input=batch, model=model)
                all_embeddings.extend([d.embedding for d in response.data])
                break
            except Exception as e:
                if attempt == 4:
                    raise
                wait = 2 ** attempt
                time.sleep(wait)

    return all_embeddings


def embed_query(text: str, model: str | None = None) -> list[float]:
    return embed_texts([text], model)[0]


def get_embedding_dimension(model: str | None = None) -> int:
    test = embed_query("test", model)
    return len(test)
