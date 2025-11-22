"""
Embedding-based vector index for semantic search.

Uses sentence-transformers if available. Builds an in-memory index (numpy matrix)
and computes cosine similarity by normalized dot-product. Lightweight and easy to
drop into your current pipeline.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    SentenceTransformer = None  # handled at runtime

class EmbeddingIndex:
    def __init__(self, model_name: str = "all-mpnet-base-v2", normalize: bool = True):
        """
        model_name: sentence-transformers model id. Defaults to a high-quality model.
        normalize: whether to L2-normalize vectors (recommended).
        """
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers not installed. Install with:\n"
                "  pip install -U sentence-transformers\n"
                "or choose to run BM25-only mode."
            )
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.normalize = normalize
        self._id_to_idx: Dict[str, int] = {}
        self._idx_to_id: List[str] = []
        self._emb_matrix: Optional[np.ndarray] = None  # shape (N, D)

    def build(self, docs: Iterable[Tuple[str, str]]):
        """
        docs: iterable of (doc_id, text)
        Builds embedding matrix and mappings.
        """
        doc_list = list(docs)
        if not doc_list:
            self._emb_matrix = None
            self._id_to_idx.clear()
            self._idx_to_id.clear()
            return

        texts = [t for (_, t) in doc_list]
        ids = [i for (i, _) in doc_list]
        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        if self.normalize:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vectors = vectors / norms

        self._emb_matrix = vectors.astype(np.float32)
        self._idx_to_id = ids
        self._id_to_idx = {doc_id: idx for idx, doc_id in enumerate(self._idx_to_id)}

    def search(self, query: str, k: int = 10) -> List[Tuple[str, float]]:
        """
        Return list of (doc_id, cosine_score) sorted by score desc.
        Cosine is in [-1, 1] if normalized, otherwise raw dot-product.
        """
        if self._emb_matrix is None:
            return []

        qvec = self.model.encode([query], convert_to_numpy=True)[0]
        if self.normalize:
            qnorm = np.linalg.norm(qvec)
            if qnorm == 0:
                qnorm = 1.0
            qvec = qvec / qnorm

        # cosine via dot product with normalized vectors
        scores = np.dot(self._emb_matrix, qvec.astype(np.float32))
        top_idx = np.argsort(-scores)[:k]
        results = [(self._idx_to_id[int(i)], float(scores[int(i)])) for i in top_idx]
        return results

    def get_vector(self, doc_id: str):
        idx = self._id_to_idx.get(doc_id)
        if idx is None or self._emb_matrix is None:
            return None
        return self._emb_matrix[idx]

