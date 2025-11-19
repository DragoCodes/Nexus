"""
Flask blueprint exposing the BM25 search engine.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from flask import Blueprint, jsonify, request

from search.indexer import ArticleIndexer


def _create_indexer(dataset: Optional[str] = None) -> ArticleIndexer:
    path = dataset or os.getenv("NEXUS_ARTICLE_DATA", "data/articles_export.json")
    indexer = ArticleIndexer(articles_path=path)
    try:
        indexer.load_articles()
        indexer.build_index()
    except FileNotFoundError:
        # Delay building until a dataset appears
        pass
    return indexer


@lru_cache(maxsize=1)
def get_indexer() -> ArticleIndexer:
    return _create_indexer()


search_blueprint = Blueprint("search", __name__)


@search_blueprint.route("/health", methods=["GET"])
def health():
    indexer = get_indexer()
    return jsonify(
        {
            "status": "ok",
            "documents": len(indexer.articles),
            "avg_doc_length": indexer.bm25.avg_doc_length,
        }
    )


@search_blueprint.route("/search", methods=["GET"])
def search_endpoint():
    query = request.args.get("q", "").strip()
    k = int(request.args.get("k", 10))
    indexer = get_indexer()
    results = indexer.search(query=query, k=k)
    return jsonify(
        {
            "query": query,
            "results": results,
            "returned": len(results),
            "total_documents": len(indexer.articles),
        }
    )


@search_blueprint.route("/article/<article_id>", methods=["GET"])
def get_article(article_id: str):
    indexer = get_indexer()
    article = indexer.get_article(article_id)
    if article is None:
        return jsonify({"error": "article not found"}), 404
    return jsonify(article)


@search_blueprint.route("/stats", methods=["GET"])
def stats():
    indexer = get_indexer()
    return jsonify(indexer.stats())


@search_blueprint.route("/reload", methods=["POST"])
def reload_index():
    dataset = request.json.get("dataset") if request.is_json else None
    get_indexer.cache_clear()
    indexer = _create_indexer(dataset)
    get_indexer.cache_info()  # prime cache
    return jsonify({"status": "reloaded", "documents": len(indexer.articles)})
