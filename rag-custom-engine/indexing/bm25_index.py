"""
Okapi BM25 implementation from scratch — no rank-bm25 library.

BM25 score(q, D) = Σ IDF(qi) × (f(qi,D) × (k1+1)) / (f(qi,D) + k1 × (1 - b + b × |D|/avgdl))

Where:
- f(qi,D) = term frequency of qi in document D
- |D| = document length (in tokens)
- avgdl = average document length across corpus
- IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)
- N = total documents, n(qi) = documents containing term qi
"""

import json
import math
import re
from pathlib import Path
from typing import Optional

# ───────────────────── English stopwords (hardcoded) ─────────────────────

STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "just", "me", "my", "no", "nor", "not", "of", "on",
    "or", "our", "out", "own", "said", "she", "so", "some", "than", "that",
    "the", "their", "them", "then", "there", "these", "they", "this", "to",
    "too", "us", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "will", "with", "would", "you",
    "your", "about", "after", "again", "all", "also", "am", "any", "because",
    "been", "before", "being", "between", "both", "can", "could", "did", "do",
    "does", "doing", "down", "during", "each", "few", "get", "got", "having",
    "here", "him", "himself", "herself", "itself", "let", "like", "make",
    "more", "most", "much", "must", "need", "nor", "now", "off", "once",
    "only", "other", "over", "own", "re", "s", "same", "shall", "should",
    "since", "still", "such", "t", "take", "tell", "through", "under",
    "until", "up", "upon", "used", "using", "ve", "want", "well", "went",
})


# ───────────────────── Tokenizer ─────────────────────

def tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


# ───────────────────── BM25 Document ─────────────────────

class BM25Doc:
    __slots__ = ("id", "content", "metadata", "tokens", "tf")

    def __init__(self, id: str, content: str, metadata: dict):
        self.id = id
        self.content = content
        self.metadata = metadata
        self.tokens = tokenize(content)
        # Term frequency map
        self.tf: dict[str, int] = {}
        for token in self.tokens:
            self.tf[token] = self.tf.get(token, 0) + 1


class BM25SearchResult:
    __slots__ = ("id", "content", "metadata", "score")

    def __init__(self, id: str, content: str, metadata: dict, score: float):
        self.id = id
        self.content = content
        self.metadata = metadata
        self.score = score

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "score": self.score,
        }


# ───────────────────── BM25 Index ─────────────────────

class BM25Index:
    """
    Full Okapi BM25 index with inverted index and IDF computation.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.docs: dict[str, BM25Doc] = {}
        self.inverted_index: dict[str, set[str]] = {}  # term -> set of doc_ids
        self.avgdl: float = 0.0
        self.total_docs: int = 0

    def _rebuild_stats(self) -> None:
        self.total_docs = len(self.docs)
        if self.total_docs == 0:
            self.avgdl = 0.0
            return
        total_len = sum(len(d.tokens) for d in self.docs.values())
        self.avgdl = total_len / self.total_docs

    def _rebuild_inverted_index(self) -> None:
        self.inverted_index = {}
        for doc in self.docs.values():
            for term in doc.tf:
                if term not in self.inverted_index:
                    self.inverted_index[term] = set()
                self.inverted_index[term].add(doc.id)

    def add_documents(self, ids: list[str], contents: list[str], metadatas: list[dict]) -> None:
        for doc_id, content, meta in zip(ids, contents, metadatas):
            self.docs[doc_id] = BM25Doc(doc_id, content, meta)
        self._rebuild_inverted_index()
        self._rebuild_stats()

    def remove_documents(self, ids: list[str]) -> int:
        count = 0
        for doc_id in ids:
            if doc_id in self.docs:
                del self.docs[doc_id]
                count += 1
        if count > 0:
            self._rebuild_inverted_index()
            self._rebuild_stats()
        return count

    def remove_by_metadata(self, key: str, value: str) -> int:
        to_remove = [d.id for d in self.docs.values() if d.metadata.get(key) == value]
        return self.remove_documents(to_remove)

    def idf(self, term: str) -> float:
        n = len(self.inverted_index.get(term, set()))
        return math.log((self.total_docs - n + 0.5) / (n + 0.5) + 1.0)

    def score_document(self, query_tokens: list[str], doc: BM25Doc) -> float:
        score = 0.0
        doc_len = len(doc.tokens)
        for qt in query_tokens:
            tf = doc.tf.get(qt, 0)
            if tf == 0:
                continue
            idf_val = self.idf(qt)
            numerator = tf * (self.k1 + 1.0)
            denominator = tf + self.k1 * (1.0 - self.b + self.b * doc_len / max(self.avgdl, 1.0))
            score += idf_val * (numerator / denominator)
        return score

    def search(self, query: str, k: int = 5) -> list[BM25SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens or not self.docs:
            return []

        # Only score docs that contain at least one query term
        candidate_ids: set[str] = set()
        for qt in query_tokens:
            candidate_ids.update(self.inverted_index.get(qt, set()))

        if not candidate_ids:
            return []

        scored = []
        for doc_id in candidate_ids:
            doc = self.docs[doc_id]
            s = self.score_document(query_tokens, doc)
            if s > 0:
                scored.append(BM25SearchResult(doc_id, doc.content, doc.metadata, s))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:k]

    def get_matched_terms(self, query: str) -> dict[str, int]:
        query_tokens = tokenize(query)
        return {
            t: len(self.inverted_index.get(t, set()))
            for t in query_tokens
            if t in self.inverted_index
        }

    def count(self) -> int:
        return len(self.docs)

    def get_stats(self) -> dict:
        return {
            "total_docs": self.total_docs,
            "avg_doc_length": round(self.avgdl, 1),
            "vocabulary_size": len(self.inverted_index),
            "k1": self.k1,
            "b": self.b,
        }

    # ────────────────────── Persistence ──────────────────────

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "k1": self.k1,
            "b": self.b,
            "docs": [
                {"id": d.id, "content": d.content, "metadata": d.metadata}
                for d in self.docs.values()
            ],
        }
        tmp = str(p) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        Path(tmp).replace(p)

    def load(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        self.k1 = data.get("k1", self.k1)
        self.b = data.get("b", self.b)
        docs_data = data.get("docs", [])
        if docs_data:
            self.add_documents(
                [d["id"] for d in docs_data],
                [d["content"] for d in docs_data],
                [d["metadata"] for d in docs_data],
            )


# ─────────────────────── Singleton ──────────────────────────

_index: Optional[BM25Index] = None


def get_bm25_index() -> BM25Index:
    global _index
    if _index is None:
        from config import settings
        _index = BM25Index()
        _index.load(settings.BM25_INDEX_FILE)
    return _index
