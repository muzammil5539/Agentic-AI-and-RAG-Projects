"""
Hybrid retrieval — combines vector search + BM25 via weighted ensemble or RRF.
From scratch, no LangChain ensembles.
"""

from indexing.hnsw_vector_store import get_vector_store, SearchResult
from indexing.bm25_index import get_bm25_index, BM25SearchResult
from indexing.openai_embeddings import embed_query

DOC_NAMESPACE = "doc_"


def _normalize_scores(results: list, max_score: float | None = None) -> list[tuple[str, float, dict]]:
    """Normalize scores to [0, 1] range. Returns list of (id, norm_score, result_dict)."""
    if not results:
        return []
    scores = [r.score for r in results]
    max_s = max_score or max(scores) if scores else 1.0
    min_s = min(scores) if scores else 0.0
    range_s = max_s - min_s if max_s != min_s else 1.0

    out = []
    for r in results:
        norm = (r.score - min_s) / range_s
        out.append((r.id, norm, {
            "id": r.id,
            "content": r.content,
            "metadata": r.metadata,
            "score": r.score,
        }))
    return out


def weighted_ensemble(
    vector_results: list[SearchResult],
    bm25_results: list[BM25SearchResult],
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
) -> list[dict]:
    """Combine results using weighted score normalization."""
    vec_norm = _normalize_scores(vector_results)
    bm25_norm = _normalize_scores(bm25_results)

    combined: dict[str, dict] = {}

    for rid, norm_score, res in vec_norm:
        key = rid.replace(DOC_NAMESPACE, "", 1) if rid.startswith(DOC_NAMESPACE) else rid
        if key not in combined:
            combined[key] = {**res, "combined_score": 0.0, "vector_score": norm_score, "bm25_score": 0.0}
        combined[key]["combined_score"] += norm_score * vector_weight
        combined[key]["vector_score"] = norm_score

    for rid, norm_score, res in bm25_norm:
        key = rid
        if key not in combined:
            combined[key] = {**res, "combined_score": 0.0, "vector_score": 0.0, "bm25_score": norm_score}
        combined[key]["combined_score"] += norm_score * bm25_weight
        combined[key]["bm25_score"] = norm_score

    ranked = sorted(combined.values(), key=lambda x: x["combined_score"], reverse=True)
    return ranked


def reciprocal_rank_fusion(
    *result_lists: list,
    k: int = 60,
) -> list[dict]:
    """
    Combine multiple ranked lists using RRF.
    RRF_score(d) = Σ 1/(k + rank_i) for each list i where d appears.
    """
    rrf_scores: dict[str, dict] = {}

    for results in result_lists:
        for rank, r in enumerate(results):
            rid = r.id if hasattr(r, "id") else r["id"]
            key = rid.replace(DOC_NAMESPACE, "", 1) if rid.startswith(DOC_NAMESPACE) else rid

            if key not in rrf_scores:
                rrf_scores[key] = {
                    "id": rid,
                    "content": r.content if hasattr(r, "content") else r["content"],
                    "metadata": r.metadata if hasattr(r, "metadata") else r["metadata"],
                    "combined_score": 0.0,
                }
            rrf_scores[key]["combined_score"] += 1.0 / (k + rank + 1)

    ranked = sorted(rrf_scores.values(), key=lambda x: x["combined_score"], reverse=True)
    return ranked


def hybrid_search(
    query: str,
    query_vector: list[float] | None = None,
    vector_k: int = 5,
    bm25_k: int = 5,
    top_k: int = 5,
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
    merge_method: str = "weighted",
    method_override: str | None = None,
) -> dict:
    """
    Run hybrid retrieval and return results + diagnostics for pipeline viz.

    Returns:
        {
            "results": [merged result dicts],
            "vector_results": [raw vector results],
            "bm25_results": [raw bm25 results],
            "vector_time_ms": float,
            "bm25_time_ms": float,
            "merge_method": str,
            "matched_terms": dict,
        }
    """
    import time

    store = get_vector_store()
    bm25 = get_bm25_index()

    # Vector search
    if query_vector is None:
        query_vector = embed_query(query)

    t0 = time.perf_counter()
    vec_results = store.search(query_vector, k=vector_k, namespace=DOC_NAMESPACE, method_override=method_override)
    vec_time = (time.perf_counter() - t0) * 1000

    # BM25 search
    t0 = time.perf_counter()
    bm25_results = bm25.search(query, k=bm25_k)
    bm25_time = (time.perf_counter() - t0) * 1000

    matched_terms = bm25.get_matched_terms(query)

    # Merge
    if merge_method == "rrf":
        merged = reciprocal_rank_fusion(vec_results, bm25_results)
    else:
        merged = weighted_ensemble(vec_results, bm25_results, vector_weight, bm25_weight)

    return {
        "results": merged[:top_k],
        "vector_results_count": len(vec_results),
        "bm25_results_count": len(bm25_results),
        "vector_time_ms": round(vec_time, 2),
        "bm25_time_ms": round(bm25_time, 2),
        "merge_method": merge_method,
        "matched_terms": matched_terms,
    }
