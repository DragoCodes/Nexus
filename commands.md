# 📝 Nexus Command Reference

Quick reference for all available commands.

---

## 🚀 Setup & Installation

```bash
# Initial setup (run once)
chmod +x setup.sh
./setup.sh

# Quick start with mock data (no API keys needed)
chmod +x quickstart.sh
./quickstart.sh

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt
```

---

## 🔧 Module Commands

### Member 1: Data Ingestion

```bash
# Generate mock articles (50 articles)
python -m ingestion.mock_generator

# Fetch real articles from NewsAPI (requires API key)
python -m ingestion.news_fetcher

# Test database operations
python -m ingestion.database

# Export articles to JSON
python -c "
from ingestion.database import ArticleDatabase
db = ArticleDatabase()
db.export_to_json('data/articles_export.json')
"
```

### Member 2: Search Engine

```bash
# Build search index from database
python -m search.indexer

# Test preprocessor
python -m search.preprocessor

# Test BM25 implementation
python -m search.bm25

# Run search API server (standalone)
python -m search.api

# Interactive search
python -c "
from search.indexer import SearchIndex
index = SearchIndex()
index.build_index_from_json('mock_data/sample_articles.json')
# Then search interactively
"
```

### Member 3: Information Extraction

```bash
# Extract relationships (mock mode - no API key)
python -m extraction.batch_process --mock

# Extract relationships (real LLM)
python -m extraction.batch_process

# Process specific number of articles
python -c "
from extraction.batch_process import BatchExtractor
extractor = BatchExtractor(use_mock=True)
results = extractor.process_from_json('mock_data/sample_articles.json', limit=10)
"

# Test LLM client
python -m extraction.llm_client

# Test prompt templates
python -m extraction.prompts

# View cache statistics
python -c "
from extraction.cache import ExtractionCache
cache = ExtractionCache()
print(cache.get_statistics())
"

# Export all cached extractions
python -c "
from extraction.cache import ExtractionCache
cache = ExtractionCache()
cache.export_all('data/all_extractions.json')
"
```

### Member 4: Knowledge Graph

```bash
# Build graph from cached extractions
python -m graph.builder

# Test analytics
python -m graph.analytics

# Run graph API server (standalone)
python -m graph.api

# Calculate PageRank
python -c "
from graph.builder import KnowledgeGraphBuilder
from graph.analytics import GraphAnalytics
builder = KnowledgeGraphBuilder()
builder.load_from_cache()
analytics = GraphAnalytics(builder.graph)
results = analytics.calculate_pagerank(top_k=10)
for r in results: print(f\"{r['entity']}: {r['score']}\")
"

# Detect communities
python -c "
from graph.builder import KnowledgeGraphBuilder
from graph.analytics import GraphAnalytics
builder = KnowledgeGraphBuilder()
builder.load_from_cache()
analytics = GraphAnalytics(builder.graph)
communities = analytics.detect_communities()
print(f'Found {len(communities)} communities')
"

# Export graph to GEXF (for Gephi)
python -c "
from graph.builder import KnowledgeGraphBuilder
builder = KnowledgeGraphBuilder()
builder.load_from_cache()
builder.save_graph('data/knowledge_graph.gexf')
"
```

---

## 🌐 Running the Application

### Start API Server
```bash
# Full integrated API
python main.py

# Access at http://localhost:5000
# API docs at http://localhost:5000/
```

### Start Streamlit UI
```bash
# Interactive web interface
streamlit run streamlit_demo.py

# Access at http://localhost:8501
```

### Run Both (in separate terminals)
```bash
# Terminal 1: API
python main.py

# Terminal 2: UI
streamlit run streamlit_demo.py
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run integration tests
pytest tests/test_integration.py -v -s

# Run specific test
pytest tests/test_integration.py::TestIntegration::test_1_ingestion -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

---

## 🔍 API Examples

### Using curl

```bash
# Search articles
curl "http://localhost:5000/api/search/search?q=NVIDIA&k=10"

# Get article by ID
curl "http://localhost:5000/api/search/article/ARTICLE_ID"

# Search index stats
curl "http://localhost:5000/api/search/stats"

# Get entity relationships
curl "http://localhost:5000/api/graph/entity/NVIDIA"

# Calculate PageRank
curl -X POST "http://localhost:5000/api/graph/analytics/pagerank?top_k=20"

# Detect communities
curl -X POST "http://localhost:5000/api/graph/analytics/communities?min_size=3"

# Analyze trends
curl "http://localhost:5000/api/graph/analytics/trends?granularity=week"

# Find shortest path
curl "http://localhost:5000/api/graph/path/NVIDIA/TSMC"

