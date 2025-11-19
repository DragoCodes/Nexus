# Entity Relationship Extractor

## Quick Start
```bash
python extraction/batch_process.py --articles data/articles_export.json --cache-dir data/cache
```

## Testing with Mock Data
```bash
pytest tests/test_extraction.py
```

## API / CLI Examples
- Process single article: `python extraction/batch_process.py --article-id <uuid>`
- Inspect cache: `python extraction/cache.py --list`

Configure `.env` with `OPENAI_API_KEY` (or OpenRouter token). To work offline, pass `--mock-responses mock_data/mock_llm_responses.json`—the parser (`extraction/parser.py`) still validates JSON against the pydantic schema before writing `data/extractions/{article_id}.json`.

## Prompt Engineering Notes
- **System Prompt:** explicitly lists entity/relationship schema, snake_case verbs, and output-only JSON guardrails.
- **Few-shot Examples:** cover acquisition, partnership, and empty extractions to bias the LLM toward concise triples.
- **Error Handling:** outputs are parsed via `parse_llm_response`, which trims whitespace, enforces entity types, and clamps confidence scores between 0 and 1.
- **Caching:** `ExtractionCache` avoids duplicate API calls; rerun with `--force` to overwrite.

