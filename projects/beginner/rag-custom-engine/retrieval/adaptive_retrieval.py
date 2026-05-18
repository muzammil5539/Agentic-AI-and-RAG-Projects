"""
Self-RAG (Adaptive Retrieval) — Three-stage LLM evaluation:
1. Retrieval Decision: Does this question need document retrieval?
2. Relevance Grading: Is each retrieved chunk relevant?
3. Hallucination Check: Is the generated answer grounded in context?

No LangChain. Direct OpenAI calls.
"""

import json
from openai import OpenAI
from config import settings


def _call_llm(messages: list[dict], temperature: float = 0.0) -> str:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


# ───────────────────── Stage 1: Retrieval Decision ─────────────────────

def decide_retrieval(query: str) -> dict:
    """
    Evaluate if the query needs document retrieval.
    Returns: {"needs_retrieval": bool, "reasoning": str}
    """
    response = _call_llm([
        {
            "role": "system",
            "content": (
                "You are a retrieval decision module for a RAG system. "
                "Determine whether the user's question requires retrieving documents from a knowledge base.\n\n"
                "Questions that NEED retrieval:\n"
                "- Factual questions about specific topics/documents\n"
                "- Technical questions that need domain knowledge\n"
                "- Questions referencing uploaded content\n\n"
                "Questions that DON'T need retrieval:\n"
                "- Greetings (hi, hello, how are you)\n"
                "- Meta questions about the system itself\n"
                "- Simple math or logic\n"
                "- Requests to summarize the conversation\n\n"
                'Respond with ONLY a JSON object: {"needs_retrieval": true/false, "reasoning": "brief explanation"}'
            ),
        },
        {"role": "user", "content": query},
    ])

    try:
        text = response
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return {
            "needs_retrieval": bool(result.get("needs_retrieval", True)),
            "reasoning": str(result.get("reasoning", "")),
        }
    except (json.JSONDecodeError, KeyError):
        # Default to retrieval if parsing fails
        return {"needs_retrieval": True, "reasoning": "Parse error — defaulting to retrieval"}


# ───────────────────── Stage 2: Relevance Grading ─────────────────────

def grade_relevance(query: str, chunks: list[dict]) -> dict:
    """
    Grade each retrieved chunk as relevant or irrelevant.
    Returns: {"graded": [{"chunk": dict, "relevant": bool, "reason": str}], "kept": int, "filtered": int}
    """
    if not chunks:
        return {"graded": [], "kept": 0, "filtered": 0}

    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        content_preview = chunk["content"][:300]
        source = chunk.get("metadata", {}).get("source_filename", "Unknown")
        chunk_summaries.append(f"[Chunk {i}] Source: {source}\n{content_preview}")

    chunks_text = "\n---\n".join(chunk_summaries)

    response = _call_llm([
        {
            "role": "system",
            "content": (
                "You are a relevance grading module for a RAG system. "
                "For each retrieved chunk, determine if it is relevant to the user's question.\n\n"
                "A chunk is RELEVANT if it contains information that could help answer the question.\n"
                "A chunk is IRRELEVANT if it discusses unrelated topics.\n\n"
                "Respond with ONLY a JSON array where each element is:\n"
                '{"chunk_index": N, "relevant": true/false, "reason": "brief explanation"}'
            ),
        },
        {
            "role": "user",
            "content": f"Question: {query}\n\nRetrieved chunks:\n{chunks_text}",
        },
    ])

    try:
        text = response
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        grades = json.loads(text)
    except (json.JSONDecodeError, KeyError):
        # Default to keeping all chunks
        grades = [{"chunk_index": i, "relevant": True, "reason": "Parse error — kept"} for i in range(len(chunks))]

    graded = []
    for i, chunk in enumerate(chunks):
        grade = next((g for g in grades if g.get("chunk_index") == i), None)
        is_relevant = grade.get("relevant", True) if grade else True
        reason = grade.get("reason", "") if grade else ""
        graded.append({"chunk": chunk, "relevant": is_relevant, "reason": reason})

    kept = sum(1 for g in graded if g["relevant"])
    filtered = len(graded) - kept

    return {"graded": graded, "kept": kept, "filtered": filtered}


# ───────────────────── Stage 3: Hallucination Check ─────────────────────

def check_hallucination(query: str, context: str, answer: str) -> dict:
    """
    Check if the generated answer is grounded in the provided context.
    Returns: {"grounded": bool, "reasoning": str, "confidence": float}
    """
    response = _call_llm([
        {
            "role": "system",
            "content": (
                "You are a hallucination detection module for a RAG system. "
                "Evaluate whether the assistant's answer is grounded in the provided context.\n\n"
                "GROUNDED means: every factual claim in the answer can be traced to the context.\n"
                "NOT GROUNDED means: the answer contains claims not supported by the context.\n\n"
                "Respond with ONLY a JSON object:\n"
                '{"grounded": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question: {query}\n\n"
                f"Context provided:\n{context[:3000]}\n\n"
                f"Assistant's answer:\n{answer[:2000]}\n\n"
                "Is this answer grounded in the context?"
            ),
        },
    ])

    try:
        text = response
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return {
            "grounded": bool(result.get("grounded", True)),
            "confidence": float(result.get("confidence", 0.5)),
            "reasoning": str(result.get("reasoning", "")),
        }
    except (json.JSONDecodeError, KeyError):
        return {"grounded": True, "confidence": 0.5, "reasoning": "Parse error — assumed grounded"}
