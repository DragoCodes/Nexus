import json
from pathlib import Path

from search.indexer import ArticleIndexer
from search.preprocessor import FinancialTextPreprocessor


def test_preprocessor_preserves_special_tokens():
    pre = FinancialTextPreprocessor()
    text = "Apple reports $100M buyback for $AAPL shares, up 25%."
    tokens = pre.preprocess(text)
    assert "$aapl" in tokens
    assert "25%" in tokens


def test_indexer_search_returns_results(tmp_path: Path):
    with open("mock_data/sample_articles.json", encoding="utf-8") as handle:
        articles = json.load(handle)[:5]

    dataset = tmp_path / "articles.json"
    with open(dataset, "w", encoding="utf-8") as handle:
        json.dump(articles, handle)

    indexer = ArticleIndexer(articles_path=str(dataset))
    indexer.load_articles()
    indexer.build_index()
    results = indexer.search("NVIDIA", k=3)
    assert results
    assert results[0]["bm25_score"] > 0
