"""Knowledge Graph visualization page."""

import streamlit as st
import sys
from pathlib import Path
import networkx as nx

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.module5_api.app import NexusApp

# Import graph visualizer
import sys
from pathlib import Path
frontend_path = Path(__file__).parent.parent
sys.path.insert(0, str(frontend_path))
from components.graph_visualizer import (
    create_interactive_graph,
    get_default_color_scheme,
    get_relationship_color
)


@st.cache_resource
def get_app():
    """Get NexusApp instance."""
    return NexusApp()


def main():
    """Main function for Knowledge Graph page."""
    st.title("🕸️ Knowledge Graph")
    st.markdown("Interactive visualization of entity relationships")
    
    # Get app instance
    app = get_app()
    
    if app is None or app.graph_manager is None:
        st.error("Graph manager not available. Please ensure the graph database exists.")
        st.info("You may need to run Module 4 to build the graph first.")
        st.stop()
    
    # Get graph
    graph = app.graph_manager.get_graph()
    
    if graph.number_of_nodes() == 0:
        st.warning("Graph is empty. Please build the graph first.")
        st.info("Run Module 4 to extract relationships and build the graph.")
        st.stop()
    
    # Sidebar - Controls Panel
    with st.sidebar:
        st.header("🎛️ Controls")
        
        # Filters
        st.subheader("Filters")
        
        # Entity type filter
        entity_types = set()
        for node, data in graph.nodes(data=True):
            entity_type = data.get('type', 'Unknown')
            entity_types.add(entity_type)
        
        selected_entity_types = st.multiselect(
            "Entity Types",
            options=sorted(entity_types),
            default=sorted(entity_types),
            help="Select entity types to display"
        )
        
        # Relationship type filter
        rel_types = set()
        for u, v, data in graph.edges(data=True):
            rel_type = data.get('relationship_type', 'Unknown')
            rel_types.add(rel_type)
        
        selected_rel_types = st.multiselect(
            "Relationship Types",
            options=sorted(rel_types),
            default=sorted(rel_types),
            help="Select relationship types to display"
        )
        
        # Minimum connections filter
        min_connections = st.slider(
            "Minimum Connections",
            min_value=0,
            max_value=10,
            value=1,
            help="Filter out nodes with fewer connections"
        )
        
        st.divider()
        
        # View Options
        st.subheader("View Options")
        
        node_size_by = st.selectbox(
            "Node Size By",
            ["Degree", "PageRank", "Mention Count"],
            index=0,
            help="What metric determines node size"
        )
        
        show_labels = st.checkbox(
            "Show Labels",
            value=True,
            help="Display entity names on nodes"
        )
        
        physics_enabled = st.checkbox(
            "Physics Simulation",
            value=True,
            help="Enable force-directed layout"
        )
        
        st.divider()
        
        # Search
        st.subheader("Search")
        
        # Get all entities for autocomplete
        all_entities = app.get_all_entities()
        entity_names = [e['entity_name'] for e in all_entities]
        
        selected_entity = st.selectbox(
            "Focus on Entity",
            options=["None"] + entity_names[:100],  # Limit to first 100 for performance
            help="Focus graph on a specific entity (ego network)"
        )
        
        if selected_entity != "None":
            if st.button("🔍 Focus", use_container_width=True):
                st.session_state.focus_entity = selected_entity
        
        if st.button("🔄 Reset View", use_container_width=True):
            if 'focus_entity' in st.session_state:
                del st.session_state.focus_entity
            st.rerun()
        
        st.divider()
        
        # Graph Statistics
        st.subheader("Graph Statistics")
        
        filtered_graph = _apply_filters(
            graph,
            selected_entity_types,
            selected_rel_types,
            min_connections,
            st.session_state.get('focus_entity', None)
        )
        
        st.metric("Nodes", filtered_graph.number_of_nodes())
        st.metric("Edges", filtered_graph.number_of_edges())
        
        if filtered_graph.number_of_nodes() > 0:
            avg_degree = sum(dict(filtered_graph.degree()).values()) / filtered_graph.number_of_nodes()
            st.metric("Avg. Degree", f"{avg_degree:.2f}")
        
        # Density
        if filtered_graph.number_of_nodes() > 1:
            density = nx.density(filtered_graph)
            st.metric("Density", f"{density:.4f}")
        
        st.divider()
        
        # Legend
        st.subheader("Legend")
        
        st.markdown("**Node Colors:**")
        color_scheme = get_default_color_scheme()
        for entity_type, color in color_scheme.items():
            st.markdown(f'<span style="color: {color}">●</span> {entity_type}', unsafe_allow_html=True)
        
        st.markdown("**Node Size:**")
        st.caption(f"Based on {node_size_by}")
        
        st.markdown("**Edge Colors:**")
        sample_rels = list(rel_types)[:5]
        for rel_type in sample_rels:
            color = get_relationship_color(rel_type)
            st.markdown(f'<span style="color: {color}">━</span> {rel_type}', unsafe_allow_html=True)
    
    # Main content area
    col_main, col_details = st.columns([2, 1])
    
    with col_main:
        # Graph Visualization
        st.subheader("Graph Visualization")
        
        # Apply filters and get filtered graph
        filtered_graph = _apply_filters(
            graph,
            selected_entity_types,
            selected_rel_types,
            min_connections,
            st.session_state.get('focus_entity', None)
        )
        
        if filtered_graph.number_of_nodes() == 0:
            st.warning("No nodes match the current filters. Try adjusting your filters.")
        else:
            # Configuration for visualization
            config = {
                'node_size_by': node_size_by,
                'color_scheme': get_default_color_scheme(),
                'show_labels': show_labels,
                'physics_enabled': physics_enabled,
                'min_node_size': 10,
                'max_node_size': 50
            }
            
            # Generate graph HTML
            with st.spinner("Generating graph visualization..."):
                html_string = create_interactive_graph(
                    filtered_graph,
                    config,
                    height="700px",
                    width="100%"
                )
            
            # Display graph
            st.components.v1.html(html_string, height=700, scrolling=False)
            
            # Download button
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                if st.button("📥 Export GraphML", use_container_width=True):
                    try:
                        nx.write_graphml(filtered_graph, "graph_export.graphml")
                        st.success("Graph exported to graph_export.graphml")
                    except Exception as e:
                        st.error(f"Export failed: {e}")
            
            with col_dl2:
                if st.button("🔄 Regenerate", use_container_width=True):
                    st.rerun()
    
    with col_details:
        # Details Panel
        st.subheader("Entity Details")
        
        # Entity search
        entity_search = st.selectbox(
            "Select Entity",
            options=["None"] + [e['entity_name'] for e in all_entities[:50]],
            help="Select an entity to view details"
        )
        
        if entity_search != "None":
            entity_details = app.get_entity_details(entity_search)
            
            if entity_details:
                st.markdown(f"### {entity_details.entity_name}")
                st.markdown(f"**Type:** {entity_details.entity_type}")
                st.markdown(f"**Mentions:** {entity_details.mention_count}")
                st.markdown(f"**Total Connections:** {entity_details.total_degree}")
                
                st.divider()
                
                # Incoming relationships
                if entity_details.incoming_relationships:
                    st.markdown("#### Incoming Relationships")
                    for rel in entity_details.incoming_relationships[:10]:  # Limit to 10
                        rel_type = rel.get('relationship_type', 'Unknown')
                        entity2 = rel.get('entity1', 'Unknown')
                        st.markdown(f"- **{entity2}** → {rel_type}")
                    
                    if len(entity_details.incoming_relationships) > 10:
                        st.caption(f"... and {len(entity_details.incoming_relationships) - 10} more")
                
                # Outgoing relationships
                if entity_details.outgoing_relationships:
                    st.markdown("#### Outgoing Relationships")
                    for rel in entity_details.outgoing_relationships[:10]:  # Limit to 10
                        rel_type = rel.get('relationship_type', 'Unknown')
                        entity2 = rel.get('entity2', 'Unknown')
                        st.markdown(f"- {rel_type} → **{entity2}**")
                    
                    if len(entity_details.outgoing_relationships) > 10:
                        st.caption(f"... and {len(entity_details.outgoing_relationships) - 10} more")
            else:
                st.info("Entity details not found")
        else:
            st.info("Select an entity to view details")
            
            # Show top entities by degree
            st.markdown("#### Top Connected Entities")
            top_entities = sorted(
                all_entities,
                key=lambda x: x.get('mention_count', 0),
                reverse=True
            )[:10]
            
            for idx, entity in enumerate(top_entities, 1):
                st.caption(f"{idx}. {entity['entity_name']} ({entity['entity_type']}) - {entity.get('mention_count', 0)} mentions")


