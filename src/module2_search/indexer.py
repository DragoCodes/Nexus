"""Inverted index builder for the search engine."""

from __future__ import annotations

import json
import os
import pickle
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Import for hybrid search components
from .bm25 import BM25Index
from .preprocessor import TextPreprocessor

# Alias for compatibility
FinancialTextPreprocessor = TextPreprocessor

# Embedding index may not be available if sentence-transformers is not installed
try:
    from .embeddings import EmbeddingIndex
except ImportError:
    EmbeddingIndex = None  # graceful fallback to BM25-only

DEFAULT_DATASET = "data/articles_export.json"
MOCK_DATASET = "mock_data/sample_articles.json"


class InvertedIndex:
    """Build and manage an inverted index from the corpus."""
    
    def __init__(self, preprocessor):
        """
        Initialize the inverted index.
        
        Args:
            preprocessor: TextPreprocessor instance
        """
        self.preprocessor = preprocessor
        self.index = {}  # {term: [(doc_id, term_freq), ...]}
        self.doc_lengths = {}  # {doc_id: length}
        self.avg_doc_length = 0
        self.num_docs = 0
    
    def build_from_db(self, db_handler):
        """
        Build inverted index from database articles.
        
        Args:
            db_handler: Database handler instance with get_all_articles() method
        """
        print("Fetching articles from database...")
        articles = db_handler.get_all_articles()
        
        if not articles:
            print("No articles found in database!")
            return
        
        print(f"Found {len(articles)} articles. Building index...")
        
        # Build index
        for idx, article in enumerate(articles):
            doc_id = article['article_id']
            
            # Combine headline and full_text
            headline = article.get('headline', '')
            full_text = article.get('full_text', '')
            text = f"{headline} {full_text}".strip()
            
            # Preprocess text
            tokens = self.preprocessor.preprocess(text)
            
            # Store document length
            self.doc_lengths[doc_id] = len(tokens)
            
            # Count term frequencies
            term_freqs = Counter(tokens)
            
            # Update inverted index
            for term, freq in term_freqs.items():
                if term not in self.index:
                    self.index[term] = []
                self.index[term].append((doc_id, freq))
            
            # Log progress every 50 articles
            if (idx + 1) % 50 == 0:
                print(f"Processed {idx + 1}/{len(articles)} articles...")
        
        # Calculate statistics
        self.num_docs = len(articles)
        if self.num_docs > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.num_docs
        
        # Print final statistics
        print(f"\nIndex build complete!")
        print(f"Total documents: {self.num_docs}")
        print(f"Unique terms: {len(self.index)}")
        print(f"Average document length: {self.avg_doc_length:.2f} tokens")
    
    def get_postings(self, term):
        """
        Get posting list for a term.
        
        Args:
            term: Term to look up
            
        Returns:
            List of (doc_id, term_freq) tuples
        """
        return self.index.get(term, [])
    
    def get_document_frequency(self, term):
        """
        Get document frequency for a term.
        
        Args:
            term: Term to look up
            
        Returns:
            Number of documents containing this term
        """
        return len(self.index.get(term, []))
    
    def save_to_disk(self, filepath):
        """
        Save index to disk using pickle.
        
        Args:
            filepath: Path to save the index
        """
        try:
            data = {
                'index': self.index,
                'doc_lengths': self.doc_lengths,
                'avg_doc_length': self.avg_doc_length,
                'num_docs': self.num_docs
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            
            import os
            file_size = os.path.getsize(filepath) / (1024 * 1024)  # Size in MB
            print(f"Index saved to {filepath}")
            print(f"File size: {file_size:.2f} MB")
        except Exception as e:
            print(f"Error saving index: {e}")
            raise
    
    def load_from_disk(self, filepath):
        """
        Load index from disk.
        
        Args:
            filepath: Path to load the index from
        """
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.index = data['index']
            self.doc_lengths = data['doc_lengths']
            self.avg_doc_length = data['avg_doc_length']
            self.num_docs = data['num_docs']
            
            print(f"Index loaded from {filepath}")
            print(f"Total documents: {self.num_docs}")
            print(f"Unique terms: {len(self.index)}")
            print(f"Average document length: {self.avg_doc_length:.2f} tokens")
        except Exception as e:
            print(f"Error loading index: {e}")
            raise


# ============================================================================
# Hybrid Search Components (BM25 + Embeddings)
# ============================================================================

@dataclass
class ArticleRecord:
    article_id: str
    headline: str
    full_text: str
    source: str
    publication_date: str
    processed: bool = False

    def to_dict(self) -> Dict:
        return {
            "article_id": self.article_id,
            "headline": self.headline,
            "full_text": self.full_text,
            "source": self.source,
            "publication_date": self.publication_date,
            "processed": self.processed,
        }


class ArticleIndexer:
    def __init__(
        self,
        articles_path: str = DEFAULT_DATASET,
        preprocessor: Optional[FinancialTextPreprocessor] = None,
        k1: float = 1.5,
        b: float = 0.75,
        embedding_model: str = "all-mpnet-base-v2",
        embed_alpha: float = 0.6,
    ):
        """
        embed_alpha: weight for embedding score when combining with BM25.
                     final_score = alpha * embed_norm + (1-alpha) * bm25_norm
        """
        self.articles_path = articles_path
        self.preprocessor = preprocessor or FinancialTextPreprocessor()
        self.bm25 = BM25Index(k1=k1, b=b)
        self.articles: Dict[str, ArticleRecord] = {}
        self._indexed = False

        # embedding setup
        self.embedding_model_name = embedding_model
        self.embed_alpha = float(embed_alpha)
        self.embedding_index = None
        if EmbeddingIndex is not None:
            try:
                self.embedding_index = EmbeddingIndex(model_name=self.embedding_model_name)
            except Exception as e:
                # Fall back to BM25-only if embeddings can't be initialized
                self.embedding_index = None

    def load_articles(self, path: Optional[str] = None) -> List[ArticleRecord]:
        dataset_path = path or self.articles_path
        if not os.path.exists(dataset_path):
            if os.path.exists(MOCK_DATASET):
                dataset_path = MOCK_DATASET
            else:
                raise FileNotFoundError(
                    f"No article dataset found at {dataset_path} or {MOCK_DATASET}"
                )

        with open(dataset_path, encoding="utf-8") as handle:
            payload = json.load(handle)

        self.articles = {
            item["article_id"]: ArticleRecord(
                article_id=item["article_id"],
                headline=item.get("headline", ""),
                full_text=item.get("full_text") or item.get("description", ""),
                source=item.get("source", "Unknown"),
                publication_date=item.get("publication_date", ""),
                processed=item.get("processed", False),
            )
            for item in payload
            if item.get("article_id") and item.get("headline")
        }
        return list(self.articles.values())

    def build_index(self):
        if not self.articles:
            self.load_articles()

        # BM25 indexing
        for article in self.articles.values():
            tokens = self.preprocessor.preprocess(article.full_text or article.headline)
            self.bm25.add_document(article.article_id, tokens)
        self.bm25.finalize()

        # Embedding indexing (if available)
        if self.embedding_index is not None:
            # We prefer full_text; fallback to headline
            docs = [(a.article_id, a.full_text or a.headline) for a in self.articles.values()]
            try:
                self.embedding_index.build(docs)
            except Exception as e:
                # if something goes wrong, disable embedding_index
                self.embedding_index = None

        self._indexed = True

    def ensure_index(self):
        if not self._indexed:
            self.build_index()

    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize dict values to [0,1]. If all zeros, return zeros."""
        if not scores:
            return {}
        mx = max(scores.values())
        mn = min(scores.values())
        if mx == mn:
            # All equal -> map to zeros to avoid divide-by-zero
            return {k: 0.0 for k in scores}
        denom = mx - mn
        return {k: (v - mn) / denom for k, v in scores.items()}

    def search(self, query: str, k: int = 10) -> List[Dict]:
        """
        Hybrid search: run BM25 and embeddings (if available), combine scores.
        Results include bm25_score, embed_score, and combined_score.
        """
        query = (query or "").strip()
        if not query:
            return []
        self.ensure_index()

        # 1) BM25 results
        tokens = self.preprocessor.preprocess_query(query)
        bm25_ranked = self.bm25.score(tokens, k=k * 5)  # fetch more to give embeddings room
        bm25_scores = {doc_id: float(score) for doc_id, score in bm25_ranked}

        # 2) Embedding results (if available)
        embed_scores = {}
        if self.embedding_index is not None:
            try:
                embeds = self.embedding_index.search(query, k=k * 5)
                # embed scores are cosine in [-1,1] (if normalized). We'll keep raw for now.
                embed_scores = {doc_id: float(score) for doc_id, score in embeds}
            except Exception:
                embed_scores = {}

        # 3) Combine doc ids
        all_doc_ids = set(bm25_scores.keys()) | set(embed_scores.keys())
        if not all_doc_ids:
            # fallback: return BM25 top-k minimal processed format
            results = []
            for article_id, score in bm25_ranked[:k]:
                article = self.articles.get(article_id)
                if not article:
                    continue
                results.append(
                    {
                        "article_id": article.article_id,
                        "headline": article.headline,
                        "source": article.source,
                        "publication_date": article.publication_date,
                        "bm25_score": round(float(score), 6),
                        "embed_score": None,
                        "combined_score": round(float(score), 6),
                        "snippet": self._build_snippet(article.full_text, tokens),
                    }
                )
            return results

        # 4) Normalize BM25 and embed scores to [0,1]
        bm25_norm = self._normalize_scores(bm25_scores)
        # embeddings are cosine in [-1,1] (if model normalized). Map to [0,1] by (x+1)/2
        embed_norm = {}
        if embed_scores:
            # first normalize embeddings to common range
            # if embeddings are in [-1,1], map to [0,1], else normalize as fallback
            min_e = min(embed_scores.values())
            max_e = max(embed_scores.values())
            if min_e >= -1.001 and max_e <= 1.001:
                # treat as cosine, map to [0,1]
                embed_norm = {k: (v + 1.0) / 2.0 for k, v in embed_scores.items()}
            else:
                embed_norm = self._normalize_scores(embed_scores)

        # ensure every doc has a numeric normalized score (0.0 default)
        combined_scores: Dict[str, float] = {}
        alpha = float(self.embed_alpha)
        for doc_id in all_doc_ids:
            b = bm25_norm.get(doc_id, 0.0)
            e = embed_norm.get(doc_id, 0.0)
            combined = alpha * e + (1.0 - alpha) * b
            combined_scores[doc_id] = combined

        # 5) Rank final
        ranked_docs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:k]

        # 6) Build results payload
        results = []
        for doc_id, combined in ranked_docs:
            article = self.articles.get(doc_id)
            if not article:
                continue
            results.append(
                {
                    "article_id": article.article_id,
                    "headline": article.headline,
                    "source": article.source,
                    "publication_date": article.publication_date,
                    "bm25_score": round(float(bm25_scores.get(doc_id, 0.0)), 6),
                    "embed_score": None
                    if not embed_scores
                    else round(float(embed_scores.get(doc_id, 0.0)), 6),
                    "combined_score": round(float(combined), 6),
                    "snippet": self._build_snippet(article.full_text, tokens),
                }
            )
        return results

    def _build_snippet(self, text: str, query_tokens: List[str], length: int = 240) -> str:
        snippet = (text or "")[:length].strip()
        if len(text) > length:
            snippet += "..."
        if not snippet:
            snippet = "No preview available."
        return snippet

    def get_article(self, article_id: str) -> Optional[Dict]:
        article = self.articles.get(article_id)
        return article.to_dict() if article else None

    def stats(self) -> Dict:
        self.ensure_index()
        return {
            "documents": len(self.articles),
            "avg_doc_length": self.bm25.avg_doc_length,
            "vocabulary_size": len(self.bm25.inverted_index),
            "has_embeddings": self.embedding_index is not None and self.embedding_index._emb_matrix is not None,
        }

