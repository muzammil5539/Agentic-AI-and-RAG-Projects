"""
Vector store from scratch — Brute-Force Cosine Similarity + HNSW algorithm.
No ChromaDB, no FAISS, no external vector DB. Pure Python + math.
JSON persistence.
"""

import json
import math
import random
import uuid
import threading
from pathlib import Path
from typing import Optional


# ───────────────────────────── Math helpers ─────────────────────────────

def _dot(a: list[float], b: list[float]) -> float:
    s = 0.0
    for x, y in zip(a, b):
        s += x * y
    return s


def _norm(a: list[float]) -> float:
    return math.sqrt(_dot(a, a))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    na, nb = _norm(a), _norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return _dot(a, b) / (na * nb)


def cosine_distance(a: list[float], b: list[float]) -> float:
    return 1.0 - cosine_similarity(a, b)


# ───────────────────────────── Data types ───────────────────────────────

class VectorEntry:
    __slots__ = ("id", "vector", "content", "metadata")

    def __init__(self, id: str, vector: list[float], content: str, metadata: dict):
        self.id = id
        self.vector = vector
        self.content = content
        self.metadata = metadata

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vector": self.vector,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VectorEntry":
        return cls(d["id"], d["vector"], d["content"], d["metadata"])


class SearchResult:
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


# ───────────────────────── Brute-Force Store ────────────────────────────