# Graph statistics
curl "http://localhost:5000/api/graph/stats"
```

### Using Python requests

```python
import requests

# Search
response = requests.get(
    "http://localhost:5000/api/search/search",
    params={"q": "artificial intelligence", "k": 5}
)
print(response.json())

# Entity lookup
response = requests.get(
    "http://localhost:5000/api/graph/entity/Apple"
)
print(response.json())

# PageRank
response = requests.post(
    "http://localhost:5000/api/graph/analytics/pagerank",
    params={"top_k": 10}
)
print(response.json())
```

---

## 📊 Data Management

```bash
# View database statistics
python -c "
from ingestion.database import ArticleDatabase
db = ArticleDatabase()
print(db.get_statistics())
"

# Count cached extractions
ls -1 data/extractions/*/*.json | wc -l

# View graph statistics
python -c "
from graph.builder import KnowledgeGraphBuilder
builder = KnowledgeGraphBuilder()
builder.load_from_cache()
import json
print(json.dumps(builder.get_statistics(), indent=2))
"

# Clear cache
rm -rf data/extractions/*

# Reset database (careful!)
rm data/articles.db

# Backup data
tar -czf nexus_backup_$(date +%Y%m%d).tar.gz data/
```

---

## 🔧 Development Commands

```bash
# Format code with black
black .

# Lint with flake8
flake8 . --max-line-length=100

# Type checking with mypy
mypy ingestion/ search/ extraction/ graph/

# Generate requirements
pip freeze > requirements.txt

# Create new branch for feature
git checkout -b feature/new-feature

# View logs
tail -f nohup.out  # if running in background
```

---

## 🐛 Debugging

```bash
# Check if modules are importable
python -c "import ingestion; import search; import extraction; import graph; print('✅ All modules OK')"

# Test NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Check API server
curl http://localhost:5000/health

# Verbose extraction (shows each step)
python -c "
from extraction.batch_process import BatchExtractor
extractor = BatchExtractor(use_mock=True)
results = extractor.process_from_json('mock_data/sample_articles.json', limit=1)
print('Processed:', len(results))
"

# Test search with debug output
python -c "
from search.indexer import SearchIndex
index = SearchIndex()
index.build_index_from_json('mock_data/sample_articles.json')
results = index.search('test query', k=5)
print(f'Found {len(results)} results')
for r in results:
    print(f'{r[\"headline\"][:50]}... (score: {r[\"bm25_score\"]})')
"
```

---

## 📦 Deployment

```bash
# Production mode (disable debug)
# Edit main.py: app.run(debug=False, host='0.0.0.0', port=5000)
python main.py

# Run in background
nohup python main.py > nohup.out 2>&1 &

# Stop background process
ps aux | grep main.py
kill <PID>

# Using gunicorn (production WSGI server)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app

# Docker (if Dockerfile exists)
docker build -t nexus .
docker run -p 5000:5000 nexus
```

---

## 💡 Useful One-Liners

```bash
# Complete pipeline in one command
python -m ingestion.mock_generator && \
python -m search.indexer && \
python -m extraction.batch_process --mock && \
python main.py

# Count entities in graph
python -c "from graph.builder import KnowledgeGraphBuilder; b=KnowledgeGraphBuilder(); b.load_from_cache(); print(b.graph.number_of_nodes())"

# Find most connected entity
python -c "from graph.builder import KnowledgeGraphBuilder; b=KnowledgeGraphBuilder(); b.load_from_cache(); print(max(b.graph.nodes(), key=lambda x: b.graph.degree(x)))"

# Export all data
python -m ingestion.database && \
python -c "from extraction.cache import ExtractionCache; ExtractionCache().export_all()" && \
python -c "from graph.builder import KnowledgeGraphBuilder; b=KnowledgeGraphBuilder(); b.load_from_cache(); b.save_graph()"
```

---

## 📚 Documentation Generation

```bash
# Generate API docs with Swagger (if configured)
# Install: pip install flasgger
# Add to main.py: from flasgger import Swagger; Swagger(app)

# Generate module documentation
pydoc -w ingestion search extraction graph

# Create architecture diagram
# Use: https://app.diagrams.net/
# Or: pip install diagrams && python create_diagram.py
```

---

## 🆘 Emergency Commands

```bash
# If everything breaks, reset:
rm -rf data/ mock_data/
rm -rf venv/
./setup.sh

# If port is already in use:
lsof -ti:5000 | xargs kill -9

# If imports fail:
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# If NLTK fails:
python -c "import nltk; nltk.download('all')"
```

---

For more information, see README.md or check individual module documentation.