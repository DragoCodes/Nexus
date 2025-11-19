# `data/articles.db` Schema

SQLite database created/managed by `ingestion/database.py`. Use `sqlite3 data/articles.db` or the helper script in `ingestion/` to inspect.

## Tables

### `articles`

| Column            | Type        | Constraints/Notes                                  |
|-------------------|-------------|----------------------------------------------------|
| `article_id`      | TEXT        | Primary key, UUID string                           |
| `source`          | TEXT        | Publisher (e.g., Reuters)                          |
| `headline`        | TEXT        | Unique together with `publication_date` for dedupe |
| `full_text`       | TEXT        | Full article body                                  |
| `publication_date`| TEXT        | ISO 8601 timestamp (UTC)                           |
| `processed`       | INTEGER     | 0/1 flag indicating extraction status              |
| `created_at`      | TEXT        | Insert timestamp (ISO 8601)                        |
| `updated_at`      | TEXT        | Last update timestamp                              |

#### Indexes

- `idx_articles_pubdate` on (`publication_date`) to speed range queries.
- `idx_articles_source` on (`source`).

**Duplicate Detection:** before insert, query by `headline` + `publication_date`; if exists, skip or update existing row.

### `article_metadata` (optional extension)

| Column          | Type  | Notes                                        |
|-----------------|-------|----------------------------------------------|
| `article_id`    | TEXT  | FK → `articles.article_id`                   |
| `url`           | TEXT  | Original article URL                         |
| `summary`       | TEXT  | Short abstract (if available)                |
| `language`      | TEXT  | ISO language code                            |

Index on `article_id` for quick lookup. This table can be omitted when metadata is not provided.

## Data Export Contract

`ingestion/database.py` exports articles to `data/articles_export.json` with the following schema:

```json
{
  "article_id": "uuid",
  "headline": "Sample headline",
  "full_text": "Full body text…",
  "source": "Reuters",
  "publication_date": "2024-03-15T10:30:00Z",
  "processed": false
}
```

## Setup Notes

- Create the database by running `python ingestion/database.py --init`.
- Ensure the `data/` directory exists and is git-ignored for `.db` files.
- For tests, use an in-memory SQLite connection (`sqlite3.connect(':memory:')`) with the same schema migration logic.
