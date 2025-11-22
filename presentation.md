# Nexus: Financial Intelligence Knowledge Graph

---

# Title & Hook

## Nexus: Financial Intelligence Knowledge Graph

**Transform financial news articles into an interactive knowledge graph that reveals hidden relationships between companies, people, and organizations using AI-powered entity extraction.**

---

# The Architecture (High Level)

## Tech Stack & Data Flow

**Built with:**
- **Python 3.12** - Core language
- **Streamlit** - Web frontend framework
- **NetworkX** - In-memory graph operations and analytics
- **SQLite** - Persistent graph storage
- **Google Gemini API** - LLM for entity/relationship extraction
- **PyVis** - Interactive graph visualization
- **BM25** - Information retrieval ranking algorithm

**Architecture Flow:**
```
News API → SQLite (articles.db) → BM25 Search Index
                ↓
         Gemini LLM Extraction → Relationships JSON
                ↓
         Graph Builder → SQLite (nexus_graph.db) → NetworkX Graph
                ↓
         Streamlit Frontend → Interactive Visualization
```

**Module Structure:**
- **Module 1**: News ingestion and storage
- **Module 2**: BM25 inverted index construction
- **Module 3**: LLM-powered relationship extraction
- **Module 4**: Knowledge graph construction and analytics
- **Module 5**: API layer for frontend integration

---

# Feature Deep Dive 1: LLM-Powered Extraction with Robust Error Handling

## How It Works

The `GeminiClient` orchestrates AI-powered relationship extraction from financial news articles with enterprise-grade reliability.

**Key Features:**
- **Rate Limiting**: Enforces 4.5-second delays between API calls to respect Gemini's 15 req/min limit
- **Retry Logic**: Exponential backoff for transient failures, specific handling for 429 (rate limit) and 5xx errors
- **Response Parsing**: Handles multiple response formats, blocked content, and truncated responses
- **Safety Filter Handling**: Gracefully handles content blocked by Gemini's safety filters

**Critical Code Snippet:**

```python
def extract(self, prompt_text: str) -> Optional[str]:
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Rate limiting: wait 4-5 seconds between calls
            time_since_last_call = time.time() - self.last_call_time
            if time_since_last_call < 4.5:
                wait_time = 4.5 - time_since_last_call
                time.sleep(wait_time)
            
            response = self.model.generate_content(prompt_text)
            
            # Handle blocked/truncated responses
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = candidate.finish_reason
                if finish_reason == 3:  # SAFETY - content blocked
                    return None
            
            return response.text
            
        except Exception as e:
            if error_code == 429:  # Rate limit
                wait_time = 60
                time.sleep(wait_time)
                continue
            # Exponential backoff for other errors
            wait_time = 2 ** attempt
            time.sleep(wait_time)
```

**Why It Matters:** Ensures reliable extraction even with API constraints, handling edge cases that would otherwise crash the pipeline.

---

# Feature Deep Dive 2: BM25 Search Engine Implementation

## How It Works

The search engine implements the BM25 ranking algorithm for relevance-based article retrieval, combining term frequency, inverse document frequency, and document length normalization.

**Key Components:**
- **BM25Scorer**: Calculates relevance scores using the BM25 formula
- **Inverted Index**: Efficient term-to-document mapping
- **Text Preprocessing**: Tokenization, stopword removal, normalization

**BM25 Formula Implementation:**

```python
def calculate_bm25_for_document(self, query_terms, doc_id):
    score = 0.0
    doc_length = self.inverted_index.doc_lengths.get(doc_id, 0)
    avg_doc_length = self.inverted_index.avg_doc_length
    
    for term in query_terms:
        idf = self.calculate_idf(term)  # log((N - n(term) + 0.5) / (n(term) + 0.5) + 1)
        term_freq = self._get_term_frequency(term, doc_id)
        
        # BM25 component: IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (dl / avgdl)))
        numerator = term_freq * (self.k1 + 1)
        denominator = term_freq + self.k1 * (
            1 - self.b + self.b * (doc_length / avg_doc_length)
        )
        score += idf * (numerator / denominator)
    
    return score
```

**Parameters:**
- `k1 = 1.5`: Controls term frequency saturation
- `b = 0.75`: Controls document length normalization

**Why It Matters:** Provides state-of-the-art search relevance ranking, outperforming simple keyword matching by considering document length and term rarity.

---

# Feature Deep Dive 3: Dual-Storage Graph Architecture

## How It Works

