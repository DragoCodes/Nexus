"""
BM25 Ranking Implementation
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.inverted_index: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.document_lengths: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.num_documents: int = 0

    def add_document(self, doc_id: str, tokens: Iterable[str]):
        """Add a document to the inverted index."""
        token_counts = Counter(tokens)
        self.document_lengths[doc_id] = sum(token_counts.values())

        for term, freq in token_counts.items():
            if doc_id not in self.inverted_index[term]:
                self.doc_freqs[term] += 1
            self.inverted_index[term][doc_id] = freq

    def finalize(self):
        """Finalize the index and compute averages."""
        self.num_documents = len(self.document_lengths)
        if self.num_documents == 0:
            self.avg_doc_length = 0.0
        else:
            self.avg_doc_length = sum(self.document_lengths.values()) / self.num_documents

    def _idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        if df == 0 or self.num_documents == 0:
            return 0.0
        return math.log(1 + (self.num_documents - df + 0.5) / (df + 0.5))

    def score(self, query_tokens: Iterable[str], k: int = 10) -> List[Tuple[str, float]]:
        """Score documents for the given query tokens."""
        scores: Dict[str, float] = defaultdict(float)
        for term in query_tokens:
            postings = self.inverted_index.get(term)
            if not postings:
                continue
            idf = self._idf(term)
            for doc_id, freq in postings.items():
                doc_len = self.document_lengths.get(doc_id, 1)
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (
                    1 - self.b + self.b * (doc_len / (self.avg_doc_length or 1))
                )
                scores[doc_id] += idf * (numerator / denominator)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:k]
