# Article Harvester & Database Manager

## Quick Start
```bash
python ingestion/news_fetcher.py --use-mock mock_data/sample_articles.json
python ingestion/mock_generator.py --count 50 --out data/articles.db
```

## Testing with Mock Data
```bash
pytest tests/test_ingestion.py
```

## API / CLI Examples
- Initialize database schema: `python ingestion/database.py --init`
- Insert CSV: `python ingestion/database.py --import data/news.csv`
- Export JSON: `python ingestion/database.py --export data/articles_export.json`

Environment: set `NEWSAPI_KEY` in `.env` to hit the live API; otherwise scripts fall back to `mock_data/sample_articles.json`.

