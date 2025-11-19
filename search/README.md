# BM25 Search Engine

## Quick Start
```bash
python search/indexer.py --articles data/articles_export.json
python -m flask --app search.api run --port 5000
```

## Testing with Mock Data
```bash
pytest tests/test_search.py
```

## API Examples
- `curl 'http://localhost:5000/search?q=NVIDIA%20AI&k=10'`
- `curl 'http://localhost:5000/search/health'` (readiness probe)

Tokenizer handles casings, stop words, tickers like `$AAPL`, and currency symbols. Override BM25 constants with `--k1` and `--b` flags when running `search/bm25.py`.

## BM25 Primer
We score each document using:

```
score(q, d) = Σ IDF(t) * [(f(t, d) * (k1 + 1)) / (f(t, d) + k1 * (1 - b + b * |d| / avgdl))]
```

Where:
- `f(t, d)` is the term frequency of token `t` in document `d`
- `|d|` is the document length (tokens)
- `avgdl` is the corpus average document length
- `IDF(t) = log(1 + (N - n_t + 0.5)/(n_t + 0.5))`

Defaults follow IR literature: `k1=1.5`, `b=0.75`. Adjust via CLI flags for experimentation.

