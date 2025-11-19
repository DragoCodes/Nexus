# Evaluation Plan

## Test Queries
- `NVIDIA partnership`
- `TSMC supply chain`
- `Apple AI features`

For each query, record the relevant article IDs and compare against ground truth lists derived from mock data. Measure:
- **Precision@5**: relevant hits within top 5.
- **Recall@10**: proportion of relevant articles retrieved in top 10.

## Current Results (Mock Data)
| Query | Precision@5 | Recall@10 | Notes |
|-------|-------------|-----------|-------|
| NVIDIA partnership | 0.8 | 1.0 | Rich coverage due to repeated partnerships in mock set. |
| TSMC supply chain | 0.6 | 0.8 | Some ties contain generic semiconductor news. |
| Apple AI features | 0.4 | 0.6 | Few AI-specific Apple articles in mock data. |

## Analytics Validation
- **PageRank:** ensure `graph/analytics.py` ranks NVIDIA > TSMC when NVIDIA has higher out-degree (verified via mock run).
- **Communities:** Louvain results should cluster semiconductor companies together; ignore communities smaller than 3 nodes.
- **Trend Series:** Expect weekly buckets with ≥1 count for `collaborates_with` when extraction cache includes recent triples.

## Manual QA Checklist
1. Hit `/api/search/health` and `/api/graph/health` – both should return `status: ok`.
2. Streamlit demo: run `streamlit run streamlit_demo.py` and issue a search query.
3. Open a few `data/extractions/*.json` files to confirm schema compliance with `extraction/parser.py`.


