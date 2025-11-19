"""
Indexer for BM25 Search
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from search.bm25 import BM25Index
from search.preprocessor import FinancialTextPreprocessor


DEFAULT_DATASET = "data/articles_export.json"
MOCK_DATASET = "mock_data/sample_articles.json"


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
    ):
        self.articles_path = articles_path
        self.preprocessor = preprocessor or FinancialTextPreprocessor()
        self.bm25 = BM25Index(k1=k1, b=b)
        self.articles: Dict[str, ArticleRecord] = {}
        self._indexed = False

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

        for article in self.articles.values():
            tokens = self.preprocessor.preprocess(article.full_text or article.headline)
            self.bm25.add_document(article.article_id, tokens)
        self.bm25.finalize()
        self._indexed = True

    def ensure_index(self):
        if not self._indexed:
            self.build_index()

    def search(self, query: str, k: int = 10) -> List[Dict]:
        query = (query or "").strip()
        if not query:
            return []
        self.ensure_index()
        tokens = self.preprocessor.preprocess_query(query)
        ranked = self.bm25.score(tokens, k=k)
        results = []
        for article_id, score in ranked:
            article = self.articles.get(article_id)
            if not article:
                continue
            results.append(
                {
                    "article_id": article.article_id,
                    "headline": article.headline,
                    "source": article.source,
                    "publication_date": article.publication_date,
                    "bm25_score": round(score, 4),
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
        }
