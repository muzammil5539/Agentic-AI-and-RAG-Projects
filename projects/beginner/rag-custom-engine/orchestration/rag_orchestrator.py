"""
Pipeline Orchestrator — runs the full RAG pipeline step-by-step,
tracking timing, inputs/outputs, and status for each step.

This is the brain that coordinates all RAG components and produces
the pipeline trace for the frontend visualization.
"""

import time
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator
from dataclasses import dataclass, field, asdict


@dataclass
class PipelineStep:
    name: str
    status: str = "pending"  # pending | running | completed | skipped | error
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    details: dict = field(default_factory=dict)

    def start(self):
        self.status = "running"
        self._start_time = time.perf_counter()

    def complete(self, output_summary: str = "", details: dict | None = None):
        self.status = "completed"
        self.duration_ms = round((time.perf_counter() - self._start_time) * 1000, 2)
        self.output_summary = output_summary
        if details:
            self.details.update(details)

    def skip(self, reason: str = ""):
        self.status = "skipped"
        self.output_summary = reason
        self.duration_ms = 0.0

    def fail(self, error: str = ""):
        self.status = "error"
        if hasattr(self, "_start_time"):
            self.duration_ms = round((time.perf_counter() - self._start_time) * 1000, 2)
        self.output_summary = error

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


@dataclass
class PipelineConfig:
    use_multi_query: bool = False
    use_self_rag: bool = False
    use_compression: bool = False
    vector_method: str = "brute_force"  # brute_force | hnsw
    merge_method: str = "weighted"  # weighted | rrf
    vector_k: int = 5
    bm25_k: int = 5
    top_k: int = 5
    vector_weight: float = 0.5
    bm25_weight: float = 0.5


@dataclass
class PipelineResult:
    answer: str = ""
    sources: list = field(default_factory=list)
    cross_chat_refs: list = field(default_factory=list)
    session_id: str = ""
    steps: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "cross_chat_refs": self.cross_chat_refs,
            "session_id": self.session_id,
            "steps": [s.to_dict() if isinstance(s, PipelineStep) else s for s in self.steps],
        }


