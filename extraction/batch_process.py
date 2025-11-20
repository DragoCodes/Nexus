"""
Batch extraction runner.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List, Optional

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from extraction.cache import ExtractionCache
from extraction.llm_client import LLMClient
from extraction.parser import parse_llm_response

DEFAULT_ARTICLES = "data/articles_export.json"


def load_articles(path: str) -> List[Dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Articles file not found: {path}")
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run entity extraction over articles.")
    parser.add_argument("--articles", default=DEFAULT_ARTICLES)
    parser.add_argument("--article-id", help="Process a single article_id")
    parser.add_argument("--limit", type=int, help="Limit number of articles")
    parser.add_argument("--mock-responses", default="mock_data/mock_llm_responses.json")
    parser.add_argument("--cache-dir", default="data/extractions")
    parser.add_argument("--force", action="store_true", help="Reprocess even if cached")
    return parser.parse_args()


def main():
    args = parse_args()
    articles = load_articles(args.articles if os.path.exists(args.articles) else args.mock_responses)
    if args.article_id:
        articles = [a for a in articles if a.get("article_id") == args.article_id]
    if args.limit:
        articles = articles[: args.limit]

    mock_data = []
    if args.mock_responses and os.path.exists(args.mock_responses):
        with open(args.mock_responses, encoding="utf-8") as handle:
            mock_data = json.load(handle)

    client = LLMClient(mock_responses=mock_data)
    cache = ExtractionCache(cache_dir=args.cache_dir)

    processed = 0
    skipped = 0

    for article in articles:
        article_id = article["article_id"]
        if cache.exists(article_id) and not args.force:
            skipped += 1
            continue

        output = client.generate(article_id, article.get("full_text") or article.get("headline", ""))
        payload = parse_llm_response(
            article_id=article_id,
            raw_response=output,
            metadata={
                "headline": article.get("headline"),
                "source": article.get("source"),
                "publication_date": article.get("publication_date"),
            },
        )
        cache.save(article_id, payload)
        processed += 1

    print(
        json.dumps(
            {"processed": processed, "skipped": skipped, "cache_dir": args.cache_dir},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
