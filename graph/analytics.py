"""
Graph analytics utilities (PageRank, communities, trends).
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import networkx as nx

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

try:
    import community as community_louvain
except ImportError:  # pragma: no cover
    community_louvain = None


def compute_pagerank(graph: nx.MultiDiGraph, top_k: int = 20) -> List[Dict]:
    if graph.number_of_nodes() == 0:
        return []
    pr = nx.pagerank(graph.to_directed())
    ranked = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"entity": entity, "score": score} for entity, score in ranked]


def detect_communities(
    graph: nx.MultiDiGraph, min_size: int = 3
) -> List[Dict[str, List[str]]]:
    if community_louvain is None:
        raise RuntimeError("python-louvain is not installed.")
    undirected = graph.to_undirected()
    if undirected.number_of_nodes() == 0:
        return []
    partition = community_louvain.best_partition(undirected)
    communities: Dict[int, List[str]] = {}
    for node, community_id in partition.items():
        communities.setdefault(community_id, []).append(node)

    results = []
    for community_id, members in communities.items():
        if len(members) >= min_size:
            results.append({"community_id": community_id, "members": sorted(members)})
    return results


def relationship_trends(
    graph: nx.MultiDiGraph,
    relationship: Optional[str] = None,
    granularity: str = "day",
) -> List[Dict]:
    if pd is None:
        raise RuntimeError("pandas is required for trend analysis.")

    rows = []
    for source, target, data in graph.edges(data=True):
        rel = data.get("relationship", "")
        if relationship and rel != relationship:
            continue
        timestamp = data.get("publication_date") or data.get("created_at")
        if not timestamp:
            continue
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        rows.append({"relationship": rel, "timestamp": dt})

    if not rows:
        return []

    df = pd.DataFrame(rows)
    df["bucket"] = df["timestamp"].dt.to_period(granularity[0].upper()).dt.start_time
    grouped = (
        df.groupby("bucket")
        .size()
        .reset_index(name="count")
        .sort_values("bucket")
    )

    return [
        {"bucket": row.bucket.isoformat(), "count": int(row["count"])}
        for _, row in grouped.iterrows()
    ]
