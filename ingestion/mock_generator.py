"""
Mock Article Generator
----------------------
Creates synthetic financial articles for local development/testing.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import List

from faker import Faker

from ingestion.database import ArticleDatabase

DEFAULT_OUTPUT = "mock_data/sample_articles.json"


def generate_articles(count: int, seed: int | None = None) -> List[dict]:
    faker = Faker()
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)

    companies = [
        "NVIDIA",
        "TSMC",
        "Apple",
        "Microsoft",
        "Amazon",
        "Meta",
        "Alphabet",
        "Intel",
        "AMD",
        "Samsung",
        "ASML",
    ]
    actions = [
        "announced",
        "expanded",
        "partnered on",
        "secured",
        "invested in",
        "launched",
        "accelerated",
        "reported",
        "opened",
        "scaled",
    ]
    initiatives = [
        "AI accelerator program",
        "cloud data center",
        "chip supply agreement",
        "semiconductor alliance",
        "autonomous driving stack",
        "edge computing rollout",
        "quantum research hub",
    ]

    base_time = datetime(2024, 3, 1, 12, 0, 0)
    articles: List[dict] = []
    for i in range(count):
        company = random.choice(companies)
        partner = random.choice([c for c in companies if c != company])
        action = random.choice(actions)
        initiative = random.choice(initiatives)
        headline = f"{company} {action} {initiative}"
        body = (
            f"{company} {action} a {initiative} alongside {partner}. "
            f"{faker.sentence()} {faker.sentence()}"
        )
        publication_date = (base_time + timedelta(hours=3 * i)).isoformat() + "Z"
        articles.append(
            {
                "article_id": str(uuid.uuid4()),
                "headline": headline,
                "full_text": body,
                "source": faker.company(),
                "publication_date": publication_date,
                "url": faker.url(),
                "processed": False,
            }
        )
    return articles


def write_json(payload: List[dict], output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate mock financial articles.")
    parser.add_argument("--count", type=int, default=50, help="Number of articles")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, help="JSON output path")
    parser.add_argument("--db-path", default="data/articles.db")
    parser.add_argument(
        "--insert",
        action="store_true",
        help="Also insert generated articles into SQLite database",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    articles = generate_articles(args.count, seed=args.seed)
    write_json(articles, args.out)
    print(f"Mock dataset saved to {args.out} ({len(articles)} articles)")

    if args.insert:
        db = ArticleDatabase(db_path=args.db_path)
        stats = db.bulk_insert(articles)
        db.export_to_json()
        print("Inserted into database:", stats)


if __name__ == "__main__":
    main()