class BruteForceStore:
    """O(n) cosine similarity search over all vectors. Simple and correct."""

    def __init__(self):
        self.entries: dict[str, VectorEntry] = {}

    def add(
        self,
        vectors: list[list[float]],
        contents: list[str],
        metadatas: list[dict],
        ids: list[str] | None = None,
    ) -> list[str]:
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        for vid, vec, content, meta in zip(ids, vectors, contents, metadatas):
            self.entries[vid] = VectorEntry(vid, vec, content, meta)
        return ids

    def search(self, query_vector: list[float], k: int = 5) -> list[SearchResult]:
        scored = []
        for entry in self.entries.values():
            sim = cosine_similarity(query_vector, entry.vector)
            scored.append((sim, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            SearchResult(e.id, e.content, e.metadata, sim)
            for sim, e in scored[:k]
        ]

    def delete(self, ids: list[str]) -> int:
        count = 0
        for vid in ids:
            if vid in self.entries:
                del self.entries[vid]
                count += 1
        return count

    def delete_by_metadata(self, key: str, value: str) -> int:
        to_delete = [
            eid for eid, e in self.entries.items()
            if e.metadata.get(key) == value
        ]
        return self.delete(to_delete)

    def get_all(self) -> list[VectorEntry]:
        return list(self.entries.values())

    def count(self) -> int:
        return len(self.entries)


# ──────────────────────────── HNSW Store ────────────────────────────────

class HNSWStore:
    """
    Hierarchical Navigable Small World graph — implemented from scratch.

    Key concepts:
    - Multi-layer skip-list style graph
    - Each node connects to M nearest neighbors on its layer
    - Higher layers = fewer nodes, longer skip connections
    - Search: greedy descent from top layer, refine at layer 0 with beam search

    Parameters:
    - M: max neighbors per node per layer (default 16)
    - ef_construction: beam width when inserting (default 200)
    - ef_search: beam width when querying (default 150)
    """

    def __init__(self, M: int = 16, ef_construction: int = 200, ef_search: int = 150):
        self.M = M
        self.M_max0 = M * 2  # layer 0 allows double neighbors
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.ml = 1.0 / math.log(M) if M > 1 else 1.0

        self.entries: dict[str, VectorEntry] = {}
        # graph[layer][node_id] = set of neighbor_ids
        self.graph: dict[int, dict[str, set]] = {}
        self.entry_point: Optional[str] = None
        self.max_layer: int = -1
        self.node_layers: dict[str, int] = {}  # node_id -> max layer assigned

    def _random_layer(self) -> int:
        return int(-math.log(random.random()) * self.ml)

    def _distance(self, id_a: str, id_b: str) -> float:
        return cosine_distance(self.entries[id_a].vector, self.entries[id_b].vector)

    def _distance_to_vec(self, vec: list[float], node_id: str) -> float:
        return cosine_distance(vec, self.entries[node_id].vector)

    def _search_layer(
        self,
        query_vec: list[float],
        entry_points: list[str],
        ef: int,
        layer: int,
    ) -> list[tuple[float, str]]:
        """Greedy beam search on a single layer. Returns list of (dist, node_id)."""
        visited = set(entry_points)
        # candidates: min-heap by distance (closest first)
        candidates = []
        # results: max-heap by -distance (farthest result first for trimming)
        results = []

        for ep in entry_points:
            d = self._distance_to_vec(query_vec, ep)
            candidates.append((d, ep))
            results.append((d, ep))

        candidates.sort()
        results.sort()

        while candidates:
            # Get closest candidate
            c_dist, c_id = candidates[0]
            candidates = candidates[1:]

            # Farthest in results
            f_dist = results[-1][0] if results else float("inf")
            if c_dist > f_dist and len(results) >= ef:
                break

            # Explore neighbors of c_id on this layer
            neighbors = self.graph.get(layer, {}).get(c_id, set())
            for n_id in neighbors:
                if n_id not in visited:
                    visited.add(n_id)
                    n_dist = self._distance_to_vec(query_vec, n_id)
                    f_dist = results[-1][0] if results else float("inf")

                    if n_dist < f_dist or len(results) < ef:
                        candidates.append((n_dist, n_id))
                        candidates.sort()
                        results.append((n_dist, n_id))
                        results.sort()
                        if len(results) > ef:
                            results = results[:ef]

        return results

    def _select_neighbors(
        self,
        query_vec: list[float],
        candidates: list[tuple[float, str]],
        M: int,
    ) -> list[str]:
        """Select M nearest neighbors from candidates (simple strategy)."""
        candidates.sort(key=lambda x: x[0])
        return [c_id for _, c_id in candidates[:M]]

    def _connect(self, layer: int, node_a: str, node_b: str) -> None:
        if layer not in self.graph:
            self.graph[layer] = {}
        if node_a not in self.graph[layer]:
            self.graph[layer][node_a] = set()
        if node_b not in self.graph[layer]:
            self.graph[layer][node_b] = set()
        self.graph[layer][node_a].add(node_b)
        self.graph[layer][node_b].add(node_a)

    def _prune_connections(self, node_id: str, layer: int, max_conn: int) -> None:
        if layer not in self.graph or node_id not in self.graph[layer]:
            return
        neighbors = self.graph[layer][node_id]
        if len(neighbors) <= max_conn:
            return
        # Keep closest max_conn neighbors
        scored = [
            (self._distance(node_id, n_id), n_id) for n_id in neighbors
        ]
        scored.sort()
        keep = {n_id for _, n_id in scored[:max_conn]}
        removed = neighbors - keep
        self.graph[layer][node_id] = keep
        # Remove back-links
        for r_id in removed:
            if r_id in self.graph.get(layer, {}):
                self.graph[layer][r_id].discard(node_id)

    def insert(self, entry: VectorEntry) -> None:
        node_id = entry.id
        self.entries[node_id] = entry
        node_layer = self._random_layer()
        self.node_layers[node_id] = node_layer

        # Initialize graph layers
        for l in range(node_layer + 1):
            if l not in self.graph:
                self.graph[l] = {}
            self.graph[l][node_id] = set()

        if self.entry_point is None:
            self.entry_point = node_id
            self.max_layer = node_layer
            return

        ep = self.entry_point
        query_vec = entry.vector

        # Phase 1: Greedy descent from top to node_layer + 1
        for l in range(self.max_layer, node_layer, -1):
            results = self._search_layer(query_vec, [ep], 1, l)
            if results:
                ep = results[0][1]

        # Phase 2: Insert at layers node_layer down to 0
        eps = [ep]
        for l in range(min(node_layer, self.max_layer), -1, -1):
            candidates = self._search_layer(query_vec, eps, self.ef_construction, l)
            max_conn = self.M_max0 if l == 0 else self.M
            neighbors = self._select_neighbors(query_vec, candidates, max_conn)

            for n_id in neighbors:
                self._connect(l, node_id, n_id)
                # Prune neighbor if it has too many connections
                self._prune_connections(n_id, l, max_conn)

            eps = [c_id for _, c_id in candidates[:self.ef_construction]]

        # Update entry point if new node is at a higher layer
        if node_layer > self.max_layer:
            self.entry_point = node_id
            self.max_layer = node_layer

    def add(
        self,
        vectors: list[list[float]],
        contents: list[str],
        metadatas: list[dict],
        ids: list[str] | None = None,
    ) -> list[str]:
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        for vid, vec, content, meta in zip(ids, vectors, contents, metadatas):
            entry = VectorEntry(vid, vec, content, meta)
            self.insert(entry)
        return ids

    def search(self, query_vector: list[float], k: int = 5) -> list[SearchResult]:
        if self.entry_point is None:
            return []

        ep = self.entry_point
        # Greedy descent from top layer to layer 1
        for l in range(self.max_layer, 0, -1):
            results = self._search_layer(query_vector, [ep], 1, l)
            if results:
                ep = results[0][1]

        # Search layer 0 with ef_search beam width
        candidates = self._search_layer(query_vector, [ep], max(self.ef_search, k), 0)
        candidates.sort(key=lambda x: x[0])
        top_k = candidates[:k]

        return [
            SearchResult(
                c_id,
                self.entries[c_id].content,
                self.entries[c_id].metadata,
                1.0 - dist,  # convert distance back to similarity
            )
            for dist, c_id in top_k
        ]

    def delete(self, ids: list[str]) -> int:
        count = 0
        for vid in ids:
            if vid not in self.entries:
                continue
            # Remove from all graph layers
            max_l = self.node_layers.get(vid, 0)
            for l in range(max_l + 1):
                if l in self.graph and vid in self.graph[l]:
                    # Remove back-links from neighbors
                    for n_id in list(self.graph[l][vid]):
                        if n_id in self.graph[l]:
                            self.graph[l][n_id].discard(vid)
                    del self.graph[l][vid]
            del self.entries[vid]
            del self.node_layers[vid]
            count += 1

        # Re-elect entry point if deleted
        if self.entry_point not in self.entries:
            if self.entries:
                # Pick node at the highest layer
                best_id = max(self.node_layers, key=self.node_layers.get)
                self.entry_point = best_id
                self.max_layer = self.node_layers[best_id]
            else:
                self.entry_point = None
                self.max_layer = -1

        return count

    def delete_by_metadata(self, key: str, value: str) -> int:
        to_delete = [
            eid for eid, e in self.entries.items()
            if e.metadata.get(key) == value
        ]
        return self.delete(to_delete)

    def get_all(self) -> list[VectorEntry]:
        return list(self.entries.values())

    def count(self) -> int:
        return len(self.entries)

    def get_stats(self) -> dict:
        return {
            "total_nodes": len(self.entries),
            "max_layer": self.max_layer,
            "layers": {
                l: len(nodes) for l, nodes in sorted(self.graph.items())
            },
            "M": self.M,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
        }


# ─────────────────────── Unified Vector Store ───────────────────────────

class VectorStore:
    """
    Unified vector store with pluggable backend (brute-force or HNSW).
    Supports namespaces (prefixes) for separate collections (docs vs chat memory).
    Persists to JSON.
    """

    def __init__(
        self,
        persist_path: str,
        method: str = "brute_force",
        hnsw_M: int = 16,
        hnsw_ef_construction: int = 200,
        hnsw_ef_search: int = 150,
    ):
        self.persist_path = persist_path
        self.method = method
        self._lock = threading.RLock()  # RLock allows reentrant acquisition

        self.brute_store = BruteForceStore()
        self.hnsw_store = HNSWStore(hnsw_M, hnsw_ef_construction, hnsw_ef_search)

        self._load()

    @property
    def _active(self):
        return self.hnsw_store if self.method == "hnsw" else self.brute_store

    def set_method(self, method: str) -> None:
        self.method = method

    def add(
        self,
        vectors: list[list[float]],
        contents: list[str],
        metadatas: list[dict],
        ids: list[str] | None = None,
        namespace: str = "",
    ) -> list[str]:
        with self._lock:
            if ids is None:
                ids = [f"{namespace}{str(uuid.uuid4())}" for _ in vectors]
            elif namespace:
                ids = [f"{namespace}{vid}" for vid in ids]

            # Add to both stores so switching is seamless
            self.brute_store.add(vectors, contents, metadatas, ids)
            self.hnsw_store.add(vectors, contents, metadatas, ids)
            self.save()
            return ids

    def search(
        self,
        query_vector: list[float],
        k: int = 5,
        namespace: str = "",
        method_override: str | None = None,
    ) -> list[SearchResult]:
        store = self.hnsw_store if (method_override or self.method) == "hnsw" else self.brute_store
        results = store.search(query_vector, k * 3 if namespace else k)
        if namespace:
            results = [r for r in results if r.id.startswith(namespace)]
            results = results[:k]
        return results

    def delete_by_ids(self, ids: list[str]) -> int:
        with self._lock:
            c1 = self.brute_store.delete(ids)
            c2 = self.hnsw_store.delete(ids)
            self.save()
            return max(c1, c2)

    def delete_by_metadata(self, key: str, value: str, namespace: str = "") -> int:
        with self._lock:
            if namespace:
                to_delete = [
                    e.id for e in self.brute_store.get_all()
                    if e.id.startswith(namespace) and e.metadata.get(key) == value
                ]
            else:
                to_delete = [
                    e.id for e in self.brute_store.get_all()
                    if e.metadata.get(key) == value
                ]
            if not to_delete:
                return 0
            count = self.delete_by_ids(to_delete)
            self.save()
            return count

    def get_all(self, namespace: str = "") -> list[VectorEntry]:
        entries = self.brute_store.get_all()
        if namespace:
            entries = [e for e in entries if e.id.startswith(namespace)]
        return entries

    def count(self, namespace: str = "") -> int:
        if namespace:
            return len([e for e in self.brute_store.get_all() if e.id.startswith(namespace)])
        return self.brute_store.count()

    def get_stats(self) -> dict:
        return {
            "method": self.method,
            "total_entries": self.brute_store.count(),
            "hnsw": self.hnsw_store.get_stats(),
        }

    # ────────────────────── Persistence ──────────────────────

    def save(self) -> None:
        path = Path(self.persist_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "method": self.method,
            "entries": [e.to_dict() for e in self.brute_store.get_all()],
            "hnsw_config": {
                "M": self.hnsw_store.M,
                "ef_construction": self.hnsw_store.ef_construction,
                "ef_search": self.hnsw_store.ef_search,
            },
        }

        tmp_path = str(path) + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        Path(tmp_path).replace(path)

    def _load(self) -> None:
        path = Path(self.persist_path)
        if not path.exists():
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        entries = [VectorEntry.from_dict(d) for d in data.get("entries", [])]
        hnsw_cfg = data.get("hnsw_config", {})
        self.hnsw_store = HNSWStore(
            M=hnsw_cfg.get("M", self.hnsw_store.M),
            ef_construction=hnsw_cfg.get("ef_construction", self.hnsw_store.ef_construction),
            ef_search=hnsw_cfg.get("ef_search", self.hnsw_store.ef_search),
        )

        # Rebuild both stores from entries
        if entries:
            ids = [e.id for e in entries]
            vectors = [e.vector for e in entries]
            contents = [e.content for e in entries]
            metadatas = [e.metadata for e in entries]
            self.brute_store.add(vectors, contents, metadatas, ids)
            self.hnsw_store.add(vectors, contents, metadatas, ids)


# ─────────────────────── Singleton ──────────────────────────

_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        from config import settings
        _store = VectorStore(
            persist_path=settings.VECTOR_STORE_FILE,
            method="brute_force",
            hnsw_M=settings.HNSW_M,
            hnsw_ef_construction=settings.HNSW_EF_CONSTRUCTION,
            hnsw_ef_search=settings.HNSW_EF_SEARCH,
        )
    return _store
