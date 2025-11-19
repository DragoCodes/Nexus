# Nexus System Architecture

## High-Level Overview

Nexus ingests financial news, enriches it with entity/relationship extraction, and exposes search and graph analytics APIs. Four independently developed modules exchange data via JSON contracts and a shared SQLite database.

1. **Ingestion (`ingestion/`):** pulls articles from NewsAPI.org or CSV fallback, stores them in `data/articles.db`, and exports `data/articles_export.json`.
2. **Search (`search/`):** builds a BM25 index from the exported articles, serves `/search` queries via Flask.
3. **Extraction (`extraction/`):** runs LLM-powered entity/relationship extraction on selected articles, caches responses, and saves JSON outputs in `data/extractions/`.
4. **Graph (`graph/`):** loads extraction triples into NetworkX, computes analytics, and serves `/graph` endpoints.

The shared Flask `main.py` app mounts the search and graph blueprints for integration and the optional Streamlit UI consumes those APIs.

## Data Contracts

- **Articles (Ingestion → Search/Extraction):**

  ```json
  {
    "article_id": "uuid",
    "headline": "NVIDIA Announces Partnership with TSMC",
    "full_text": "Full body text…",
    "source": "Reuters",
    "publication_date": "2024-03-15T10:30:00Z",
    "processed": false
  }
  ```

  Stored in SQLite (`articles` table) and exported to `data/articles_export.json`.

- **Extractions (Extraction → Graph):**

  ```json
  {
    "article_id": "uuid",
    "extracted_at": "2024-11-13T14:30:00Z",
    "triples": [
      {
        "entity1": "TSMC",
        "entity1_type": "Company",
        "relationship": "supplies_to",
        "entity2": "NVIDIA",
        "entity2_type": "Company",
        "confidence": 0.95
      }
    ]
  }
  ```

  Each article’s extraction is saved to `data/extractions/{article_id}.json`.

- **Graph Snapshot (Graph → Analytics/UI):**

  ```json
  {
    "nodes": [{"id": "NVIDIA", "type": "Company", "pagerank": 0.0234}],
    "edges": [{"source": "TSMC", "relationship": "supplies_to", "target": "NVIDIA", "count": 3}]
  }
  ```

  Used internally for analytics and exported for visualization (e.g., `mock_data/mock_graph.json`).

## Integration Workflow

1. `ingestion/news_fetcher.py` populates SQLite; `ingestion/mock_generator.py` can seed mock entries.
2. `search/indexer.py` reads `data/articles_export.json`, builds the inverted index, and starts the Flask API.
3. `extraction/batch_process.py` selects articles (from search results or database), queries the LLM, caches responses, and stores triples.
4. `graph/builder.py` loads extraction JSON files, updates NetworkX, runs analytics (`graph/analytics.py`), and serves endpoints via `graph/api.py`.

## Deployment & Branching

- Branches per member (`member1-ingestion`, etc.), merged into protected `main` after review.
- `.env` holds API keys (NewsAPI, OpenAI-compatible). Modules must fail gracefully when keys are absent by falling back to mock data.
- Mock data files under `mock_data/` unblock development without live services.

## Testing & Demo

- Each module supplies focused unit tests (`tests/test_search.py`, `tests/test_graph.py`, etc.).
- The end-to-end rehearsal (Day 5) executes ingestion → search → extraction → graph, then serves `/search` + `/graph`.
- `streamlit_demo.py` provides a lightweight UI that calls the Flask endpoints for demo purposes.