def run_pipeline(
    question: str,
    session_id: Optional[str],
    chat_history: list[dict],
    config: PipelineConfig,
) -> PipelineResult:
    """
    Execute the full RAG pipeline with step-by-step tracking.

    Steps:
    1. Query Received
    2. Self-RAG: Retrieval Decision (optional)
    3. Multi-Query Expansion (optional)
    4. Embedding Generation
    5. Vector Search
    6. BM25 Search
    7. Hybrid Merge
    8. Self-RAG: Relevance Grading (optional)
    9. Contextual Compression (optional)
    10. Cross-Chat Memory Search
    11. Context Assembly
    12. LLM Generation
    13. Self-RAG: Hallucination Check (optional)
    14. Response Ready
    """
    from indexing.openai_embeddings import embed_query
    from indexing.hnsw_vector_store import get_vector_store
    from indexing.bm25_index import get_bm25_index
    from retrieval.hybrid_search import hybrid_search
    from retrieval.multi_query_retriever import multi_query_search
    from retrieval.adaptive_retrieval import decide_retrieval, grade_relevance, check_hallucination
    from retrieval.contextual_compression import compress_chunks
    from generation.answer_generator import generate_answer, format_context
    from memory.cross_session_memory import get_chat_memory_store
    from config import settings

    pipeline_start_iso = datetime.now(timezone.utc).isoformat()
    result = PipelineResult(session_id=session_id or "")
    steps: list[PipelineStep] = []

    # ── Step 1: Query Received ───────────────────────────────────────
    step1 = PipelineStep(name="Query Received", input_summary=question[:100])
    step1.start()
    config_flags = []
    if config.use_multi_query: config_flags.append("Multi-Query")
    if config.use_self_rag: config_flags.append("Self-RAG")
    if config.use_compression: config_flags.append("Compression")
    step1.complete(
        output_summary=f"Query: \"{question[:80]}{'...' if len(question) > 80 else ''}\"",
        details={
            "query": question,
            "query_length": len(question),
            "history_turns": len(chat_history) // 2,
            "has_history": len(chat_history) > 0,
            "config_flags": config_flags if config_flags else ["None"],
            "vector_method": config.vector_method,
            "merge_method": config.merge_method,
        },
    )
    steps.append(step1)

    # ── Step 2: Self-RAG Retrieval Decision ──────────────────────────
    step2 = PipelineStep(name="Self-RAG: Retrieval Decision", input_summary="Evaluating if retrieval is needed")
    needs_retrieval = True
    if config.use_self_rag:
        step2.start()
        try:
            decision = decide_retrieval(question)
            needs_retrieval = decision["needs_retrieval"]
            step2.complete(
                output_summary=f"{'Retrieval needed' if needs_retrieval else 'No retrieval needed'}",
                details={
                    "decision": "RETRIEVE" if needs_retrieval else "SKIP",
                    "reasoning": decision.get("reasoning", ""),
                    "needs_retrieval": needs_retrieval,
                },
            )
        except Exception as e:
            step2.fail(str(e))
            needs_retrieval = True
    else:
        step2.skip("Self-RAG disabled")
    steps.append(step2)

    context_docs = []
    query_vector = None

    if needs_retrieval:
        # ── Step 3: Multi-Query Expansion ────────────────────────────
        step3 = PipelineStep(name="Multi-Query Expansion", input_summary=question[:60])
        query_variants = [question]
        if config.use_multi_query:
            step3.start()
            try:
                from retrieval.multi_query_retriever import generate_query_variants
                variants = generate_query_variants(question, n=3)
                query_variants = [question] + variants
                step3.complete(
                    output_summary=f"Generated {len(variants)} variants",
                    details={
                        "original_query": question,
                        "variants": variants,
                        "variant_count": len(variants),
                        "total_queries": len(query_variants),
                    },
                )
            except Exception as e:
                step3.fail(str(e))
        else:
            step3.skip("Multi-Query disabled")
        steps.append(step3)

        # ── Step 4: Embedding Generation ─────────────────────────────
        step4 = PipelineStep(name="Embedding Generation", input_summary=f"Embedding {len(query_variants)} queries")
        step4.start()
        try:
            query_vector = embed_query(question)
            step4.complete(
                output_summary=f"Generated {len(query_vector)}-dim vector",
                details={
                    "dimensions": len(query_vector),
                    "model": "text-embedding-3-small",
                    "vector_preview": query_vector[:64],
                    "vector_min": round(min(query_vector), 4),
                    "vector_max": round(max(query_vector), 4),
                },
            )
        except Exception as e:
            step4.fail(str(e))
            result.steps = steps
            result.answer = f"Embedding generation failed: {e}"
            return result
        steps.append(step4)

        # ── Step 5: Vector Search ────────────────────────────────────
        method = config.vector_method
        step5 = PipelineStep(name="Vector Search", input_summary=f"Method: {method.upper()}")
        step5.start()
        try:
            store = get_vector_store()
            t0 = time.perf_counter()
            from retrieval.hybrid_search import DOC_NAMESPACE
            vec_results = store.search(
                query_vector, k=config.vector_k,
                namespace=DOC_NAMESPACE, method_override=method
            )
            vec_time = (time.perf_counter() - t0) * 1000
            step5.complete(
                output_summary=f"Found {len(vec_results)} candidates ({method.upper()}, {vec_time:.1f}ms)",
                details={
                    "method": method,
                    "k": config.vector_k,
                    "candidates": len(vec_results),
                    "time_ms": round(vec_time, 2),
                    "top_score": round(vec_results[0].score, 4) if vec_results else 0,
                    "results": [
                        {
                            "filename": r.metadata.get("source_filename", "unknown"),
                            "page": r.metadata.get("page", 0),
                            "chunk_index": r.metadata.get("chunk_index", 0),
                            "score": round(r.score, 4),
                            "snippet": r.content[:80],
                        }
                        for r in vec_results[:5]
                    ],
                },
            )
        except Exception as e:
            step5.fail(str(e))
            vec_results = []
        steps.append(step5)

        # ── Step 6: BM25 Search ──────────────────────────────────────
        step6 = PipelineStep(name="BM25 Keyword Search", input_summary="Lexical matching")
        step6.start()
        try:
            bm25 = get_bm25_index()
            t0 = time.perf_counter()
            bm25_results = bm25.search(question, k=config.bm25_k)
            bm25_time = (time.perf_counter() - t0) * 1000
            matched = bm25.get_matched_terms(question)
            step6.complete(
                output_summary=f"Found {len(bm25_results)} candidates ({bm25_time:.1f}ms)",
                details={
                    "k": config.bm25_k,
                    "candidates": len(bm25_results),
                    "time_ms": round(bm25_time, 2),
                    "matched_terms": matched,
                    "top_score": round(bm25_results[0].score, 4) if bm25_results else 0,
                    "results": [
                        {
                            "filename": r.metadata.get("source_filename", "unknown"),
                            "score": round(r.score, 4),
                            "snippet": r.content[:80],
                        }
                        for r in bm25_results[:5]
                    ],
                },
            )
        except Exception as e:
            step6.fail(str(e))
            bm25_results = []
        steps.append(step6)

        # ── Step 7: Hybrid Merge ─────────────────────────────────────
        step7 = PipelineStep(name="Hybrid Merge", input_summary=f"Method: {config.merge_method.upper()}")
        step7.start()
        try:
            if config.use_multi_query and len(query_variants) > 1:
                mq_result = multi_query_search(
                    query=question,
                    n_variants=3,
                    vector_k=config.vector_k,
                    bm25_k=config.bm25_k,
                    top_k=config.top_k,
                    vector_weight=config.vector_weight,
                    bm25_weight=config.bm25_weight,
                    merge_method=config.merge_method,
                    method_override=method,
                )
                merged_results = mq_result["results"]
                step7.complete(
                    output_summary=f"Multi-query RRF → {len(merged_results)} results",
                    details={
                        "merge_type": "multi_query_rrf",
                        "variants_used": len(query_variants),
                        "total_candidates": mq_result.get("total_candidates", 0),
                        "result_count": len(merged_results),
                        "scores": [
                            {
                                "filename": r.get("metadata", {}).get("source_filename", "unknown"),
                                "combined_score": round(r.get("combined_score", 0), 4),
                            }
                            for r in merged_results[:5]
                        ],
                    },
                )
            else:
                from retrieval.hybrid_search import weighted_ensemble, reciprocal_rank_fusion
                if config.merge_method == "rrf":
                    merged_results = reciprocal_rank_fusion(vec_results, bm25_results)
                else:
                    merged_results = weighted_ensemble(
                        vec_results, bm25_results,
                        config.vector_weight, config.bm25_weight
                    )
                merged_results = merged_results[:config.top_k]
                step7.complete(
                    output_summary=f"{config.merge_method.upper()} → {len(merged_results)} results",
                    details={
                        "merge_type": config.merge_method,
                        "result_count": len(merged_results),
                        "vector_weight": config.vector_weight,
                        "bm25_weight": config.bm25_weight,
                        "scores": [
                            {
                                "filename": r.get("metadata", {}).get("source_filename", "unknown"),
                                "vector_score": round(r.get("vector_score", 0), 4),
                                "bm25_score": round(r.get("bm25_score", 0), 4),
                                "combined_score": round(r.get("combined_score", 0), 4),
                            }
                            for r in merged_results[:5]
                        ],
                    },
                )
        except Exception as e:
            step7.fail(str(e))
            merged_results = []
        steps.append(step7)

        context_docs = merged_results

        # ── Step 8: Self-RAG Relevance Grading ───────────────────────
        step8 = PipelineStep(name="Self-RAG: Relevance Grading", input_summary=f"Grading {len(context_docs)} chunks")
        if config.use_self_rag and context_docs:
            step8.start()
            try:
                grade_result = grade_relevance(question, context_docs)
                context_docs = [g["chunk"] for g in grade_result["graded"] if g["relevant"]]
                step8.complete(
                    output_summary=f"Kept {grade_result['kept']}, filtered {grade_result['filtered']}",
                    details={
                        "kept": grade_result["kept"],
                        "filtered": grade_result["filtered"],
                        "decisions": [
                            {
                                "snippet": g["chunk"].get("content", "")[:80],
                                "relevant": g["relevant"],
                                "reason": g.get("reason", ""),
                            }
                            for g in grade_result["graded"]
                        ],
                    },
                )
            except Exception as e:
                step8.fail(str(e))
        else:
            step8.skip("Self-RAG disabled" if not config.use_self_rag else "No chunks to grade")
        steps.append(step8)

        # ── Step 9: Contextual Compression ───────────────────────────
        step9 = PipelineStep(name="Contextual Compression", input_summary=f"Compressing {len(context_docs)} chunks")
        if config.use_compression and context_docs:
            step9.start()
            try:
                comp_result = compress_chunks(question, context_docs)
                context_docs = comp_result["compressed"]
                step9.complete(
                    output_summary=(
                        f"Compressed {comp_result['total_original']} → {comp_result['total_compressed']} chars "
                        f"({comp_result['compression_ratio']:.0%})"
                    ),
                    details={
                        "original_chars": comp_result["total_original"],
                        "compressed_chars": comp_result["total_compressed"],
                        "ratio": round(comp_result["compression_ratio"], 3),
                        "chunks_remaining": len(comp_result["compressed"]),
                        "items": [
                            {
                                "original_len": item.get("original_length", 0),
                                "compressed_len": item.get("compressed_length", 0),
                            }
                            for item in comp_result["compressed"][:5]
                        ],
                    },
                )
            except Exception as e:
                step9.fail(str(e))
        else:
            step9.skip("Compression disabled" if not config.use_compression else "No chunks to compress")
        steps.append(step9)

    else:
        # Skip retrieval steps 3-9
        for name in [
            "Multi-Query Expansion", "Embedding Generation", "Vector Search",
            "BM25 Keyword Search", "Hybrid Merge",
            "Self-RAG: Relevance Grading", "Contextual Compression"
        ]:
            s = PipelineStep(name=name)
            s.skip("Retrieval not needed (Self-RAG)")
            steps.append(s)

    # ── Step 10: Cross-Chat Memory ───────────────────────────────────
    step10 = PipelineStep(name="Cross-Chat Memory Search", input_summary="Searching past conversations")
    step10.start()
    cross_chat_docs = []
    try:
        memory_store = get_chat_memory_store()
        cross_chat_docs = memory_store.search_relevant(question, k=3)
        step10.complete(
            output_summary=f"Found {len(cross_chat_docs)} relevant past conversations",
            details={
                "count": len(cross_chat_docs),
                "memories": [
                    {
                        "session_title": d.get("metadata", {}).get("session_title", "Untitled"),
                        "archived_at": d.get("metadata", {}).get("archived_at", "")[:10],
                        "message_count": d.get("metadata", {}).get("message_count", 0),
                        "snippet": d.get("content", "")[:100],
                    }
                    for d in cross_chat_docs
                ],
            },
        )
    except Exception as e:
        step10.complete(output_summary="No cross-chat memories available", details={"error": str(e)})
    steps.append(step10)

    # ── Step 11: Context Assembly ────────────────────────────────────
    step11 = PipelineStep(name="Context Assembly", input_summary="Building LLM prompt")
    step11.start()
    context_str = format_context(context_docs)
    total_context_len = len(context_str)
    step11.complete(
        output_summary=f"Assembled {len(context_docs)} chunks + {len(cross_chat_docs)} memories ({total_context_len} chars)",
        details={
            "doc_chunks": len(context_docs),
            "memory_chunks": len(cross_chat_docs),
            "total_chars": total_context_len,
            "history_messages": len(chat_history),
            "context_preview": context_str[:300] if context_str else "",
        },
    )
    steps.append(step11)

    # ── Step 12: LLM Generation ──────────────────────────────────────
    step12 = PipelineStep(name="LLM Generation", input_summary=f"Model: {settings.OPENAI_CHAT_MODEL}")
    step12.start()
    try:
        gen_result = generate_answer(question, context_docs, chat_history, cross_chat_docs)
        step12.complete(
            output_summary=f"Generated {len(gen_result['answer'])} chars ({gen_result['usage']['total_tokens']} tokens)",
            details={
                "model": settings.OPENAI_CHAT_MODEL,
                "temperature": 0.1,
                "answer_length": len(gen_result["answer"]),
                "prompt_tokens": gen_result["usage"]["prompt_tokens"],
                "completion_tokens": gen_result["usage"]["completion_tokens"],
                "total_tokens": gen_result["usage"]["total_tokens"],
                "answer_preview": gen_result["answer"][:150],
            },
        )
        result.answer = gen_result["answer"]
        result.sources = gen_result["sources"]
        result.cross_chat_refs = gen_result["cross_chat_refs"]
    except Exception as e:
        step12.fail(str(e))
        result.answer = f"Generation failed: {e}"
    steps.append(step12)

    # ── Step 13: Self-RAG Hallucination Check ────────────────────────
    step13 = PipelineStep(name="Self-RAG: Hallucination Check", input_summary="Checking groundedness")
    if config.use_self_rag and context_docs and result.answer:
        step13.start()
        try:
            hall_result = check_hallucination(question, context_str, result.answer)
            status_text = "GROUNDED" if hall_result["grounded"] else "NOT GROUNDED"
            step13.complete(
                output_summary=f"{status_text} (confidence: {hall_result['confidence']:.0%})",
                details={
                    "grounded": hall_result["grounded"],
                    "confidence": hall_result["confidence"],
                    "reasoning": hall_result.get("reasoning", ""),
                },
            )
            # If not grounded, regenerate with stricter prompt
            if not hall_result["grounded"]:
                step13.details["action"] = "Answer flagged — user should verify"
        except Exception as e:
            step13.fail(str(e))
    else:
        step13.skip("Self-RAG disabled" if not config.use_self_rag else "No context to check")
    steps.append(step13)

    # ── Step 14: Response Ready ──────────────────────────────────────
    step14 = PipelineStep(name="Response Ready")
    step14.start()
    total_time = sum(s.duration_ms for s in steps)
    step14.complete(
        output_summary=f"Total pipeline: {total_time:.0f}ms",
        details={
            "total_time_ms": round(total_time, 2),
            "steps_completed": sum(1 for s in steps if s.status == "completed"),
            "steps_skipped": sum(1 for s in steps if s.status == "skipped"),
            "steps_errored": sum(1 for s in steps if s.status == "error"),
            "retrieval_used": needs_retrieval,
            "waterfall": [
                {"name": s.name, "duration_ms": s.duration_ms, "status": s.status}
                for s in steps
            ],
        },
    )
    steps.append(step14)

    result.steps = steps

    # Persist trace so the UI can reload it after page refresh / session switch
    if session_id:
        try:
            from memory.trace_store import get_trace_store
            total_ms = round(sum(s.duration_ms for s in steps), 2)
            get_trace_store().save_trace(session_id, {
                "trace_id": str(uuid.uuid4()),
                "session_id": session_id,
                "turn_index": None,  # TraceStore assigns based on current count
                "query": question,
                "started_at": pipeline_start_iso,
                "total_duration_ms": total_ms,
                "steps": [s.to_dict() for s in steps],
            })
        except Exception:
            pass  # trace save failure must not break the response

    return result


