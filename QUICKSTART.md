# Quick Start Guide - Nexus

## 🚀 Running the Complete Application

### Prerequisites Checklist

- [ ] Python 3.12+ installed
- [ ] MongoDB running (local or Atlas)
- [ ] News API key
- [ ] Google Gemini API key

### Step-by-Step Setup

#### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
# pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
```

#### 2. Configure Environment

Create a `.env` file in the project root:

```bash
NEWS_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DB_NAME=nexus_db
MONGODB_COLLECTION_NAME=articles
```

#### 3. Run Modules in Order

```bash
# Module 1: Ingest articles
uv run python -m src.module1_ingestion.main
# Or: python -m src.module1_ingestion.main

# Module 2: Build search index
uv run python -m src.module2_search.build_index

# Module 3: Extract relationships (takes time!)
uv run python -m src.module3_extraction.main

# Module 4: Build knowledge graph
uv run python -m src.module4_graph.main

# Module 6: Run frontend
uv run streamlit run frontend/app.py
# Or: streamlit run frontend/app.py
```

### 🎯 Quick Run (If Already Set Up)

If you've already run modules 1-4, just start the frontend:

```bash
streamlit run frontend/app.py
```

Or use the helper script:

```bash
python run_frontend.py
```

The app will open at `http://localhost:8501`

### 📋 What Each Module Does

1. **Module 1** - Fetches news articles from News API → MongoDB
2. **Module 2** - Builds BM25 search index from articles
3. **Module 3** - Uses Gemini AI to extract entities/relationships
4. **Module 4** - Builds knowledge graph (NetworkX + SQLite)
5. **Module 6** - Streamlit web interface for visualization

### ⚠️ Important Notes

- **First run takes time** - Modules 1-4 need to complete before frontend works
- **API rate limits** - Free tiers have limits (check API docs)
- **Data persistence** - Index and graph are saved, so you don't need to rebuild every time
- **MongoDB required** - Frontend needs MongoDB connection to work

### 🔍 Verify Setup

Check these files exist before running frontend:

- ✅ `data/index/inverted_index.pkl` (from Module 2)
- ✅ `data/nexus_graph.db` (from Module 4)
- ✅ MongoDB has articles (from Module 1)

### 🐛 Troubleshooting

**Frontend won't start:**
- Check MongoDB connection in `.env`
- Verify index file exists: `ls data/index/inverted_index.pkl`
- Verify graph DB exists: `ls data/nexus_graph.db`

**"Module not found" errors:**
- Make sure you're in project root directory
- If using uv: `uv run python -m src.module1_ingestion.main` (uv handles paths automatically)
- Or set PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"` (Linux/Mac)
- Or: `set PYTHONPATH=%PYTHONPATH%;%CD%\src` (Windows)

**Empty graph:**
- Run Module 3 to extract relationships
- Run Module 4 to build graph
- Check `data/exports/` for analytics files