The `GraphManager` maintains synchronization between SQLite (persistent storage) and NetworkX (in-memory graph), enabling both durability and fast graph analytics.

**Architecture:**
- **SQLite Database**: Stores entities and relationships with metadata (mention counts, publication dates, frequencies)
- **NetworkX Graph**: In-memory directed graph for fast traversal and analytics (PageRank, community detection)
- **Bidirectional Sync**: Changes to either storage layer propagate to the other

**Critical Code Snippet:**

```python
def add_or_update_relationship(self, entity1, entity2, relationship_type, 
                               article_id, publication_date, ...):
    # 1. Ensure entities exist in database
    self.add_or_update_entity(entity1, entity1_type)
    self.add_or_update_entity(entity2, entity2_type)
    
    # 2. Check if relationship exists in SQLite
    cursor.execute("""
        SELECT id, source_article_ids, frequency
        FROM relationships
        WHERE entity1 = ? AND entity2 = ? AND relationship_type = ?
    """, (entity1, entity2, relationship_type))
    
    if row:
        # Update: increment frequency, append article_id
        existing_article_ids = json.loads(row['source_article_ids'])
        if article_id not in existing_article_ids:
            existing_article_ids.append(article_id)
        cursor.execute("UPDATE relationships SET frequency = ?, ...")
    else:
        # Insert: create new relationship
        cursor.execute("INSERT INTO relationships ...")
    
    # 3. Sync to NetworkX graph
    self.graph.add_edge(
        entity1, entity2,
        relationship_type=relationship_type,
        source_article_ids=article_ids,
        frequency=frequency
    )
```

**Why It Matters:** Combines the persistence of SQLite with the analytical power of NetworkX, enabling complex graph queries while maintaining data integrity and recovery capabilities.

---

# Frontend Implementation

## Streamlit UI Architecture

The frontend uses Streamlit's component-based architecture with custom CSS styling and PyVis for interactive graph visualization.

**Styling System:**
- **Custom CSS**: Embedded in `app.py` for consistent branding
- **Metric Cards**: Custom styled components with shadows and borders
- **Color Schemes**: Entity types mapped to distinct colors (Company=Blue, Person=Green, Product=Orange)
- **Responsive Layout**: Wide layout with sidebar navigation

**Main Page Structure:**

```python
# Custom CSS for branding
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)
```

**User Experience:**
- **Home Dashboard**: Network statistics, top entities by PageRank, entity type distributions
- **News Search**: BM25-powered article search with relevance scores
- **Knowledge Graph**: Interactive PyVis visualization with filters (entity type, relationship type, minimum connections)
- **Analytics**: PageRank rankings and community detection results
- **Trends**: Time-series analysis of relationship patterns

**Graph Visualization Features:**
- **Dynamic Node Sizing**: Based on PageRank, degree, or mention count
- **Physics Simulation**: Force-directed layout with configurable physics
- **Interactive Filters**: Real-time filtering by entity/relationship types
- **Ego Network Focus**: Zoom into specific entity neighborhoods

---

# Conclusion & Next Steps

## Current Capabilities

**What Nexus Delivers:**
- ✅ Automated extraction of financial relationships from news articles
- ✅ BM25-powered semantic search across article corpus
- ✅ Interactive knowledge graph visualization with filtering
- ✅ PageRank-based entity influence analysis
- ✅ Community detection for relationship clustering
- ✅ Persistent graph storage with SQLite

**Performance Characteristics:**
- Handles 100-500 node graphs efficiently
- Processes articles with rate-limited LLM calls (15 req/min)
- Real-time graph filtering and visualization updates

## Potential Improvements

**1. Incremental Graph Updates**
- Currently rebuilds entire graph from scratch
- **Enhancement**: Implement delta updates to process only new articles, reducing processing time and API costs

**2. Advanced Relationship Validation**
- LLM extraction may produce inconsistent entity names (e.g., "Apple Inc." vs "Apple")
- **Enhancement**: Add entity disambiguation layer using fuzzy matching or named entity recognition to merge aliases

**3. Real-Time Data Pipeline**
- Current workflow is batch-oriented (run modules sequentially)
- **Enhancement**: Implement event-driven architecture with message queue (Redis/RabbitMQ) to process articles as they arrive, enabling live graph updates

**Additional Opportunities:**
- Add sentiment analysis to relationships (positive/negative partnerships)
- Implement graph-based recommendation engine ("entities similar to X")
- Export graph data to Neo4j for production-scale deployments
- Add user authentication and saved search/bookmark features

---

