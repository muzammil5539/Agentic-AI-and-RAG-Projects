"""
Multi-Query Retrieval — LLM generates query variants, retrieve for each, merge via RRF.
No LangChain. Direct OpenAI calls.
"""

import json
from openai import OpenAI
from config import settings
from indexing.openai_embeddings import embed_query
from retrieval.hybrid_search import hybrid_search, reciprocal_rank_fusion


def generate_query_variants(query: str, n: int = 3) -> list[str]:
    """Ask the LLM to generate n alternative phrasings of the query."""
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=0.7,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate alternative search queries for a RAG system. "
                    "Given a user question, produce exactly {n} different phrasings "
                    "that capture the same intent but use different words/angles. "
                    "Return ONLY a JSON array of strings, no explanation."
                ).format(n=n),
            },
            {
                "role": "user",
                "content": f"Original query: {query}\n\nGenerate {n} alternative search queries:",
            },
        ],
    )

    text = response.choices[0].message.content.strip()
    # Parse JSON array from response
    try:
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        variants = json.loads(text)
        if isinstance(variants, list):
            return [str(v) for v in variants[:n]]
    except (json.JSONDecodeError, IndexError):
        pass

    # Fallback: split by newlines
    lines = [l.strip().lstrip("0123456789.-) ") for l in text.split("\n") if l.strip()]
    return lines[:n] if lines else [query]


def multi_query_search(
    query: str,
    n_variants: int = 3,
    vector_k: int = 5,
    bm25_k: int = 5,
    top_k: int = 5,
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
    merge_method: str = "weighted",
    method_override: str | None = None,
) -> dict:
    """
    Generate query variants → retrieve for each → merge via RRF.

    Returns:
        {
            "results": [merged results],
            "variants": [generated query variants],
            "per_variant_counts": [int],
            ...hybrid diagnostics
        }
    """
    variants = generate_query_variants(query, n_variants)

    # Collect all result lists for RRF fusion across variants
    all_result_lists = []
    per_variant_counts = []

    for variant in variants:
        result = hybrid_search(
            query=variant,
            vector_k=vector_k,
            bm25_k=bm25_k,
            top_k=top_k * 2,  # get more per variant, merge later
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            merge_method=merge_method,
            method_override=method_override,
        )
        all_result_lists.append(result["results"])
        per_variant_counts.append(len(result["results"]))

    # Also search with original query
    original_result = hybrid_search(
        query=query,
        vector_k=vector_k,
        bm25_k=bm25_k,
        top_k=top_k * 2,
        vector_weight=vector_weight,
        bm25_weight=bm25_weight,
        merge_method=merge_method,
        method_override=method_override,
    )
    all_result_lists.append(original_result["results"])

    # RRF merge across all variant results
    # Convert dicts to objects for RRF
    class _R:
        def __init__(self, d):
            self.id = d["id"]
            self.content = d["content"]
            self.metadata = d["metadata"]
            self.score = d.get("combined_score", 0)

    obj_lists = [[_R(d) for d in rlist] for rlist in all_result_lists]
    merged = reciprocal_rank_fusion(*obj_lists)

    return {
        "results": merged[:top_k],
        "variants": variants,
        "per_variant_counts": per_variant_counts,
        "total_candidates": sum(per_variant_counts) + len(original_result["results"]),
        "merge_method": "rrf_multi_query",
    }
