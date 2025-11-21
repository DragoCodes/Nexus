"""Graph visualization component using PyVis."""

import networkx as nx
from pyvis.network import Network
from typing import Dict, Optional, Any
import math


def create_interactive_graph(
    nx_graph: nx.DiGraph,
    config_options: Dict[str, Any],
    height: str = "700px",
    width: str = "100%"
) -> str:
    """
    Create an interactive graph visualization using PyVis.
    
    Args:
        nx_graph: NetworkX graph object
        config_options: Dictionary with visualization settings:
            - node_size_by: str ("PageRank", "Degree", "Mention Count")
            - color_scheme: dict (entity_type -> color mapping)
            - show_labels: bool
            - physics_enabled: bool
            - min_node_size: int (default: 10)
            - max_node_size: int (default: 50)
        height: Height of the visualization
        width: Width of the visualization
        
    Returns:
        HTML string for the graph visualization
    """
    if nx_graph.number_of_nodes() == 0:
        return "<div style='padding: 20px; text-align: center;'>No nodes to display</div>"
    
    # Extract config options
    node_size_by = config_options.get('node_size_by', 'Degree')
    color_scheme = config_options.get('color_scheme', get_default_color_scheme())
    show_labels = config_options.get('show_labels', True)
    physics_enabled = config_options.get('physics_enabled', True)
    min_node_size = config_options.get('min_node_size', 10)
    max_node_size = config_options.get('max_node_size', 50)
    
    # Create PyVis Network
    net = Network(
        height=height,
        width=width,
        directed=True,
        bgcolor="#ffffff",
        font_color="#333333"
    )
    
    # Configure physics
    if physics_enabled:
        net.set_options("""
        {
            "physics": {
                "enabled": true,
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 200,
                    "springConstant": 0.08,
                    "damping": 0.4,
                    "avoidOverlap": 0.5
                },
                "minVelocity": 0.75,
                "solver": "forceAtlas2Based",
                "stabilization": {
                    "enabled": true,
                    "iterations": 200,
                    "updateInterval": 25
                }
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 200,
                "hideEdgesOnDrag": false,
                "hideEdgesOnZoom": false
            },
            "edges": {
                "smooth": {
                    "type": "continuous",
                    "roundness": 0.5
                },
                "arrows": {
                    "to": {
                        "enabled": true,
                        "scaleFactor": 0.8
                    }
                }
            }
        }
        """)
    else:
        net.set_options("""
        {
            "physics": {
                "enabled": false
            }
        }
        """)
    
    # Calculate node sizes
    node_sizes = _calculate_node_sizes(nx_graph, node_size_by, min_node_size, max_node_size)
    
    # Add nodes
    for node, data in nx_graph.nodes(data=True):
        entity_name = str(node)
        entity_type = data.get('type', 'Unknown')
        mention_count = data.get('mention_count', 0)
        
        # Get node size
        node_size = node_sizes.get(node, min_node_size)
        
        # Get node color
        node_color = color_scheme.get(entity_type, '#808080')  # Default gray
        
        # Create tooltip
        tooltip = f"""
        <b>{entity_name}</b><br>
        Type: {entity_type}<br>
        Mentions: {mention_count}<br>
        Connections: {nx_graph.degree(node)}
        """
        
        # Add node to network
        net.add_node(
            entity_name,
            label=entity_name if show_labels else "",
            size=node_size,
            color=node_color,
            title=tooltip,
            font={"size": 12 if show_labels else 0}
        )
    
    # Calculate edge widths based on frequency
    edge_frequencies = {}
    for u, v, data in nx_graph.edges(data=True):
        key = (u, v)
        freq = data.get('frequency', 1)
        edge_frequencies[key] = freq
    
    max_freq = max(edge_frequencies.values()) if edge_frequencies else 1
    min_edge_width = 1
    max_edge_width = 5
    
    # Add edges
    for u, v, data in nx_graph.edges(data=True):
        relationship_type = data.get('relationship_type', 'Unknown')
        frequency = data.get('frequency', 1)
        article_ids = data.get('source_article_ids', [])
        
        # Calculate edge width
        if max_freq > 1:
            edge_width = min_edge_width + (max_edge_width - min_edge_width) * (frequency / max_freq)
        else:
            edge_width = min_edge_width
        
        # Get edge color
        edge_color = get_relationship_color(relationship_type)
        
        # Create tooltip
        tooltip = f"""
        <b>{relationship_type}</b><br>
        From: {u}<br>
        To: {v}<br>
        Frequency: {frequency}<br>
        Evidence: {len(article_ids)} article(s)
        """
        
        # Add edge to network
        net.add_edge(
            str(u),
            str(v),
            title=tooltip,
            color=edge_color,
            width=edge_width,
            label=relationship_type if show_labels else ""
        )
    
    # Generate HTML
    html_string = net.generate_html()
    
    return html_string


