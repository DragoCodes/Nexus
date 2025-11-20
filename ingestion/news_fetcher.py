"""
Article Harvester
-----------------
- Pulls financial articles from NewsAPI.org (or CSV/JSON fallback)
- Writes results into SQLite via ArticleDatabase
- Exports canonical JSON for downstream modules
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import requests
from dotenv import load_dotenv
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ingestion.database import ArticleDatabase


load_dotenv()

NEWSAPI_URL = "https://newsapi.org/v2/everything"
DEFAULT_EXPORT = "data/articles_export.json"


@dataclass
class Article:
    article_id: str
    headline: str
    full_text: str
    source: str
    publication_date: str
    url: str = ""
    processed: bool = False

    @classmethod
    def from_newsapi(cls, payload: Dict) -> "Article":
        return cls(
            article_id=payload.get("id") or str(uuid.uuid4()),
            headline=payload.get("title") or "Untitled Article",
            full_text=payload.get("content") or payload.get("description") or "",
            source=(payload.get("source") or {}).get("name", "Unknown"),
            publication_date=payload.get("publishedAt")
            or datetime.utcnow().isoformat() + "Z",
            url=payload.get("url") or "",
            processed=False,
        )

    @classmethod
    def from_csv(cls, row: Dict) -> "Article":
        return cls(
            article_id=row.get("article_id") or str(uuid.uuid4()),
            headline=row.get("title") or row.get("headline") or "Untitled",
            full_text=row.get("full_text") or row.get("description") or "",
            source=row.get("source") or "Unknown",
            publication_date=row.get("publishedAt")
            or row.get("publication_date")
            or datetime.utcnow().isoformat() + "Z",
            url=row.get("url") or "",
            processed=str(row.get("processed", "false")).lower() == "true",
        )

    def to_dict(self) -> Dict:
        return {
            "article_id": self.article_id,
            "headline": self.headline,
            "full_text": self.full_text,
            "source": self.source,
            "publication_date": self.publication_date,
            "url": self.url,
            "processed": self.processed,
        }


def fetch_from_newsapi(
    query: str,
    api_key: str,
    page_size: int = 50,
    max_pages: int = 2,
    language: str = "en",
) -> List[Article]:
    """Fetch articles using NewsAPI."""
    if not api_key:
        raise RuntimeError("NEWSAPI_KEY not provided. Supply via env or --api-key.")

    articles: List[Article] = []
    for page in range(1, max_pages + 1):
        params = {
            "q": query,
            "language": language,
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "page": page,
        }
        resp = requests.get(
            NEWSAPI_URL,
            params=params,
            headers={"X-Api-Key": api_key},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"NewsAPI error {resp.status_code}: {resp.text[:200]}"
            )
        data = resp.json()
        for item in data.get("articles", []):
            articles.append(Article.from_newsapi(item))

        if page >= data.get("totalResults", 0) // page_size + 1:
            break

        time.sleep(1)  # respect rate limits

    return articles


def load_from_csv(csv_path: str) -> List[Article]:
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [Article.from_csv(row) for row in reader]


def load_from_json(json_path: str) -> List[Article]:
    with open(json_path, encoding="utf-8") as handle:
        data = json.load(handle)
    articles = []
    for item in data:
        articles.append(
            Article(
                article_id=item.get("article_id") or str(uuid.uuid4()),
                headline=item["headline"],
                full_text=item.get("full_text") or item.get("description", ""),
                source=item.get("source", "Unknown"),
                publication_date=item.get("publication_date")
                or datetime.utcnow().isoformat() + "Z",
                url=item.get("url", ""),
                processed=item.get("processed", False),
            )
        )
    return articles


def persist_articles(
    articles: Iterable[Article],
    db_path: str,
    export_path: str,
    dry_run: bool = False,
) -> Dict[str, int]:
    articles_list = [article.to_dict() for article in articles]
    if dry_run:
        with open(export_path, "w", encoding="utf-8") as handle:
            json.dump(articles_list, handle, indent=2, ensure_ascii=False)
        return {"inserted": 0, "duplicates": 0, "errors": 0, "exported": len(articles_list)}

    database = ArticleDatabase(db_path=db_path)
    stats = database.bulk_insert(articles_list)
    exported = database.export_to_json(export_path)
    stats["exported"] = exported
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest articles into SQLite.")
    parser.add_argument("--query", default="NVIDIA", help="NewsAPI query string")
    parser.add_argument("--api-key", default=os.getenv("NEWSAPI_KEY"))
    parser.add_argument("--from-csv", help="Path to CSV fallback dataset")
    parser.add_argument("--use-mock", help="Path to JSON mock dataset")
    parser.add_argument("--db-path", default="data/articles.db")
    parser.add_argument("--export-json", default=DEFAULT_EXPORT)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true", help="Skip DB writes")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.use_mock and not os.path.exists(args.use_mock):
        raise FileNotFoundError(f"Mock data not found: {args.use_mock}")

    if args.from_csv and not os.path.exists(args.from_csv):
        raise FileNotFoundError(f"CSV file not found: {args.from_csv}")

    if args.use_mock:
        print(f"Loading mock articles from {args.use_mock}")
        articles = load_from_json(args.use_mock)
    elif args.from_csv:
        print(f"Ingesting articles from CSV {args.from_csv}")
        articles = load_from_csv(args.from_csv)
    else:
        print(f"Fetching articles from NewsAPI with query '{args.query}'")
        articles = fetch_from_newsapi(
            query=args.query,
            api_key=args.api_key,
            page_size=args.page_size,
            max_pages=args.max_pages,
        )

    if not articles:
        print("No articles found. Nothing to insert.")
        sys.exit(0)

    stats = persist_articles(
        articles=articles,
        db_path=args.db_path,
        export_path=args.export_json,
        dry_run=args.dry_run,
    )

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
