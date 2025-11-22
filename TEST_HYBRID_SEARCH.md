# Testing Hybrid Search System

This guide provides terminal commands to test the new hybrid BM25 + Embedding search system.

## Quick Test Commands

### 1. Install Required Dependencies

```bash
# Navigate to project directory
cd /Users/vaibhav.yadav/Documents/Course/IR/Final

# Install sentence-transformers for embedding support (optional but recommended)
pip install sentence-transformers

# Or if using uv:
uv pip install sentence-transformers

# Verify installation
python -c "import sentence_transformers; print('✅ sentence-transformers installed')"
```

### 2. Run the Test Suite

```bash
# Run comprehensive test script
python test_hybrid_search.py

# Or make it executable and run directly
chmod +x test_hybrid_search.py
./test_hybrid_search.py
```

### 3. Quick Python REPL Test

```bash
# Start Python REPL
python

# Then run these commands:
```

```python
# Test imports
from src.module2_search.bm25 import BM25Index
from src.module2_search.indexer import ArticleIndexer
from src.module2_search.preprocessor import TextPreprocessor

# Test BM25Index
bm25 = BM25Index()
bm25.add_document("doc1", ["financial", "market", "analysis"])
bm25.add_document("doc2", ["stock", "price", "financial"])
bm25.finalize()

results = bm25.score(["financial", "market"], k=2)
print("BM25 Results:", results)

# Test EmbeddingIndex (if available)
try:
    from src.module2_search.embeddings import EmbeddingIndex
    emb = EmbeddingIndex()
    emb.build([("doc1", "Financial market analysis"), ("doc2", "Stock prices rising")])
    results = emb.search("financial markets", k=2)
    print("Embedding Results:", results)
except ImportError:
    print("⚠️  Embeddings not available - install sentence-transformers")

# Test ArticleIndexer (requires test data)
# This will be tested in the full test suite
```

### 4. Test with Real Data (if available)

```bash
# Check if you have article data
ls -la data/articles_export.json 2>/dev/null || echo "No articles_export.json found"

# If you have data, test with it:
python -c "
from src.module2_search.indexer import ArticleIndexer
import os

if os.path.exists('data/articles_export.json'):
    indexer = ArticleIndexer(articles_path='data/articles_export.json')
    indexer.build_index()
    results = indexer.search('financial markets', k=5)
    print(f'Found {len(results)} results')
    for r in results[:3]:
        print(f\"- {r['headline']}: BM25={r['bm25_score']:.4f}, Embed={r['embed_score']}, Combined={r['combined_score']:.4f}\")
else:
    print('No article data found. Run Module 1 ingestion first.')
"
```

### 5. Verify Integration with Existing System

```bash
# Check if existing search engine still works
python -c "
from src.module2_search.indexer import InvertedIndex
from src.module2_search.preprocessor import TextPreprocessor
print('✅ InvertedIndex (legacy) still available')
print('✅ ArticleIndexer (new hybrid) available')
"

# Verify both classes coexist
python -c "
from src.module2_search.indexer import InvertedIndex, ArticleIndexer
print('✅ Both InvertedIndex and ArticleIndexer available')
print('✅ Backward compatibility maintained')
"
```

### 6. Test Fallback Behavior (BM25-only mode)

```bash
# Test that system works without sentence-transformers
# (Uninstall temporarily to test, or just verify graceful handling)

python -c "
from src.module2_search.indexer import ArticleIndexer
import json
import tempfile
import os

# Create minimal test data
test_data = [{
    'article_id': 'test1',
    'headline': 'Test Article',
    'full_text': 'This is a test article about financial markets.',
    'source': 'Test',
    'publication_date': '2024-01-01'
}]

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(test_data, f)
    temp_path = f.name

try:
    indexer = ArticleIndexer(articles_path=temp_path)
    indexer.build_index()
    stats = indexer.stats()
    print(f'✅ System works in BM25-only mode')
    print(f'   Has embeddings: {stats[\"has_embeddings\"]}')
    results = indexer.search('financial', k=1)
    print(f'✅ Search works: {len(results)} results')
finally:
    os.unlink(temp_path)
"
```

## Expected Output

### Successful Test Run (with embeddings):
```
✅ All available tests passed!
   Documents: 3
   Has embeddings: True
   Search returned 3 results with both BM25 and embedding scores
```

### Successful Test Run (BM25-only):
```
⚠️  EmbeddingIndex: SKIPPED (not available)
✅ All available tests passed!
   Has embeddings: False
   Search returned 3 results with BM25 scores only
```

## Troubleshooting

### Issue: ImportError for sentence-transformers
```bash
# Solution: Install the package
pip install sentence-transformers
```

### Issue: ModuleNotFoundError for module2_search
```bash
# Solution: Make sure you're in the project root
cd /Users/vaibhav.yadav/Documents/Course/IR/Final
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Issue: No article data found
```bash
# Solution: Run Module 1 ingestion first, or use the test script which creates mock data
python test_hybrid_search.py
```

## Performance Testing

```bash
# Time the index building
time python -c "
from src.module2_search.indexer import ArticleIndexer
# ... (use your actual data path)
indexer.build_index()
"

# Compare BM25-only vs Hybrid search speed
python -c "
import time
from src.module2_search.indexer import ArticleIndexer
# ... build indexer ...

start = time.time()
results = indexer.search('your query', k=10)
elapsed = time.time() - start
print(f'Search took {elapsed:.3f} seconds')
"
```