def _calculate_node_sizes(
    graph: nx.DiGraph,
    size_by: str,
    min_size: int,
    max_size: int
) -> Dict[str, float]:
    """Calculate node sizes based on the specified metric."""
    node_sizes = {}
    
    if size_by == "PageRank":
        try:
            pagerank = nx.pagerank(graph)
            if pagerank:
                max_pr = max(pagerank.values())
                min_pr = min(pagerank.values())
                for node, score in pagerank.items():
                    if max_pr > min_pr:
                        normalized = (score - min_pr) / (max_pr - min_pr)
                    else:
                        normalized = 0.5
                    node_sizes[node] = min_size + (max_size - min_size) * normalized
        except:
            # Fallback to degree if PageRank fails
            size_by = "Degree"
    
    if size_by == "Degree":
        degrees = dict(graph.degree())
        if degrees:
            max_degree = max(degrees.values())
            min_degree = min(degrees.values())
            for node, degree in degrees.items():
                if max_degree > min_degree:
                    normalized = (degree - min_degree) / (max_degree - min_degree)
                else:
                    normalized = 0.5
                node_sizes[node] = min_size + (max_size - min_size) * normalized
    
    elif size_by == "Mention Count":
        mention_counts = {node: data.get('mention_count', 0) for node, data in graph.nodes(data=True)}
        if mention_counts:
            max_mentions = max(mention_counts.values())
            min_mentions = min(mention_counts.values())
            for node, mentions in mention_counts.items():
                if max_mentions > min_mentions:
                    normalized = (mentions - min_mentions) / (max_mentions - min_mentions)
                else:
                    normalized = 0.5
                node_sizes[node] = min_size + (max_size - min_size) * normalized
    
    # Default size if calculation failed
    if not node_sizes:
        for node in graph.nodes():
            node_sizes[node] = (min_size + max_size) / 2
    
    return node_sizes


def get_default_color_scheme() -> Dict[str, str]:
    """Get default color scheme for entity types."""
    return {
        "Company": "#1f77b4",      # Blue
        "Person": "#2ca02c",       # Green
        "Product": "#ff7f0e",      # Orange
        "Organization": "#d62728", # Red
        "Location": "#9467bd",     # Purple
        "Unknown": "#808080"       # Gray
    }


def get_relationship_color(relationship_type: str) -> str:
    """Get color for relationship type."""
    color_map = {
        "acquires": "#d62728",           # Red
        "acquired_by": "#d62728",
        "partners_with": "#2ca02c",      # Green
        "invests_in": "#ffd700",         # Gold
        "receives_investment_from": "#ffd700",
        "supplies_to": "#1f77b4",        # Blue
        "sources_from": "#1f77b4",
        "competes_with": "#ff7f0e",      # Orange
        "employs": "#9467bd",            # Purple
        "works_for": "#9467bd",
        "appoints": "#9467bd",
        "owns": "#8c564b",               # Brown
        "owned_by": "#8c564b",
        "sues": "#e377c2",                # Pink
        "sued_by": "#e377c2",
        "regulates": "#7f7f7f",          # Dark gray
        "regulated_by": "#7f7f7f",
        "announces": "#17becf",           # Cyan
        "launches": "#17becf",
        "merges_with": "#bcbd22"          # Olive
    }
    
    # Normalize relationship type
    rel_type_lower = relationship_type.lower().replace(" ", "_")
    
    return color_map.get(rel_type_lower, "#808080")  # Default gray

