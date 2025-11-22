"""
BM25 Index implementation for hybrid search.
Provides a simple interface for building and querying BM25 index.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Tuple


class BM25Index:
    """BM25 index with add_document/finalize/score interface."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 index.
        
        Args:
            k1: BM25 tuning parameter (default: 1.5)
            b: BM25 tuning parameter (default: 0.75)
        """
        self.k1 = k1
        self.b = b
        self.inverted_index: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.doc_lengths: Dict[str, int] = {}
        self.num_docs = 0
        self.avg_doc_length = 0.0
        self._finalized = False
    
    def add_document(self, doc_id: str, tokens: List[str]):
        """
        Add a document to the index.
        
        Args:
            doc_id: Document identifier
            tokens: List of preprocessed tokens
        """
        if self._finalized:
            raise RuntimeError("Cannot add documents after finalize() has been called")
        
        doc_length = len(tokens)
        self.doc_lengths[doc_id] = doc_length
        
        # Count term frequencies
        term_freqs = Counter(tokens)
        
        # Update inverted index
        for term, freq in term_freqs.items():
            self.inverted_index[term].append((doc_id, freq))
        
        self.num_docs += 1
    
    def finalize(self):
        """Finalize the index and compute statistics."""
        if self._finalized:
            return
        
        if self.num_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.num_docs
        
        self._finalized = True
    
    def _calculate_idf(self, term: str) -> float:
        """Calculate IDF for a term."""
        import math
        if term not in self.inverted_index or self.num_docs == 0:
            return 0.0
        # Document frequency is the number of unique documents containing the term
        unique_docs = len(set(doc_id for doc_id, _ in self.inverted_index[term]))
        if unique_docs == 0:
            return 0.0
        return math.log((self.num_docs - unique_docs + 0.5) / (unique_docs + 0.5) + 1)
    
    def score(self, query_tokens: List[str], k: int = 10) -> List[Tuple[str, float]]:
        """
        Score documents for query tokens and return top-k.
        
        Args:
            query_tokens: List of preprocessed query tokens
            k: Number of top results to return
            
        Returns:
            List of (doc_id, score) tuples sorted by score descending
        """
        if not self._finalized:
            self.finalize()
        
        if not query_tokens or self.num_docs == 0:
            return []
        
        # Collect all candidate documents
        candidate_docs = set()
        for term in query_tokens:
            if term in self.inverted_index:
                for doc_id, _ in self.inverted_index[term]:
                    candidate_docs.add(doc_id)
        
        if not candidate_docs:
            return []
        
        # Calculate BM25 scores
        scores: Dict[str, float] = {}
        for doc_id in candidate_docs:
            doc_length = self.doc_lengths.get(doc_id, 0)
            if doc_length == 0:
                continue
            
            score = 0.0
            for term in query_tokens:
                if term not in self.inverted_index:
                    continue
                
                # Find term frequency in this document
                term_freq = 0
                for posting_doc_id, posting_freq in self.inverted_index[term]:
                    if posting_doc_id == doc_id:
                        term_freq = posting_freq
                        break
                
                if term_freq == 0:
                    continue
                
                # Calculate BM25 component
                idf = self._calculate_idf(term)
                numerator = term_freq * (self.k1 + 1)
                denominator = term_freq + self.k1 * (
                    1 - self.b + self.b * (doc_length / self.avg_doc_length)
                )
                score += idf * (numerator / denominator)
            
            if score > 0:
                scores[doc_id] = score
        
        # Sort by score and return top-k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:k]

