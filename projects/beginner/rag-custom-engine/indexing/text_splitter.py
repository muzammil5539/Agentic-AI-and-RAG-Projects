"""
Recursive character text splitter — from scratch, no LangChain.
Splits text using hierarchical separators, respecting chunk_size and overlap.
"""


def recursive_split(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separators: list[str] | None = None,
) -> list[str]:
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    chunks: list[str] = []
    _split_recursive(text, separators, chunk_size, chunk_overlap, chunks)
    return [c for c in chunks if c.strip()]


def _split_recursive(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
    result: list[str],
) -> None:
    if len(text) <= chunk_size:
        result.append(text.strip())
        return

    sep = separators[0] if separators else ""
    remaining_seps = separators[1:] if len(separators) > 1 else [""]

    if sep == "":
        # Hard split by character count
        for i in range(0, len(text), chunk_size - chunk_overlap):
            piece = text[i : i + chunk_size]
            if piece.strip():
                result.append(piece.strip())
        return

    parts = text.split(sep)

    current_chunk = ""
    for part in parts:
        candidate = (current_chunk + sep + part).strip() if current_chunk else part.strip()

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            # Flush current chunk if it has content
            if current_chunk.strip():
                result.append(current_chunk.strip())

            # If this single part is still too large, recurse with next separator
            if len(part.strip()) > chunk_size:
                _split_recursive(part.strip(), remaining_seps, chunk_size, chunk_overlap, result)
            else:
                current_chunk = part.strip()
                continue

            # Start new chunk with overlap from end of flushed chunk
            if chunk_overlap > 0 and result:
                overlap_text = result[-1][-chunk_overlap:]
                current_chunk = overlap_text
            else:
                current_chunk = ""

    if current_chunk.strip():
        result.append(current_chunk.strip())


def chunk_documents(
    docs: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict]:
    chunks = []
    chunk_index = 0
    for doc in docs:
        text = doc["content"]
        metadata = doc["metadata"].copy()
        splits = recursive_split(text, chunk_size, chunk_overlap)
        for split_text in splits:
            chunk_meta = metadata.copy()
            chunk_meta["chunk_index"] = chunk_index
            chunks.append({"content": split_text, "metadata": chunk_meta})
            chunk_index += 1
    return chunks