async def stream_pipeline(
    question: str,
    session_id: Optional[str],
    chat_history: list[dict],
    config: "PipelineConfig",
) -> AsyncGenerator[str, None]:
    """
    Async generator that streams pipeline events as SSE-formatted strings.

    Each event is a JSON line: `data: {json}\\n\\n`

    Event types:
      {"type": "step_start",    "step_name": str, "index": int}
      {"type": "step_complete", "step": <PipelineStep.to_dict()>}
      {"type": "answer",        "data": {answer, sources, session_id, cross_chat_refs}}
      {"type": "error",         "data": {"message": str}}
    """

    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    from indexing.openai_embeddings import embed_query
    from indexing.hnsw_vector_store import get_vector_store
    from indexing.bm25_index import get_bm25_index
    from retrieval.hybrid_search import hybrid_search, DOC_NAMESPACE
    from retrieval.multi_query_retriever import multi_query_search
    from retrieval.adaptive_retrieval import decide_retrieval, grade_relevance, check_hallucination
    from retrieval.contextual_compression import compress_chunks
    from generation.answer_generator import generate_answer, format_context
    from memory.cross_session_memory import get_chat_memory_store
    from config import settings

    pipeline_start_iso = datetime.now(timezone.utc).isoformat()
    loop = asyncio.get_running_loop()
    step_index = 0
    all_steps: list[PipelineStep] = []

    async def run_step(step: PipelineStep):
        nonlocal step_index
        step.start()
        yield _sse({"type": "step_start", "step_name": step.name, "index": step_index})
        step_index += 1
        # Tiny yield so FastAPI can flush
        await asyncio.sleep(0)

    # ── Step 1: Query Received ───────────────────────────────────────
    step1 = PipelineStep(name="Query Received", input_summary=question[:100])
    step1.start()
    config_flags = []
    if config.use_multi_query: config_flags.append("Multi-Query")
    if config.use_self_rag: config_flags.append("Self-RAG")
    if config.use_compression: config_flags.append("Compression")
    async for msg in run_step(step1):
        yield msg
    step1.complete(
        output_summary=f"Query: \"{question[:80]}{'...' if len(question) > 80 else ''}\"",
        details={
            "query": question,
            "query_length": len(question),
            "history_turns": len(chat_history) // 2,
            "has_history": len(chat_history) > 0,
            "config_flags": config_flags if config_flags else ["None"],
            "vector_method": config.vector_method,
            "merge_method": config.merge_method,
        },
    )
    all_steps.append(step1)
    yield _sse({"type": "step_complete", "step": step1.to_dict()})
    await asyncio.sleep(0)

    # ── Step 2: Self-RAG Retrieval Decision ──────────────────────────
    step2 = PipelineStep(name="Self-RAG: Retrieval Decision", input_summary="Evaluating if retrieval is needed")
    needs_retrieval = True
    if config.use_self_rag:
        async for msg in run_step(step2):
            yield msg
        try:
            decision = await loop.run_in_executor(None, decide_retrieval, question)
            needs_retrieval = decision["needs_retrieval"]
            step2.complete(
                output_summary=f"{'Retrieval needed' if needs_retrieval else 'No retrieval needed'}",
                details={
                    "decision": "RETRIEVE" if needs_retrieval else "SKIP",
                    "reasoning": decision.get("reasoning", ""),
                    "needs_retrieval": needs_retrieval,
                },
            )
        except Exception as e:
            step2.fail(str(e))
            needs_retrieval = True
    else:
        step2.skip("Self-RAG disabled")
    all_steps.append(step2)
    yield _sse({"type": "step_complete", "step": step2.to_dict()})
    await asyncio.sleep(0)

    context_docs = []
    query_vector = None

    if needs_retrieval:
        # ── Step 3: Multi-Query Expansion ────────────────────────────
        step3 = PipelineStep(name="Multi-Query Expansion", input_summary=question[:60])
        query_variants = [question]
        if config.use_multi_query:
            async for msg in run_step(step3):
                yield msg
            try:
                from retrieval.multi_query_retriever import generate_query_variants
                variants = generate_query_variants(question, n=3)
                query_variants = [question] + variants
                step3.complete(
                    output_summary=f"Generated {len(variants)} variants",
                    details={
                        "original_query": question,
                        "variants": variants,
                        "variant_count": len(variants),
                        "total_queries": len(query_variants),
                    },
                )
            except Exception as e:
                step3.fail(str(e))
        else:
            step3.skip("Multi-Query disabled")
        all_steps.append(step3)
        yield _sse({"type": "step_complete", "step": step3.to_dict()})
        await asyncio.sleep(0)

        # ── Step 4: Embedding ─────────────────────────────────────────
        step4 = PipelineStep(name="Embedding Generation", input_summary=f"Embedding {len(query_variants)} queries")
        async for msg in run_step(step4):
            yield msg
        try:
            query_vector = await loop.run_in_executor(None, embed_query, question)
            step4.complete(
                output_summary=f"Generated {len(query_vector)}-dim vector",
                details={
                    "dimensions": len(query_vector),
                    "model": "text-embedding-3-small",
                    "vector_preview": query_vector[:64],
                    "vector_min": round(min(query_vector), 4),
                    "vector_max": round(max(query_vector), 4),
                },
            )
        except Exception as e:
            step4.fail(str(e))
            all_steps.append(step4)
            yield _sse({"type": "step_complete", "step": step4.to_dict()})
            yield _sse({"type": "error", "data": {"message": f"Embedding failed: {e}"}})
            return
        all_steps.append(step4)
        yield _sse({"type": "step_complete", "step": step4.to_dict()})
        await asyncio.sleep(0)

        # ── Step 5: Vector Search ────────────────────────────────────
        method = config.vector_method
        step5 = PipelineStep(name="Vector Search", input_summary=f"Method: {method.upper()}")
        async for msg in run_step(step5):
            yield msg
        try:
            store = get_vector_store()
            t0 = time.perf_counter()
            vec_results = store.search(query_vector, k=config.vector_k, namespace=DOC_NAMESPACE, method_override=method)
            vec_time = (time.perf_counter() - t0) * 1000
            step5.complete(
                output_summary=f"Found {len(vec_results)} candidates ({method.upper()}, {vec_time:.1f}ms)",
                details={
                    "method": method,
                    "k": config.vector_k,
                    "candidates": len(vec_results),
                    "time_ms": round(vec_time, 2),
                    "top_score": round(vec_results[0].score, 4) if vec_results else 0,
                    "results": [
                        {
                            "filename": r.metadata.get("source_filename", "unknown"),
                            "page": r.metadata.get("page", 0),
                            "chunk_index": r.metadata.get("chunk_index", 0),
                            "score": round(r.score, 4),
                            "snippet": r.content[:80],
                        }
                        for r in vec_results[:5]
                    ],
                },
            )
        except Exception as e:
            step5.fail(str(e))
            vec_results = []
        all_steps.append(step5)
        yield _sse({"type": "step_complete", "step": step5.to_dict()})
        await asyncio.sleep(0)

        # ── Step 6: BM25 ─────────────────────────────────────────────
        step6 = PipelineStep(name="BM25 Keyword Search", input_summary="Lexical matching")
        async for msg in run_step(step6):
            yield msg
        try:
            bm25 = get_bm25_index()
            t0 = time.perf_counter()
            bm25_results = bm25.search(question, k=config.bm25_k)
            bm25_time = (time.perf_counter() - t0) * 1000
            matched = bm25.get_matched_terms(question)
            step6.complete(
                output_summary=f"Found {len(bm25_results)} candidates ({bm25_time:.1f}ms)",
                details={
                    "k": config.bm25_k,
                    "candidates": len(bm25_results),
                    "time_ms": round(bm25_time, 2),
                    "matched_terms": matched,
                    "top_score": round(bm25_results[0].score, 4) if bm25_results else 0,
                    "results": [
                        {
                            "filename": r.metadata.get("source_filename", "unknown"),
                            "score": round(r.score, 4),
                            "snippet": r.content[:80],
                        }
                        for r in bm25_results[:5]
                    ],
                },
            )
        except Exception as e:
            step6.fail(str(e))
            bm25_results = []
        all_steps.append(step6)
        yield _sse({"type": "step_complete", "step": step6.to_dict()})
        await asyncio.sleep(0)

        # ── Step 7: Hybrid Merge ─────────────────────────────────────
        step7 = PipelineStep(name="Hybrid Merge", input_summary=f"Method: {config.merge_method.upper()}")
        async for msg in run_step(step7):
            yield msg
        try:
            if config.use_multi_query and len(query_variants) > 1:
                mq_result = await loop.run_in_executor(
                    None, lambda: multi_query_search(
                        query=question, n_variants=3,
                        vector_k=config.vector_k, bm25_k=config.bm25_k, top_k=config.top_k,
                        vector_weight=config.vector_weight, bm25_weight=config.bm25_weight,
                        merge_method=config.merge_method, method_override=method,
                    )
                )
                merged_results = mq_result["results"]
                step7.complete(
                    output_summary=f"Multi-query RRF → {len(merged_results)} results",
                    details={
                        "merge_type": "multi_query_rrf",
                        "variants_used": len(query_variants),
                        "total_candidates": mq_result.get("total_candidates", 0),
                        "result_count": len(merged_results),
                        "scores": [
                            {"filename": r.get("metadata", {}).get("source_filename", "unknown"), "combined_score": round(r.get("combined_score", 0), 4)}
                            for r in merged_results[:5]
                        ],
                    },
                )
            else:
                from retrieval.hybrid_search import weighted_ensemble, reciprocal_rank_fusion
                if config.merge_method == "rrf":
                    merged_results = reciprocal_rank_fusion(vec_results, bm25_results)
                else:
                    merged_results = weighted_ensemble(vec_results, bm25_results, config.vector_weight, config.bm25_weight)
                merged_results = merged_results[:config.top_k]
                step7.complete(
                    output_summary=f"{config.merge_method.upper()} → {len(merged_results)} results",
                    details={
                        "merge_type": config.merge_method,
                        "result_count": len(merged_results),
                        "vector_weight": config.vector_weight,
                        "bm25_weight": config.bm25_weight,
                        "scores": [
                            {
                                "filename": r.get("metadata", {}).get("source_filename", "unknown"),
                                "vector_score": round(r.get("vector_score", 0), 4),
                                "bm25_score": round(r.get("bm25_score", 0), 4),
                                "combined_score": round(r.get("combined_score", 0), 4),
                            }
                            for r in merged_results[:5]
                        ],
                    },
                )
        except Exception as e:
            step7.fail(str(e))
            merged_results = []
        all_steps.append(step7)
        yield _sse({"type": "step_complete", "step": step7.to_dict()})
        await asyncio.sleep(0)

        context_docs = merged_results

        # ── Step 8: Relevance Grading ─────────────────────────────────
        step8 = PipelineStep(name="Self-RAG: Relevance Grading", input_summary=f"Grading {len(context_docs)} chunks")
        if config.use_self_rag and context_docs:
            async for msg in run_step(step8):
                yield msg
            try:
                grade_result = await loop.run_in_executor(None, lambda: grade_relevance(question, context_docs))
                context_docs = [g["chunk"] for g in grade_result["graded"] if g["relevant"]]
                step8.complete(
                    output_summary=f"Kept {grade_result['kept']}, filtered {grade_result['filtered']}",
                    details={
                        "kept": grade_result["kept"],
                        "filtered": grade_result["filtered"],
                        "decisions": [
                            {
                                "snippet": g["chunk"].get("content", "")[:80],
                                "relevant": g["relevant"],
                                "reason": g.get("reason", ""),
                            }
                            for g in grade_result["graded"]
                        ],
                    },
                )
            except Exception as e:
                step8.fail(str(e))
        else:
            step8.skip("Self-RAG disabled" if not config.use_self_rag else "No chunks to grade")
        all_steps.append(step8)
        yield _sse({"type": "step_complete", "step": step8.to_dict()})
        await asyncio.sleep(0)

        # ── Step 9: Compression ──────────────────────────────────────
        step9 = PipelineStep(name="Contextual Compression", input_summary=f"Compressing {len(context_docs)} chunks")
        if config.use_compression and context_docs:
            async for msg in run_step(step9):
                yield msg
            try:
                comp_result = await loop.run_in_executor(None, lambda: compress_chunks(question, context_docs))
                context_docs = comp_result["compressed"]
                step9.complete(
                    output_summary=f"Compressed {comp_result['total_original']} → {comp_result['total_compressed']} chars ({comp_result['compression_ratio']:.0%})",
                    details={
                        "original_chars": comp_result["total_original"],
                        "compressed_chars": comp_result["total_compressed"],
                        "ratio": round(comp_result["compression_ratio"], 3),
                        "chunks_remaining": len(comp_result["compressed"]),
                        "items": [
                            {"original_len": item.get("original_length", 0), "compressed_len": item.get("compressed_length", 0)}
                            for item in comp_result["compressed"][:5]
                        ],
                    },
                )
            except Exception as e:
                step9.fail(str(e))
        else:
            step9.skip("Compression disabled" if not config.use_compression else "No chunks to compress")
        all_steps.append(step9)
        yield _sse({"type": "step_complete", "step": step9.to_dict()})
        await asyncio.sleep(0)

    else:
        # Skip steps 3-9
        for name in [
            "Multi-Query Expansion", "Embedding Generation", "Vector Search",
            "BM25 Keyword Search", "Hybrid Merge",
            "Self-RAG: Relevance Grading", "Contextual Compression",
        ]:
            s = PipelineStep(name=name)
            s.skip("Retrieval not needed (Self-RAG)")
            all_steps.append(s)
            yield _sse({"type": "step_complete", "step": s.to_dict()})
            await asyncio.sleep(0)

    # ── Step 10: Cross-Chat Memory ────────────────────────────────────
    step10 = PipelineStep(name="Cross-Chat Memory Search", input_summary="Searching past conversations")
    async for msg in run_step(step10):
        yield msg
    cross_chat_docs = []
    try:
        memory_store = get_chat_memory_store()
        cross_chat_docs = await loop.run_in_executor(None, lambda: memory_store.search_relevant(question, k=3))
        step10.complete(
            output_summary=f"Found {len(cross_chat_docs)} relevant past conversations",
            details={
                "count": len(cross_chat_docs),
                "memories": [
                    {
                        "session_title": d.get("metadata", {}).get("session_title", "Untitled"),
                        "archived_at": d.get("metadata", {}).get("archived_at", "")[:10],
                        "message_count": d.get("metadata", {}).get("message_count", 0),
                        "snippet": d.get("content", "")[:100],
                    }
                    for d in cross_chat_docs
                ],
            },
        )
    except Exception as e:
        step10.complete(output_summary="No cross-chat memories available", details={"error": str(e)})
    all_steps.append(step10)
    yield _sse({"type": "step_complete", "step": step10.to_dict()})
    await asyncio.sleep(0)

    # ── Step 11: Context Assembly ─────────────────────────────────────
    step11 = PipelineStep(name="Context Assembly", input_summary="Building LLM prompt")
    async for msg in run_step(step11):
        yield msg
    context_str = format_context(context_docs)
    total_context_len = len(context_str)
    step11.complete(
        output_summary=f"Assembled {len(context_docs)} chunks + {len(cross_chat_docs)} memories ({total_context_len} chars)",
        details={
            "doc_chunks": len(context_docs),
            "memory_chunks": len(cross_chat_docs),
            "total_chars": total_context_len,
            "history_messages": len(chat_history),
            "context_preview": context_str[:300] if context_str else "",
        },
    )
    all_steps.append(step11)
    yield _sse({"type": "step_complete", "step": step11.to_dict()})
    await asyncio.sleep(0)

    # ── Step 12: LLM Generation ───────────────────────────────────────
    step12 = PipelineStep(name="LLM Generation", input_summary=f"Model: {settings.OPENAI_CHAT_MODEL}")
    async for msg in run_step(step12):
        yield msg
    answer = ""
    sources = []
    cross_chat_refs = []
    try:
        gen_result = await loop.run_in_executor(None, lambda: generate_answer(question, context_docs, chat_history, cross_chat_docs))
        step12.complete(
            output_summary=f"Generated {len(gen_result['answer'])} chars ({gen_result['usage']['total_tokens']} tokens)",
            details={
                "model": settings.OPENAI_CHAT_MODEL,
                "temperature": 0.1,
                "answer_length": len(gen_result["answer"]),
                "prompt_tokens": gen_result["usage"]["prompt_tokens"],
                "completion_tokens": gen_result["usage"]["completion_tokens"],
                "total_tokens": gen_result["usage"]["total_tokens"],
                "answer_preview": gen_result["answer"][:150],
            },
        )
        answer = gen_result["answer"]
        sources = gen_result["sources"]
        cross_chat_refs = gen_result["cross_chat_refs"]
    except Exception as e:
        step12.fail(str(e))
        answer = f"Generation failed: {e}"
    all_steps.append(step12)
    yield _sse({"type": "step_complete", "step": step12.to_dict()})
    await asyncio.sleep(0)

    # ── Step 13: Hallucination Check ──────────────────────────────────
    step13 = PipelineStep(name="Self-RAG: Hallucination Check", input_summary="Checking groundedness")
    if config.use_self_rag and context_docs and answer:
        async for msg in run_step(step13):
            yield msg
        try:
            hall_result = await loop.run_in_executor(None, lambda: check_hallucination(question, context_str, answer))
            status_text = "GROUNDED" if hall_result["grounded"] else "NOT GROUNDED"
            step13.complete(
                output_summary=f"{status_text} (confidence: {hall_result['confidence']:.0%})",
                details={
                    "grounded": hall_result["grounded"],
                    "confidence": hall_result["confidence"],
                    "reasoning": hall_result.get("reasoning", ""),
                },
            )
            if not hall_result["grounded"]:
                step13.details["action"] = "Answer flagged — user should verify"
        except Exception as e:
            step13.fail(str(e))
    else:
        step13.skip("Self-RAG disabled" if not config.use_self_rag else "No context to check")
    all_steps.append(step13)
    yield _sse({"type": "step_complete", "step": step13.to_dict()})
    await asyncio.sleep(0)

    # ── Step 14: Response Ready ───────────────────────────────────────
    step14 = PipelineStep(name="Response Ready")
    async for msg in run_step(step14):
        yield msg
    total_time = sum(s.duration_ms for s in all_steps)
    step14.complete(
        output_summary=f"Total pipeline: {total_time:.0f}ms",
        details={
            "total_time_ms": round(total_time, 2),
            "steps_completed": sum(1 for s in all_steps if s.status == "completed"),
            "steps_skipped": sum(1 for s in all_steps if s.status == "skipped"),
            "steps_errored": sum(1 for s in all_steps if s.status == "error"),
            "retrieval_used": needs_retrieval,
            "waterfall": [
                {"name": s.name, "duration_ms": s.duration_ms, "status": s.status}
                for s in all_steps
            ],
        },
    )
    all_steps.append(step14)
    yield _sse({"type": "step_complete", "step": step14.to_dict()})
    await asyncio.sleep(0)

    # ── Final answer event ────────────────────────────────────────────
    yield _sse({
        "type": "answer",
        "data": {
            "answer": answer,
            "sources": sources,
            "session_id": session_id or "",
            "cross_chat_refs": cross_chat_refs,
        },
    })

    # Persist trace so the UI can reload it after page refresh / session switch
    if session_id:
        try:
            from memory.trace_store import get_trace_store
            total_ms = round(sum(s.duration_ms for s in all_steps), 2)
            get_trace_store().save_trace(session_id, {
                "trace_id": str(uuid.uuid4()),
                "session_id": session_id,
                "turn_index": None,  # TraceStore assigns based on current count
                "query": question,
                "started_at": pipeline_start_iso,
                "total_duration_ms": total_ms,
                "steps": [s.to_dict() for s in all_steps],
            })
        except Exception:
            pass  # trace save failure must not break the stream
