"""
Contextual Compression — LLM extracts only relevant portions from chunks.
Reduces noise before generation. No LangChain.
"""

from openai import OpenAI
from config import settings


def compress_chunks(query: str, chunks: list[dict]) -> dict:
    """
    For each chunk, extract only the text relevant to the query.

    Returns:
        {
            "compressed": [{"content": str, "metadata": dict, "original_length": int, "compressed_length": int}],
            "total_original": int,
            "total_compressed": int,
            "compression_ratio": float,
        }
    """
    if not chunks:
        return {"compressed": [], "total_original": 0, "total_compressed": 0, "compression_ratio": 1.0}

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    compressed = []
    total_original = 0
    total_compressed = 0

    for chunk in chunks:
        content = chunk["content"]
        original_length = len(content)
        total_original += original_length

        # Skip compression for short chunks
        if original_length < 200:
            compressed.append({
                "content": content,
                "metadata": chunk.get("metadata", {}),
                "original_length": original_length,
                "compressed_length": original_length,
            })
            total_compressed += original_length
            continue

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_CHAT_MODEL,
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a context compression module. "
                            "Extract ONLY the parts of the text that are directly relevant to answering the question. "
                            "Remove irrelevant sentences and filler. Keep key facts, data, and explanations intact. "
                            "If no part is relevant, respond with: [NOT RELEVANT]\n"
                            "Do NOT add your own text — only extract from the given content."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {query}\n\nText to compress:\n{content}",
                    },
                ],
            )

            compressed_text = response.choices[0].message.content.strip()

            if compressed_text == "[NOT RELEVANT]" or not compressed_text:
                continue  # Drop entirely irrelevant chunks

            compressed_length = len(compressed_text)
            total_compressed += compressed_length

            compressed.append({
                "content": compressed_text,
                "metadata": chunk.get("metadata", {}),
                "original_length": original_length,
                "compressed_length": compressed_length,
            })

        except Exception:
            # On error, keep original
            compressed.append({
                "content": content,
                "metadata": chunk.get("metadata", {}),
                "original_length": original_length,
                "compressed_length": original_length,
            })
            total_compressed += original_length

    ratio = total_compressed / total_original if total_original > 0 else 1.0

    return {
        "compressed": compressed,
        "total_original": total_original,
        "total_compressed": total_compressed,
        "compression_ratio": round(ratio, 3),
    }
