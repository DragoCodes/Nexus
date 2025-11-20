"""
Helper query functions for the graph API.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import networkx as nx

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from graph.builder import KnowledgeGraphBuilder


def entity_payload(builder: KnowledgeGraphBuilder, entity_name: str) -> Optional[Dict]:
    node = builder.get_entity(entity_name)
    if not node:
        return None
    relationships = builder.get_relationships(entity_name)
    return {"entity": entity_name, "data": node, "relationships": relationships}


def shortest_path(graph: nx.MultiDiGraph, source: str, target: str) -> List[str]:
    if source not in graph.nodes or target not in graph.nodes:
        return []
    try:
        path = nx.shortest_path(graph.to_undirected(), source=source, target=target)
        return path
    except nx.NetworkXNoPath:
        return []
