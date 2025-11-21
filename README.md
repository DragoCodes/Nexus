# Nexus - Financial Intelligence Knowledge Graph

A comprehensive system for extracting, analyzing, and visualizing financial relationships from news articles using AI-powered knowledge graph technology.

## 🚀 Quick Start

### Prerequisites

1. **Python 3.12+** (check with `python --version`)
2. **uv** - Fast Python package installer (install from [astral.sh/uv](https://astral.sh/uv))
3. **API Keys:**
   - News API key from [newsapi.org](https://newsapi.org)
   - Google Gemini API key from [ai.google.dev](https://ai.google.dev)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /Users/vaibhav.yadav/Documents/Course/IR/Final
   ```

2. **Install dependencies using uv:**
   ```bash
   # uv automatically creates and manages virtual environment
   uv sync
   ```
   
   **Note:** If you prefer pip, you can still use:
   ```bash
   pip install -r requirements.txt
   ```

4. **Download NLTK data:**
   ```bash
   python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt')"
   ```

5. **Set up environment variables:**
   
   Create a `.env` file in the project root:
   ```bash
   # .env file
   NEWS_API_KEY=your_newsapi_key_here
   GEMINI_API_KEY=your_gemini_key_here
   ```
   
   **Note:** All data is stored locally in SQLite databases. No MongoDB required!

## 📋 Running the Application

### Step 1: Data Ingestion (Module 1)

Ingest news articles from News API into MongoDB:

```bash
# Using uv (recommended)
uv run python -m src.module1_ingestion.main

# Or using python directly (if virtual env is activated)
python -m src.module1_ingestion.main
```

This will:
- Fetch financial news articles from News API
- Store them in MongoDB
- Create article corpus for search

**Expected output:** Articles stored in MongoDB collection

### Step 2: Build Search Index (Module 2)

Build the BM25 inverted index for article search:

```bash
uv run python -m src.module2_search.build_index
```

This will:
- Preprocess all articles
- Build inverted index
- Save index to `data/index/inverted_index.pkl`

**Expected output:** Index file created at `data/index/inverted_index.pkl`

### Step 3: Extract Relationships (Module 3)

Extract entities and relationships using Google Gemini:

```bash
uv run python -m src.module3_extraction.main
```

This will:
- Process articles through LLM
- Extract entities and relationships
- Cache results to avoid redundant API calls
- Save extraction results to JSON

**Expected output:** Extraction results JSON file

**Note:** This step uses the Gemini API and may take time depending on the number of articles. The free tier has rate limits (15 requests/minute).

### Step 4: Build Knowledge Graph (Module 4)

Build the knowledge graph from extracted relationships:

```bash
uv run python -m src.module4_graph.main
```

This will:
- Create SQLite database for graph storage
- Build NetworkX graph from relationships
- Compute PageRank and detect communities
- Save analytics results

**Expected output:** 
- Graph database at `data/nexus_graph.db`
- Analytics exports in `data/exports/`

### Step 5: Run Frontend (Module 6)

Launch the Streamlit web interface:

```bash
# Option 1: Using uv
uv run streamlit run frontend/app.py

# Option 2: Using the run script
uv run python run_frontend.py

# Option 3: Direct Streamlit command (if venv activated)
streamlit run frontend/app.py
```

The frontend will open in your browser at `http://localhost:8501`

## 🎯 Complete Workflow (One-Time Setup)

For a complete setup from scratch, run these commands in order:

```bash
# 1. Install dependencies (using uv)
uv sync

# Or using pip:
# pip install -r requirements.txt

# 2. Set up environment variables (.env file)
# (Edit .env with your API keys)

# 3. Ingest articles
uv run python -m src.module1_ingestion.main

# 4. Build search index
uv run python -m src.module2_search.build_index

# 5. Extract relationships (this may take a while)
uv run python -m src.module3_extraction.main

# 6. Build knowledge graph
uv run python -m src.module4_graph.main

# 7. Run frontend
uv run streamlit run frontend/app.py
```

## 📱 Using the Frontend

Once the frontend is running, you can:

1. **Home/Dashboard** - View overview statistics, top entities, and recent activity
2. **📰 News Search** - Search articles using BM25 ranking
3. **🕸️ Knowledge Graph** - Interactive graph visualization with filters
4. **📊 Analytics** - PageRank analysis and community detection
5. **📈 Trends** - Time-series analysis of relationships

## 🔧 Troubleshooting

### Common Issues

1. **"Failed to initialize application"**
   - Check that `data/articles.db` exists (run Module 1 first)
   - Ensure you have write permissions in the `data/` directory
   - Verify index file exists: `data/index/inverted_index.pkl`

2. **"Index file not found"**
   - Run Module 2 to build the index: `uv run python -m src.module2_search.build_index`

3. **"Graph database not found"**
   - Run Module 4 to build the graph: `uv run python -m src.module4_graph.main`

4. **"Module 4 not available"**
   - Ensure all dependencies are installed: `uv sync` (or `pip install -r requirements.txt`)
   - Check that `src/module4_graph/` exists

5. **API Rate Limits**
   - News API: 100 requests/day (free tier)
   - Gemini API: 15 requests/minute, 1500 requests/day (free tier)
   - Add delays between API calls if needed

### File Structure

```
Final/
├── config/              # Configuration files
├── data/
│   ├── cache/          # Extraction cache
│   ├── index/          # Search index
│   ├── exports/        # Analytics exports
│   └── nexus_graph.db  # Graph database
├── frontend/
│   ├── app.py          # Main Streamlit app
│   ├── pages/          # Streamlit pages
│   └── components/     # Reusable components
├── src/
│   ├── module1_ingestion/
│   ├── module2_search/
│   ├── module3_extraction/
│   ├── module4_graph/
│   ├── module5_api/
│   └── utils/
├── .env                # Environment variables (create this)
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 📊 Data Flow

```
News API → MongoDB → Search Index (BM25)
                ↓
         LLM Extraction → Relationships JSON
                ↓
         Graph Builder → SQLite DB → NetworkX Graph
                ↓
         Frontend (Streamlit) → Visualization
```

## 🔑 Environment Variables

Required environment variables (set in `.env` file):

- `NEWS_API_KEY` - Your News API key
- `GEMINI_API_KEY` - Your Google Gemini API key

**Note:** All data is stored locally in SQLite databases:
- Articles: `data/articles.db`
- Graph: `data/nexus_graph.db`

## 📝 Notes

- The first run will take longer as it builds indexes and processes data
- Subsequent runs will use cached data where available
- Graph visualization works best with 50-500 nodes
- All data is stored locally - no external database server needed!

## 🆘 Getting Help

If you encounter issues:

1. Check that all prerequisites are installed
2. Verify `.env` file has correct values
3. Ensure MongoDB is accessible
4. Check logs for specific error messages
5. Verify all modules completed successfully before running frontend

