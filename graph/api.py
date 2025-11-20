"""
Flask blueprint for graph queries and analytics.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Blueprint, jsonify, request

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from graph.analytics import compute_pagerank, detect_communities, relationship_trends
from graph.builder import KnowledgeGraphBuilder
from graph.queries import entity_payload, shortest_path

DEFAULT_EXTRACTIONS = "data/extractions"
MOCK_EXTRACTIONS = "mock_data/mock_llm_responses.json"


def _bootstrap_builder() -> KnowledgeGraphBuilder:
    builder = KnowledgeGraphBuilder()
    if Path(DEFAULT_EXTRACTIONS).exists():
        builder.load_from_cache(DEFAULT_EXTRACTIONS)
    elif Path(MOCK_EXTRACTIONS).exists():
        with open(MOCK_EXTRACTIONS, encoding="utf-8") as handle:
            for record in json.load(handle):
                builder.add_extraction_result(record)
    return builder


_BUILDER: KnowledgeGraphBuilder | None = None


def get_builder() -> KnowledgeGraphBuilder:
    global _BUILDER
    if _BUILDER is None:
        _BUILDER = _bootstrap_builder()
    return _BUILDER


def set_builder(builder: KnowledgeGraphBuilder):
    global _BUILDER
    _BUILDER = builder


graph_blueprint = Blueprint("graph", __name__)


@graph_blueprint.route("/health", methods=["GET"])
def health():
    builder = get_builder()
    stats = builder.get_statistics()
    return jsonify({"status": "ok", **stats})


@graph_blueprint.route("/stats", methods=["GET"])
def stats():
    builder = get_builder()
    return jsonify(builder.get_statistics())


@graph_blueprint.route("/entity/<entity_name>", methods=["GET"])
def entity_view(entity_name: str):
    builder = get_builder()
    payload = entity_payload(builder, entity_name)
    if not payload:
        return jsonify({"error": "entity not found"}), 404
    return jsonify(payload)


@graph_blueprint.route("/article/<article_id>/entities", methods=["GET"])
def article_entities(article_id: str):
    """Get all entities from an article's extraction data"""
    extraction_path = Path(DEFAULT_EXTRACTIONS) / f"{article_id}.json"
    if not extraction_path.exists():
        return jsonify({"error": "extraction not found"}), 404
    
    try:
        with open(extraction_path, encoding="utf-8") as handle:
            extraction = json.load(handle)
        
        entities = set()
        for triple in extraction.get("triples", []):
            entities.add(triple.get("entity1"))
            entities.add(triple.get("entity2"))
        
        return jsonify({"article_id": article_id, "entities": sorted(list(entities))})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@graph_blueprint.route("/analytics/pagerank", methods=["POST", "GET"])
def pagerank_view():
    builder = get_builder()
    top_k = int(request.args.get("top_k", 20))
    results = compute_pagerank(builder.graph, top_k=top_k)
    return jsonify({"top_entities": results})


@graph_blueprint.route("/analytics/communities", methods=["POST", "GET"])
def communities_view():
    builder = get_builder()
    min_size = int(request.args.get("min_size", 3))
    try:
        results = detect_communities(builder.graph, min_size=min_size)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"communities": results})


@graph_blueprint.route("/analytics/trends", methods=["GET"])
def trends_view():
    builder = get_builder()
    relationship = request.args.get("relationship")
    granularity = request.args.get("granularity", "day")
    try:
        data = relationship_trends(builder.graph, relationship=relationship, granularity=granularity)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"relationship": relationship, "granularity": granularity, "series": data})


@graph_blueprint.route("/path/<source>/<target>", methods=["GET"])
def path_view(source: str, target: str):
    builder = get_builder()
    path = shortest_path(builder.graph, source, target)
    if not path:
        return jsonify({"error": "no path found"}), 404
    return jsonify({"path": path})


@graph_blueprint.route("/visualization", methods=["GET"])
def graph_visualization():
    """Get graph data for visualization (nodes and edges)"""
    builder = get_builder()
    graph = builder.graph
    
    # Get nodes with metadata
    nodes = []
    for node, data in graph.nodes(data=True):
        nodes.append({
            "id": node,
            "label": node,
            "type": data.get("type", "Unknown"),
            "degree": data.get("degree", 0)
        })
    
    # Get edges with metadata
    edges = []
    edge_counts = {}  # Count multiple edges between same nodes
    for source, target, data in graph.edges(data=True):
        key = (source, target, data.get("relationship", ""))
        if key not in edge_counts:
            edge_counts[key] = 0
        edge_counts[key] += 1
        
        edges.append({
            "source": source,
            "target": target,
            "relationship": data.get("relationship", ""),
            "count": edge_counts[key],
            "confidence": data.get("confidence", 1.0)
        })
    
    # Remove duplicates, keeping the one with highest count
    unique_edges = {}
    for edge in edges:
        key = (edge["source"], edge["target"], edge["relationship"])
        if key not in unique_edges or edge["count"] > unique_edges[key]["count"]:
            unique_edges[key] = edge
    
    return jsonify({
        "nodes": nodes,
        "edges": list(unique_edges.values()),
        "stats": {
            "nodes": len(nodes),
            "edges": len(unique_edges),
            "relationships": len(set(e["relationship"] for e in unique_edges.values()))
        }
    })


@graph_blueprint.route("/reload", methods=["POST"])
def reload_graph():
    dataset_dir = request.json.get("cache_dir") if request.is_json else DEFAULT_EXTRACTIONS
    builder = KnowledgeGraphBuilder()
    if Path(dataset_dir).exists():
        builder.load_from_cache(dataset_dir)
    elif Path(MOCK_EXTRACTIONS).exists():
        with open(MOCK_EXTRACTIONS, encoding="utf-8") as handle:
            for record in json.load(handle):
                builder.add_extraction_result(record)
    set_builder(builder)
    return jsonify({"status": "reloaded", "nodes": builder.graph.number_of_nodes()})
