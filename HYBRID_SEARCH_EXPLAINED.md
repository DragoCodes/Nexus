# BM25 + Embedding Hybrid Search: Technical Explanation

## Table of Contents
1. [Overview](#overview)
2. [Traditional BM25 Algorithm](#traditional-bm25-algorithm)
3. [Embedding-Based Semantic Search](#embedding-based-semantic-search)
4. [Hybrid Search Architecture](#hybrid-search-architecture)
5. [Key Differences](#key-differences)
6. [Advantages of Hybrid Approach](#advantages-of-hybrid-approach)
7. [Implementation Details](#implementation-details)
8. [Score Fusion Strategy](#score-fusion-strategy)

---

## Overview

The hybrid search system combines **lexical search (BM25)** with **semantic search (embeddings)** to leverage the strengths of both approaches. This provides better search results by matching both exact keywords and semantic meaning.

### Quick Comparison

| Aspect | BM25 Only | Hybrid BM25 + Embeddings |
|--------|-----------|--------------------------|
| **Matching Type** | Lexical (exact word matching) | Lexical + Semantic |
| **Query Understanding** | Keyword-based | Keyword + Meaning-based |
| **Synonym Handling** | Poor | Good |
| **Exact Match Preference** | High | Balanced |
| **Semantic Similarity** | None | High |

---

## Traditional BM25 Algorithm

### How BM25 Works

BM25 (Best Matching 25) is a **probabilistic ranking function** that scores documents based on:

1. **Term Frequency (TF)**: How often query terms appear in a document
2. **Inverse Document Frequency (IDF)**: How rare/common a term is across all documents
3. **Document Length Normalization**: Penalizes very long documents

### BM25 Formula

```
BM25(D, Q) = Σ IDF(qi) × (f(qi, D) × (k1 + 1)) / (f(qi, D) + k1 × (1 - b + b × (|D| / avgdl)))
```

Where:
- `D` = Document
- `Q` = Query
- `qi` = Each query term
- `f(qi, D)` = Term frequency of qi in document D
- `|D|` = Document length (number of tokens)
- `avgdl` = Average document length
- `k1` = 1.5 (tuning parameter for term frequency saturation)
- `b` = 0.75 (tuning parameter for length normalization)
- `IDF(qi)` = log((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)
  - `N` = Total number of documents
  - `n(qi)` = Number of documents containing term qi

### BM25 Characteristics

**Strengths:**
- ✅ Excellent for exact keyword matching
- ✅ Fast and efficient (uses inverted index)
- ✅ Handles typos well (if preprocessing normalizes them)
- ✅ No training required
- ✅ Interpretable scores

**Limitations:**
- ❌ Cannot handle synonyms ("car" vs "automobile")
- ❌ Cannot understand semantic meaning
- ❌ Requires exact word matches (after preprocessing)
- ❌ Misses conceptually related documents without shared terms

### Example: BM25 Search

**Query:** "financial markets"

**Document 1:** "The financial markets showed strong performance today."
- Contains both "financial" and "markets" → **High BM25 score**

**Document 2:** "Stock exchanges experienced significant gains."
- Contains neither word → **Zero BM25 score** (even though semantically relevant)

---

## Embedding-Based Semantic Search

### How Embeddings Work

Embeddings convert text into **dense vector representations** in a high-dimensional space (typically 768 dimensions for `all-mpnet-base-v2`). Semantically similar texts are positioned close together in this space.

### Embedding Process

1. **Document Encoding**: Each document is converted to a vector using a pre-trained transformer model
2. **Query Encoding**: The query is converted to the same vector space
3. **Similarity Calculation**: Cosine similarity between query and document vectors
4. **Ranking**: Documents ranked by similarity scores

### Cosine Similarity Formula

```
cosine_similarity(q, d) = (q · d) / (||q|| × ||d||)
```

Where:
- `q` = Query vector
- `d` = Document vector
- `·` = Dot product
- `||v||` = L2 norm (magnitude) of vector v

For normalized vectors (L2-normalized), this simplifies to:
```
cosine_similarity(q, d) = q · d  (just dot product)
```

### Embedding Characteristics

**Strengths:**
- ✅ Understands semantic meaning
- ✅ Handles synonyms automatically
- ✅ Captures conceptual relationships
- ✅ Works with paraphrased queries
- ✅ Language model knowledge (trained on vast text)

**Limitations:**
- ❌ Computationally expensive (requires neural network inference)
- ❌ May miss exact keyword matches (less precise)
- ❌ Requires pre-trained model (storage and memory)
- ❌ Less interpretable scores

### Example: Embedding Search

**Query:** "financial markets"

**Document 1:** "The financial markets showed strong performance today."
- High semantic similarity → **High embedding score**

**Document 2:** "Stock exchanges experienced significant gains."
- High semantic similarity (markets ≈ exchanges) → **High embedding score** ✅

**Document 3:** "Cooking recipes for dinner."
- Low semantic similarity → **Low embedding score**

---

## Hybrid Search Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Query                            │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   BM25 Search   │    │ Embedding Search │
│                 │    │                  │
│ - Preprocess    │    │ - Encode Query   │
│ - Tokenize      │    │ - Cosine Similar │
│ - Score Docs    │    │ - Rank Results   │
└────────┬────────┘    └────────┬─────────┘
         │                       │
         │ BM25 Scores           │ Embedding Scores
         │ (lexical)             │ (semantic)
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Score Normalization │
         │                       │
         │ - BM25 → [0, 1]       │
         │ - Embeddings → [0, 1] │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Score Fusion        │
         │                       │
         │ combined = α × embed  │
         │        + (1-α) × bm25 │
         │                       │
         │ α = 0.6 (default)     │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Final Ranking       │
         │                       │
         │ - Sort by combined    │
         │ - Return top-k        │
         └───────────────────────┘
```

### Step-by-Step Process

#### Step 1: Parallel Search Execution

Both BM25 and embedding searches run **independently** and in parallel:

```python
# BM25 search
tokens = preprocessor.preprocess_query(query)
bm25_ranked = bm25_index.score(tokens, k=k * 5)  # Get top 5k candidates
bm25_scores = {doc_id: score for doc_id, score in bm25_ranked}

# Embedding search
embeds = embedding_index.search(query, k=k * 5)  # Get top 5k candidates
embed_scores = {doc_id: score for doc_id, score in embeds}
```

**Why `k * 5`?** We fetch more candidates (5×) to ensure we have enough overlap between both methods before fusion.

#### Step 2: Score Normalization

Scores from BM25 and embeddings are on **different scales**:

- **BM25 scores**: Typically range from 0 to ~20+ (unbounded)
- **Embedding scores**: Cosine similarity in [-1, 1] (if normalized)

We normalize both to **[0, 1]** for fair combination:

```python
# BM25 normalization: min-max scaling
bm25_norm = normalize_scores(bm25_scores)  # Maps to [0, 1]

# Embedding normalization: cosine to [0, 1]
if scores in [-1, 1]:
    embed_norm = {(score + 1) / 2 for score in embed_scores}  # Maps [-1,1] → [0,1]
else:
    embed_norm = normalize_scores(embed_scores)  # Min-max scaling
```

#### Step 3: Score Fusion

The **weighted combination** of normalized scores:

```python
alpha = 0.6  # Weight for embeddings (60%)
combined_score = alpha * embed_norm + (1 - alpha) * bm25_norm
```

**Default `alpha = 0.6`** means:
- 60% weight on semantic similarity (embeddings)
- 40% weight on lexical matching (BM25)

#### Step 4: Final Ranking

Documents are ranked by `combined_score` and top-k results are returned.

---

## Key Differences

### 1. Matching Strategy

| Aspect | BM25 Only | Hybrid |
|--------|-----------|--------|
| **Matching** | Exact word matching | Word + semantic matching |
| **Query "car"** | Only finds "car" | Finds "car", "automobile", "vehicle" |
| **Query "financial crisis"** | Only exact phrase | Also finds "economic downturn", "market crash" |

### 2. Score Calculation

**BM25 Only:**
```python
score = BM25(query_terms, document)
# Returns: single score based on term frequencies
```

**Hybrid:**
```python
bm25_score = BM25(query_terms, document)
embed_score = cosine_similarity(query_vector, doc_vector)
combined_score = 0.6 * embed_score + 0.4 * bm25_score
# Returns: three scores (bm25, embed, combined)
```

### 3. Index Structure

**BM25 Only:**
- Inverted index: `{term: [(doc_id, term_freq), ...]}`
- Document lengths: `{doc_id: length}`
- Vocabulary: Set of all terms

**Hybrid:**
- BM25 index (same as above)
- **Plus**: Embedding matrix `(N, 768)` where N = number of documents
- **Plus**: Document ID mappings

### 4. Query Processing

**BM25 Only:**
```python
query → preprocess → tokenize → BM25 scoring
```

**Hybrid:**
```python
query → {
    preprocess → tokenize → BM25 scoring,
    encode → embedding vector → cosine similarity
} → combine scores
```

### 5. Handling Edge Cases

**BM25 Only:**
- Query with no matching terms → Returns empty results
- Synonym queries → Misses relevant documents

**Hybrid:**
- Query with no matching terms → Still finds semantically similar documents via embeddings
- Synonym queries → Finds documents via embeddings even if BM25 misses them

---

## Advantages of Hybrid Approach

### 1. **Best of Both Worlds**

- **BM25**: Precise keyword matching, fast, interpretable
- **Embeddings**: Semantic understanding, synonym handling, conceptual matching

### 2. **Improved Recall**

Documents that would be missed by either method alone are now found:

```
Query: "stock market crash"

BM25 finds: Documents with exact words "stock", "market", "crash"
Embeddings find: Documents about "equity decline", "market downturn", "financial crisis"
Hybrid finds: ALL of the above ✅
```

### 3. **Better Precision**

The combination helps filter out false positives:

```
Query: "Apple"

BM25 might find: "Apple Inc." (company) + "apple fruit" (wrong!)
Embeddings might find: "Apple Inc." + "iPhone" + "Tim Cook" (all correct)
Hybrid: Combines both signals → Better ranking ✅
```

### 4. **Robustness**

- If embeddings fail → Falls back to BM25
- If BM25 misses → Embeddings catch it
- If both agree → High confidence result

### 5. **Configurable Balance**

The `alpha` parameter allows tuning:

- `alpha = 0.0` → Pure BM25 (lexical only)
- `alpha = 0.5` → Equal weight
- `alpha = 0.6` → Default (slight preference for semantics)
- `alpha = 1.0` → Pure embeddings (semantic only)

---

## Implementation Details

### Building the Hybrid Index

```python
# Initialize both indexes
bm25_index = BM25Index(k1=1.5, b=0.75)
embedding_index = EmbeddingIndex(model_name="all-mpnet-base-v2")

# Build BM25 index
for article in articles:
    tokens = preprocessor.preprocess(article.text)
    bm25_index.add_document(article.id, tokens)
bm25_index.finalize()

# Build embedding index
docs = [(article.id, article.text) for article in articles]
embedding_index.build(docs)
```

### Search Execution

```python
def search(query: str, k: int = 10):
    # 1. BM25 search
    tokens = preprocessor.preprocess_query(query)
    bm25_results = bm25_index.score(tokens, k=k * 5)
    bm25_scores = {doc_id: score for doc_id, score in bm25_results}
    
    # 2. Embedding search
    embed_results = embedding_index.search(query, k=k * 5)
    embed_scores = {doc_id: score for doc_id, score in embed_results}
    
    # 3. Normalize scores
    bm25_norm = normalize_scores(bm25_scores)  # [0, 1]
    embed_norm = normalize_cosine(embed_scores)  # [-1, 1] → [0, 1]
    
    # 4. Combine
    all_doc_ids = set(bm25_scores.keys()) | set(embed_scores.keys())
    combined_scores = {}
    for doc_id in all_doc_ids:
        b = bm25_norm.get(doc_id, 0.0)
        e = embed_norm.get(doc_id, 0.0)
        combined_scores[doc_id] = alpha * e + (1 - alpha) * b
    
    # 5. Rank and return top-k
    ranked = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:k]
```

### Result Format

Each result includes all three scores for transparency:

```python
{
    "article_id": "doc123",
    "headline": "Financial Markets Show Growth",
    "bm25_score": 1.810725,      # Raw BM25 score
    "embed_score": 0.64555,       # Raw embedding score (cosine)
    "combined_score": 0.893665,   # Final fused score
    "snippet": "..."
}
```

---

## Score Fusion Strategy

### Why Normalize?

Scores from BM25 and embeddings are **incomparable** without normalization:

- BM25: `score = 15.3` (what does this mean?)
- Embeddings: `score = 0.75` (cosine similarity)

After normalization:
- BM25: `normalized = 0.85` (85th percentile)
- Embeddings: `normalized = 0.75` (75th percentile)
- Now comparable! ✅

### Normalization Methods

#### BM25 Normalization (Min-Max Scaling)

```python
def normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    mx = max(scores.values())
    mn = min(scores.values())
    if mx == mn:
        return {k: 0.0 for k in scores}  # All equal → zeros
    denom = mx - mn
    return {k: (v - mn) / denom for k, v in scores.items()}
```

Maps scores to **[0, 1]** where:
- `0` = Lowest score in the result set
- `1` = Highest score in the result set

#### Embedding Normalization (Cosine to [0,1])

```python
# If embeddings are L2-normalized, cosine ∈ [-1, 1]
# Map to [0, 1]: (cosine + 1) / 2
embed_norm = {k: (v + 1.0) / 2.0 for k, v in embed_scores.items()}
```

Maps cosine similarity to **[0, 1]** where:
- `-1` (opposite) → `0`
- `0` (orthogonal) → `0.5`
- `1` (identical) → `1`

### Fusion Formula

```python
combined_score = α × embed_norm + (1 - α) × bm25_norm
```

**Example:**
- `bm25_norm = 0.8` (high lexical match)
- `embed_norm = 0.6` (moderate semantic match)
- `α = 0.6`
- `combined = 0.6 × 0.6 + 0.4 × 0.8 = 0.36 + 0.32 = 0.68`

### Tuning Alpha

The `alpha` parameter controls the balance:

| Alpha | BM25 Weight | Embedding Weight | Use Case |
|-------|-------------|------------------|----------|
| 0.0 | 100% | 0% | Pure keyword search (legal, code search) |
| 0.3 | 70% | 30% | Keyword-focused (product search) |
| 0.5 | 50% | 50% | Balanced (general search) |
| 0.6 | 40% | 60% | **Default** (semantic-focused) |
| 0.8 | 20% | 80% | Highly semantic (Q&A, research) |
| 1.0 | 0% | 100% | Pure semantic (conversational search) |

---

## Performance Considerations

### Computational Cost

**BM25:**
- Index building: O(N × M) where N = docs, M = avg terms/doc
- Search: O(Q × D) where Q = query terms, D = matching docs
- **Very fast** ⚡

**Embeddings:**
- Index building: O(N × E) where E = embedding model inference time
- Search: O(N) for full matrix multiplication (can be optimized with approximate search)
- **Slower** 🐢

**Hybrid:**
- Combines both costs
- Can be optimized by:
  - Using approximate nearest neighbor search (FAISS, Annoy)
  - Pre-computing embeddings
  - Caching query embeddings

### Memory Usage

**BM25:**
- Inverted index: ~O(V × D) where V = vocabulary size
- **Low memory** 💾

**Embeddings:**
- Embedding matrix: N × 768 × 4 bytes (float32)
- For 10,000 docs: ~30 MB
- **Higher memory** 💾💾

**Hybrid:**
- Sum of both
- **Moderate memory** 💾💾

---

## Real-World Example

### Query: "Tesla stock price"

**BM25 Results:**
1. "Tesla stock price reaches new high" (score: 2.5) ✅
2. "Tesla shares surge" (score: 1.2) - missing "price"
3. "Stock market analysis" (score: 0.8) - generic

**Embedding Results:**
1. "Tesla stock price reaches new high" (score: 0.92) ✅
2. "TSLA shares surge in after-hours trading" (score: 0.88) ✅ - understands TSLA = Tesla
3. "Elon Musk's company stock valuation" (score: 0.75) ✅ - semantic match

**Hybrid Results (α=0.6):**
1. "Tesla stock price reaches new high" (combined: 0.95) ✅✅
2. "TSLA shares surge in after-hours trading" (combined: 0.82) ✅✅
3. "Elon Musk's company stock valuation" (combined: 0.68) ✅
4. "Tesla shares surge" (combined: 0.65) ✅

**Key Insight:** Hybrid finds documents that either method alone would miss!

---

## Conclusion

The hybrid BM25 + Embedding approach combines:

1. **BM25's precision** for exact keyword matching
2. **Embeddings' semantic understanding** for conceptual matching
3. **Score fusion** for optimal ranking

This results in:
- ✅ Better recall (finds more relevant documents)
- ✅ Better precision (ranks relevant documents higher)
- ✅ Handles synonyms and paraphrases
- ✅ Robust fallback if one method fails
- ✅ Configurable balance via `alpha` parameter

The system gracefully degrades to BM25-only mode if embeddings are unavailable, ensuring it always works.

---

## References

- **BM25**: Robertson, S. E., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond.
- **Sentence Transformers**: Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.
- **Hybrid Search**: Various implementations in modern search systems (Elasticsearch, Vespa, etc.)

