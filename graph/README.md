# Knowledge Graph & Analytics Engine

## Quick Start
```bash
python graph/builder.py --extractions data/extractions --graph-cache data/graph_snapshot.json
python -m flask --app graph.api run --port 5001
```

## Testing with Mock Data
```bash
pytest tests/test_graph.py
```

## API Examples
- `curl http://localhost:5000/graph/entity/NVIDIA`
- `curl -X POST http://localhost:5000/graph/analytics/pagerank`

`graph/builder.py` ingests files like `mock_data/mock_llm_responses.json` or `data/extractions/*.json`, emits NetworkX structures, and `graph/analytics.py` exposes PageRank + community detection (Louvain). Export or visualize the graph by pointing `--mock-graph` to `mock_data/mock_graph.json`.

## PageRank Complexity
We use the power iteration method implemented in NetworkX (`nx.pagerank`). Each iteration costs `O(|E|)` and converges in roughly `O(log(ε)/ (1 - α))` steps (α=0.85). For a graph with 30 nodes/50 edges (mock), runtime is milliseconds; even at thousands of edges it remains interactive (<1s) on commodity hardware.