def _apply_filters(
    graph: nx.DiGraph,
    entity_types: list,
    rel_types: list,
    min_connections: int,
    focus_entity: str = None
) -> nx.DiGraph:
    """Apply filters to graph and return filtered graph."""
    filtered = graph.copy()
    
    # Focus on specific entity (ego network)
    if focus_entity and focus_entity in filtered:
        # Get ego network (radius 1)
        ego = nx.ego_graph(filtered, focus_entity, radius=1, undirected=True)
        filtered = ego
    
    # Filter by entity type
    if entity_types:
        nodes_to_remove = [
            node for node, data in filtered.nodes(data=True)
            if data.get('type') not in entity_types
        ]
        filtered.remove_nodes_from(nodes_to_remove)
    
    # Filter by relationship type
    if rel_types:
        edges_to_remove = [
            (u, v) for u, v, data in filtered.edges(data=True)
            if data.get('relationship_type') not in rel_types
        ]
        filtered.remove_edges_from(edges_to_remove)
    
    # Filter by minimum connections
    if min_connections > 0:
        nodes_to_remove = [
            node for node in filtered.nodes()
            if filtered.degree(node) < min_connections
        ]
        filtered.remove_nodes_from(nodes_to_remove)
    
    return filtered


if __name__ == "__main__":
    main()

